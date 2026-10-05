from pyscipopt import Model, quicksum, Conshdlr, SCIP_RESULT
from itertools import combinations
from pathlib import Path
import logging
import time
import csv
import math

pasta_resultados = Path(__file__).parent.parent / "Resultados" / "Benders"
pasta_resultados.mkdir(parents=True, exist_ok=True)

def configura_logger(pasta_instancia):

    arquivo_log = pasta_instancia / "_resultado.log"
    logger = logging.getLogger(f"Benders_{pasta_instancia.name}")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(arquivo_log, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def ler_instancia(nome_arquivo):
    
    with open(nome_arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    peso = {}
    familia_produto = {}
    capacidade = {}
    tempo_proc = {}
    maquinas_familia = {}
    familia = {}
    produtos_por_familia = {}

    inst = None
    secao = None
    produto_id = 1

    for linha in linhas:

        if "NÚMERO DE PRODUTOS" in linha:
            texto, inst = linha.split(":")

        if "NOME DO PRODUTO" in linha:
            secao = "produtos"
            continue

        elif "MÁQUINAS/CAPACIDADE" in linha:
            secao = "maquinas"
            continue

        elif "FAMÍLIA/TEMPO" in linha:
            secao = "familias"
            continue

        elif "---" in linha:
            continue

        if secao == "produtos":
            nome, p, f = linha.split("/")

            peso[produto_id] = float(p)
            familia_produto[produto_id] = int(f)

            produto_id += 1

        elif secao == "maquinas":
            maq, cap = linha.split("/")

            capacidade[maq] = float(cap)

        elif secao == "familias":
            fam, tempo, maq = linha.split("/")

            fam = int(fam)
            familia[fam] = fam
            tempo_proc[fam] = int(tempo)
            maquinas_familia[fam] = maq.split(",")

    for produto, fam in familia_produto.items():

        if fam not in produtos_por_familia:
            produtos_por_familia[fam] = []

        produtos_por_familia[fam].append(produto)

    return (
        inst,
        peso,
        familia_produto,
        capacidade,
        tempo_proc,
        maquinas_familia,
        familia,
        produtos_por_familia
    )

def cria_lotes(capacidade, peso, produtos_por_familia, tempo_proc, familia_produto, maquinas_familia):
    
    T = []
    P = []
    lotes_validos = []
    A = []
    maquinas = list(capacidade.keys())
    produtos = list(peso.keys())
    familia_lote = []

    for fam, produtos_fam in produtos_por_familia.items():
    
            maior_capacidade = max(capacidade[m] for m in maquinas_familia[fam])
    
            for r in range(1, len(produtos_fam) + 1):
                for lote in combinations(produtos_fam, r):
                    if sum(peso[p] for p in lote) <= maior_capacidade:
                        lotes_validos.append(lote)
                        familia_lote.append(fam)
                        
    #Binariza :)
    for lotes in lotes_validos:
        linha = [1 if n in lotes else 0 for n in produtos]
        A.append(linha)

    #tempos
    for lote in lotes_validos:
        tempo_lote = tempo_proc[familia_produto[lote[0]]]
        T.append(tempo_lote)

    #pesos
    for lote in lotes_validos:
        peso_lote = sum(peso[p] for p in lote)
        P.append(peso_lote)

    return (
        T,
        P,
        lotes_validos,
        A,
        maquinas,
        produtos,
        familia_lote
    )

def cria_master(lotes_validos, produtos, A, L):

    modelo = Model("Master")
    modelo.hideOutput()

    X = [None for n in range(len(lotes_validos))]
    for n in range(len(X)):
        X[n] = modelo.addVar(f"X{n}", vtype="B")

    theta = modelo.addVar("theta", vtype="C", lb = L)

    for i in range(len(produtos)):
        modelo.addCons(quicksum(X[n] * A[n][i] for n in range(len(lotes_validos))) == 1)

    modelo.addCons(theta >= L)

    # modelo.setObjective(quicksum(X[n] for n in range(len(lotes_validos))) + theta, "minimize")
    modelo.setObjective(theta, "minimize")

    return(modelo, X, theta)

def cria_sub(maquinas, lotes_utilizados, maquinas_familia, capacidade, T, P, familia_lote):

    modelo = Model("Sub")
    modelo.hideOutput()

    y = {}
    for u in lotes_utilizados:
        for j in range(len(maquinas)):
            y[(u,j)] = modelo.addVar(f"Y{u},{j}", vtype="B")

    Cmax = modelo.addVar("Cmax", vtype="C", lb=max(T[u] for u in lotes_utilizados))

    for u in lotes_utilizados:
        modelo.addCons(quicksum(y[(u,j)] for j in range(len(maquinas))) == 1)

    for u in lotes_utilizados:
        fam = familia_lote[u]
        for j, maquina in enumerate(maquinas):
            if maquina not in maquinas_familia[fam]:
                modelo.addCons(y[(u,j)] == 0)

    for j in range(len(maquinas)):
        modelo.addCons(quicksum(y[(u, j)] * T[u] for u in lotes_utilizados) <= Cmax)

    for u in lotes_utilizados:
        for j in range(len(maquinas)):
            modelo.addCons(P[u] * y[(u, j)] <= capacidade[maquinas[j]])

    modelo.setObjective(Cmax, "minimize")
    
    return(modelo, y, Cmax)
    
def resolve_master(modelo, X, theta):

    modelo.optimize()
    x_vals = [int(round(modelo.getVal(X[n]))) for n in range(len(X))]
    return(modelo.getObjVal(), modelo.getVal(theta), x_vals)

def resolve_sub(modelo):

    modelo.optimize()

    return(modelo.getObjVal())

class BendersLazyCuts(Conshdlr):

    def __init__(self, master, X, theta, lotes_validos, maquinas, maquinas_familia, capacidade, T, P, familia_lote, L, logger):
        
        self.master = master
        self.X = X
        self.theta = theta
        self.lotes_validos = lotes_validos
        self.maquinas = maquinas
        self.maquinas_familia = maquinas_familia
        self.capacidade = capacidade
        self.T = T
        self.P = P
        self.familia_lote = familia_lote
        self.L = L
        self.logger = logger
        self.numero_cortes = 0
        self.cache_Q = {}
        self.cache_LB = L
        self.cache_UB = float("inf")

    def _avalia(self, sol):
      
        x_vals = [round(self.master.getSolVal(sol, self.X[n])) for n in range(len(self.X))]
        U = tuple(n for n, v in enumerate(x_vals) if v > 0.5)

        if not U:
            return False, U, None, None

        if U not in self.cache_Q:
            sub, y, Cmax = cria_sub(self.maquinas, U, self.maquinas_familia,
                                     self.capacidade, self.T, self.P, self.familia_lote)
            self.cache_Q[U] = resolve_sub(sub)

        Q = self.cache_Q[U]
        theta_val = self.master.getSolVal(sol, self.theta)

        if Q <= self.cache_UB:
            self.cache_UB = Q

        lb_hist = self.master.getLowerbound()
        if lb_hist >= self.cache_LB:
            self.cache_LB = lb_hist

        self.cache_GAP = ((self.cache_UB - self.cache_LB) / self.cache_UB) * 100
        violado = theta_val < Q - 1e-6
        return violado, U, Q, theta_val

    def _corte(self, U, Q):

        n_lotes = len(self.X)
        dentro_de_U = quicksum(self.X[n] for n in U)
        fora_de_U = quicksum(self.X[n] for n in range(n_lotes) if n not in U)

        return self.theta >= (Q - self.L) * (dentro_de_U - fora_de_U) - (Q - self.L) * (len(U) - 1) + self.L

    def _tenta_cortar(self, sol):

        violado, U, Q, theta_val = self._avalia(sol)

        if not violado:
            return {"result": SCIP_RESULT.FEASIBLE}

        self.master.addCons(self._corte(U, Q))
        self.numero_cortes += 1
        self.logger.info(
            f'''[lazy] corte {self.numero_cortes}
                lotes usados = {len(U)}
                Q = {Q:.2f}
                theta = {theta_val:.2f}
                UB = {self.cache_UB}
                LB = {self.cache_LB}
                Gap = {self.cache_GAP:.2f}%
                '''
        )

        return {"result": SCIP_RESULT.CONSADDED}

    def consenfolp(self, constraints, nusefulconss, solinfeasible):
        x = [self.master.getSolVal(None, v) for v in self.X]
        if any(1e-6 < v < 1 - 1e-6 for v in x):   # defesa: fracionária não é comigo
            return {"result": SCIP_RESULT.FEASIBLE}
        return self._tenta_cortar(None)

    def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):

        return self._tenta_cortar(None)

    def conscheck(self, constraints, solution, checkintegrality, checklprows, printreason, completely):

        violado, *_ = self._avalia(solution)
        return {"result": SCIP_RESULT.INFEASIBLE if violado else SCIP_RESULT.FEASIBLE}

    def conslock(self, constraint, locktype, nlockspos, nlocksneg):

        for x in self.X:
            self.master.addVarLocks(x, nlockspos + nlocksneg, nlockspos + nlocksneg)
        self.master.addVarLocks(self.theta, nlockspos + nlocksneg, nlockspos + nlocksneg)

def salva_resultados_csv(arquivo_csv, dados):

    arquivo_existe = arquivo_csv.exists()

    with open(arquivo_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dados.keys())
        if not arquivo_existe:
            writer.writeheader()

        writer.writerow(dados)

def lowerBound(tempo_proc, produtos_por_familia, peso, maquinas_familia, capacidade):

    limites_familia = []

    for fam, produtos_fam in produtos_por_familia.items():

        tempo = tempo_proc[fam]
        peso_total = sum(peso[p] for p in produtos_fam)
        maquinas_disponiveis = maquinas_familia[fam]
        maior_capacidade = max(capacidade[m] for m in maquinas_disponiveis)
        numero_lotes = math.ceil(peso_total / maior_capacidade)
        numero_maquinas = len(maquinas_disponiveis)
        numero_camadas = math.ceil(numero_lotes / numero_maquinas)
        limite_familia = tempo * numero_camadas
        limites_familia.append(limite_familia)

    return max(limites_familia)

def main(nome_arquivo):

    inst, peso, familia_produto, capacidade, tempo_proc, maquinas_familia, familia, produtos_por_familia = ler_instancia(nome_arquivo)
    T, P, lotes_validos, A, maquinas, produtos, familia_lote = cria_lotes(capacidade, peso, produtos_por_familia, tempo_proc, familia_produto, maquinas_familia)
    L = lowerBound(tempo_proc, produtos_por_familia, peso, maquinas_familia, capacidade)

    pasta_instancia = (pasta_resultados / f"Resumo_Instancia_{inst}")
    pasta_instancia.mkdir(parents=True, exist_ok=True)
    logger = configura_logger(pasta_instancia)
    logger.info("=" * 60)
    logger.info("MÉTODO DE BENDERS")
    logger.info("=" * 60)
    logger.info(f"Instância: {inst}")
    logger.info(f"Número de produtos: {len(produtos)}")
    logger.info(f"Número de máquinas: {len(maquinas)}")
    logger.info(f"Número de lotes válidos: {len(lotes_validos)}")
    logger.info(f"Número de famílias: {len(familia)}")
    #=============================================================================

    inicio = time.time()
    
    master, X, theta = cria_master(lotes_validos, produtos, A, L)

    arquivo_master = ( pasta_instancia / f"master_{inst}produtos_iteracao_0.lp" ) 
    master.writeProblem( str(arquivo_master) ) 
    logger.info( f"Master inicial salvo em: {arquivo_master.name}" )


    cortes_lazy = BendersLazyCuts(
        master, X, theta, lotes_validos, maquinas, maquinas_familia,
        capacidade, T, P, familia_lote, L, logger
    )
    master.includeConshdlr(
        cortes_lazy, "BendersLazyCuts", "cortes de Benders gerados sob demanda (lazy constraints)",
        sepapriority=0, enfopriority=-10, chckpriority=-10,
        sepafreq=-1, propfreq=-1, eagerfreq=-1, maxprerounds=0,
        delaysepa=False, delayprop=False, needscons=False,
    )
    Z, valor_theta, valor_x = resolve_master(master, X, theta)

    fim = time.time()
    tempo_total = fim - inicio
    lotes_finais = [n for n, v in enumerate(valor_x) if v > 0.5]
    logger.info("") 
    logger.info("=" * 60) 
    logger.info("RESULTADO FINAL") 
    logger.info("=" * 60) 
    # logger.info(f"Solução ótima: " f"theta = {valor_theta:.2f}, " f"Q = {cortes_lazy.cache_Q[lotes_finais]:.2f}") 
    logger.info(f"Lotes selecionados: {lotes_finais}") 
    logger.info(f"Número de lotes = {len(lotes_finais)}")
    # logger.info(f"Número de iterações = {iteracao}")
    # logger.info(f"Número de cortes = {numero_cortes}")
    logger.info(f"Tempo total = {tempo_total:.4f} segundos")
    arquivo_csv = (pasta_resultados / "resultados.csv")
    dados_resultado = {
        "instancia": inst,
        "produtos": len(produtos),
        "maquinas": len(maquinas),
        "familias": len(familia),
        "lotes_validos": len(lotes_validos),
        # "iteracoes": iteracao,
        # "cortes": numero_cortes,
        "theta": round(valor_theta, 6),
        # "Q": round(Q, 6),
        "tempo_segundos": round(tempo_total, 6),
        "numero_lotes": len(lotes_finais),
        "lotes_selecionados": str(lotes_finais)}

    salva_resultados_csv(arquivo_csv, dados_resultado)
    logger.info(f"Resultados salvos em: " f"{arquivo_csv.name}")
    logger.info("")
    logger.info("Execução finalizada.")

if __name__ == "__main__":

    arquivo = Path(__file__).parent.parent / "Instancias" / "Instância Teste 30 jobs.txt"
    main(arquivo)

    # caminho = Path(__file__).parent.parent / "Instancias"
    # arquivos = sorted(caminho.glob("*.txt"), key=lambda arquivo: arquivo.stat().st_size)
    # for arquivo in arquivos:
    #     main(arquivo)