"""
Decomposicao de Benders (Integer L-shaped) para o problema de formacao e
sequenciamento de lotes em maquinas paralelas com familias/compatibilidade.

Dois modos de execucao:
  * iterativo : mestre resolvido do zero a cada corte (metodo classico do TCC);
  * bc        : branch-and-check - o mestre e resolvido em UMA unica arvore de
                branch-and-bound e os cortes sao adicionados por um constraint
                handler do SCIP sempre que uma solucao inteira e encontrada.

Uso:
  python TCC_Benders.py --instancia 30 --metodo bc
  python TCC_Benders.py --instancia 30 --metodo iterativo --corte classico
  python TCC_Benders.py --help
"""

from pyscipopt import Model, quicksum, Conshdlr, SCIP_RESULT
from itertools import combinations
from pathlib import Path
import argparse
import logging
import math
import time
import csv

RAIZ = Path(__file__).parent.parent
PASTA_INSTANCIAS = RAIZ / "Instancias"
pasta_resultados = RAIZ / "Resultados" / "Benders"
pasta_resultados.mkdir(parents=True, exist_ok=True)

EPS = 1e-6


# =============================================================================
# Utilidades
# =============================================================================

def configura_logger(pasta_instancia, sufixo):

    arquivo_log = pasta_instancia / f"_resultado_{sufixo}.log"
    logger = logging.getLogger(f"Benders_{pasta_instancia.name}_{sufixo}")
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


def localiza_instancia(texto):
    """Aceita o caminho completo do arquivo ou apenas o numero de produtos (ex.: 30)."""
    caminho = Path(texto)
    if caminho.exists():
        return caminho
    for arq in PASTA_INSTANCIAS.glob("*.txt"):
        if str(texto) in arq.stem.split():
            return arq
    raise FileNotFoundError(f"Instancia '{texto}' nao encontrada em {PASTA_INSTANCIAS}")


def salva_resultados_csv(arquivo_csv, dados):

    arquivo_existe = arquivo_csv.exists()
    with open(arquivo_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dados.keys())
        if not arquivo_existe:
            writer.writeheader()
        writer.writerow(dados)


# =============================================================================
# Leitura da instancia e geracao de lotes
# =============================================================================

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
        produtos_por_familia.setdefault(fam, []).append(produto)

    return (inst, peso, familia_produto, capacidade, tempo_proc,
            maquinas_familia, familia, produtos_por_familia)


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

    for lote in lotes_validos:
        A.append([1 if n in lote else 0 for n in produtos])
        T.append(tempo_proc[familia_produto[lote[0]]])
        P.append(sum(peso[p] for p in lote))

    return T, P, lotes_validos, A, maquinas, produtos, familia_lote


def maquinas_compativeis(lotes_validos, P, familia_lote, maquinas, maquinas_familia, capacidade):
    """Para cada lote, o conjunto (indices) de maquinas em que ele pode ser processado:
    maquina compativel com a familia (restricao 11) E com capacidade suficiente (restricao 13)."""
    compat = []
    for n in range(len(lotes_validos)):
        fam = familia_lote[n]
        compat.append(frozenset(
            j for j, m in enumerate(maquinas)
            if m in maquinas_familia[fam] and P[n] <= capacidade[m]
        ))
    return compat


def classes_de_lotes(familia_lote, compat):
    """Dois lotes com a mesma familia (mesmo tempo) e o mesmo conjunto de maquinas
    compativeis sao indistinguiveis para o subproblema. O valor Q(x) depende apenas
    de quantos lotes de cada classe foram escolhidos, e e monotono nessa contagem."""
    indice = {}
    classe_lote = []
    for n in range(len(familia_lote)):
        chave = (familia_lote[n], compat[n])
        classe_lote.append(indice.setdefault(chave, len(indice)))
    lotes_da_classe = [[] for _ in indice]
    for n, c in enumerate(classe_lote):
        lotes_da_classe[c].append(n)
    return classe_lote, lotes_da_classe


# =============================================================================
# Limite inferior valido L  (necessario para a validade do corte (27) do TCC)
# =============================================================================

def limite_inferior(T, tempo_proc, produtos_por_familia, peso, maquinas_familia, capacidade):
    """
    L deve satisfazer L <= Q(x) para TODA configuracao factivel x.

    (a) Toda familia com produtos usa ao menos um lote, logo Cmax >= max_n T_n.
    (b) Para cada familia f: sao necessarios ao menos ceil(peso_total_f / maior_capacidade_f)
        lotes, distribuidos entre as |FJ_f| maquinas compativeis; alguma maquina recebe
        ao menos ceil(n_lotes / |FJ_f|) lotes de duracao tempo_f.
    """
    L = max(T)
    for fam, produtos_fam in produtos_por_familia.items():
        peso_total = sum(peso[p] for p in produtos_fam)
        maqs = maquinas_familia[fam]
        maior_capacidade = max(capacidade[m] for m in maqs)
        n_lotes = math.ceil(peso_total / maior_capacidade)
        L = max(L, tempo_proc[fam] * math.ceil(n_lotes / len(maqs)))
    return L


# =============================================================================
# Problema Mestre
# =============================================================================

def cria_master(lotes_validos, produtos, A, T, L, compat, maquinas, lotes_da_classe,
                familia_lote, produtos_por_familia, fortalecer=True, ub=None):
    """
    min theta
    s.a. sum_n A_in x_n = 1                      (19)
         theta >= L, theta inteiro (todos os tempos sao inteiros => Cmax inteiro)
         [fortalecer] para todo subconjunto M' de maquinas:
              |M'| * theta >= sum_{n : FJ(n) subconjunto de M'} T_n x_n
         (a carga dos lotes que so podem ir para M' se divide entre |M'| maquinas)

    Codificacao unaria das contagens por classe (usada pelo corte 'classe'):
         sum_{n in c} x_n = sum_l w_{c,l},   w_{c,l} >= w_{c,l+1},   w binaria
         => w_{c,l} = 1  se e somente se  x usa ao menos l lotes da classe c.
    """
    modelo = Model("Master")
    modelo.hideOutput()

    N = range(len(lotes_validos))
    X = [modelo.addVar(f"X{n}", vtype="B") for n in N]
    # ub (opcional): limite superior conhecido para Cmax. Alem de podar a arvore, aperta as
    # desigualdades de carga (sum T_n x_n <= |M'| * ub) ja na propagacao.
    theta = modelo.addVar("theta", vtype="I", lb=L, ub=ub)

    for i in range(len(produtos)):
        modelo.addCons(quicksum(X[n] * A[n][i] for n in N) == 1, f"produto_{i + 1}")

    W = []
    for c, lotes_c in enumerate(lotes_da_classe):
        # no maximo um lote por produto da familia pode estar em uso simultaneamente
        M = min(len(lotes_c), len(produtos_por_familia[familia_lote[lotes_c[0]]]))
        w = [modelo.addVar(f"W{c},{l + 1}", vtype="B") for l in range(M)]
        modelo.addCons(quicksum(X[n] for n in lotes_c) == quicksum(w), f"classe_{c}")
        for l in range(M - 1):
            modelo.addCons(w[l] >= w[l + 1])
        W.append(w)

    n_validas = 0
    if fortalecer:
        J = range(len(maquinas))
        for r in range(1, len(maquinas) + 1):
            for sub in combinations(J, r):
                S = frozenset(sub)
                ns = [n for n in N if compat[n] <= S]
                if ns:
                    modelo.addCons(len(S) * theta >= quicksum(T[n] * X[n] for n in ns),
                                   f"carga_{''.join(maquinas[j] for j in sub)}")
                    n_validas += 1

    modelo.setObjective(theta, "minimize")
    return modelo, X, theta, W, n_validas


# =============================================================================
# Subproblema (com cache por classe de lotes)
# =============================================================================

def cria_sub_por_lote(maquinas, lotes_utilizados, compat, T):
    """
    Subproblema na forma do TCC (uma binaria por lote e maquina):
    min Cmax
    s.a. sum_{j in FJ(u)} y_uj = 1     para todo u em U           (22)
         sum_u T_u y_uj <= Cmax        para toda maquina j        (24)
    As restricoes (23) e (25) sao impostas pelo dominio: y_uj so existe se j e compativel.
    Sofre de simetria: lotes da mesma classe sao intercambiaveis e o SCIP demora para provar
    otimalidade (ex.: instancia 55 com lotes unitarios, > 60 s). Mantido apenas para comparacao.
    """
    modelo = Model("Sub")
    modelo.hideOutput()

    y = {}
    for u in lotes_utilizados:
        for j in compat[u]:
            y[(u, j)] = modelo.addVar(f"Y{u},{j}", vtype="B")

    Cmax = modelo.addVar("Cmax", vtype="I", lb=0)

    for u in lotes_utilizados:
        modelo.addCons(quicksum(y[(u, j)] for j in compat[u]) == 1)

    for j in range(len(maquinas)):
        termos = [y[(u, j)] * T[u] for u in lotes_utilizados if j in compat[u]]
        if termos:
            modelo.addCons(quicksum(termos) <= Cmax)

    modelo.setObjective(Cmax, "minimize")
    return modelo, y, Cmax


def cria_sub(maquinas, lotes_utilizados, compat, T, classe_lote, lotes_da_classe):
    """
    Subproblema agregado por classe, equivalente a (22)-(25): lotes da mesma classe tem o mesmo
    tempo e as mesmas maquinas compativeis, entao basta decidir QUANTOS lotes de cada classe
    vao para cada maquina.
        n_cj  : numero de lotes da classe c alocados a maquina j (inteira)
        sum_{j in FJ(c)} n_cj = k_c              (k_c = lotes da classe c em U)
        sum_c T_c n_cj <= Cmax                  para toda maquina j
    Elimina a simetria e resolve em milissegundos.
    """
    contagem = {}
    for u in lotes_utilizados:
        contagem[classe_lote[u]] = contagem.get(classe_lote[u], 0) + 1

    modelo = Model("Sub")
    modelo.hideOutput()

    n = {}
    for c, k in contagem.items():
        for j in compat[lotes_da_classe[c][0]]:
            n[(c, j)] = modelo.addVar(f"N{c},{j}", vtype="I", lb=0, ub=k)

    Cmax = modelo.addVar("Cmax", vtype="I", lb=0)

    for c, k in contagem.items():
        modelo.addCons(quicksum(n[(c, j)] for j in compat[lotes_da_classe[c][0]]) == k)

    for j in range(len(maquinas)):
        termos = [T[lotes_da_classe[c][0]] * n[(c, j)] for c in contagem if (c, j) in n]
        if termos:
            modelo.addCons(quicksum(termos) <= Cmax)

    modelo.setObjective(Cmax, "minimize")
    return modelo, n, Cmax


class Subproblema:
    """Resolve Q(x) e guarda o resultado por 'assinatura' (contagem de lotes por classe)."""

    def __init__(self, maquinas, compat, T, classe_lote, lotes_da_classe, por_lote=False):
        self.maquinas = maquinas
        self.compat = compat
        self.T = T
        self.classe_lote = classe_lote
        self.lotes_da_classe = lotes_da_classe
        self.n_classes = len(lotes_da_classe)
        self.por_lote = por_lote
        self.cache = {}
        self.chamadas = 0
        self.resolvidos = 0
        self.tempo = 0.0

    def assinatura(self, U):
        cont = [0] * self.n_classes
        for u in U:
            cont[self.classe_lote[u]] += 1
        return tuple(cont)

    def _modelo(self, U):
        if self.por_lote:
            return cria_sub_por_lote(self.maquinas, U, self.compat, self.T)
        return cria_sub(self.maquinas, U, self.compat, self.T, self.classe_lote, self.lotes_da_classe)

    def resolve(self, U):
        self.chamadas += 1
        chave = self.assinatura(U)
        if chave in self.cache:
            return self.cache[chave]

        inicio = time.time()
        modelo, _, Cmax = self._modelo(U)
        modelo.optimize()
        if modelo.getStatus() != "optimal":
            raise RuntimeError(f"Subproblema terminou com status {modelo.getStatus()}")
        Q = round(modelo.getObjVal())          # tempos inteiros => Cmax inteiro
        self.tempo += time.time() - inicio
        self.resolvidos += 1
        self.cache[chave] = Q
        return Q

    def alocacao(self, U):
        """Reotimiza o subproblema de U e devolve {lote: maquina} (usado so no relatorio final)."""
        modelo, variaveis, Cmax = self._modelo(U)
        modelo.optimize()
        if self.por_lote:
            return {u: self.maquinas[j] for (u, j), var in variaveis.items() if modelo.getVal(var) > 0.5}
        # expande as contagens n_cj para lotes concretos
        aloc = {}
        por_classe = {}
        for u in U:
            por_classe.setdefault(self.classe_lote[u], []).append(u)
        for (c, j), var in variaveis.items():
            for _ in range(int(round(modelo.getVal(var)))):
                aloc[por_classe[c].pop()] = self.maquinas[j]
        return aloc


# =============================================================================
# Cortes de otimalidade
# =============================================================================

def corte_classico(X, theta, U, Q, L):
    """
    Corte inteiro L-shaped (Laporte & Louveaux) - equacao (27) do TCC, reescrita:
        theta >= Q - (Q - L) * [ sum_{n in U} (1 - x_n) + sum_{n not in U} x_n ]
    Em x = x_barra o colchete vale 0 (theta >= Q); em qualquer outro x vale >= 1 (theta >= algo <= L).
    """
    U_set = set(U)
    distancia = quicksum(1 - X[n] for n in U) + quicksum(X[n] for n in range(len(X)) if n not in U_set)
    return theta >= Q - (Q - L) * distancia


def corte_classe(W, theta, U, Q, L, classe_lote):
    """
    Corte por classe (mais forte que o classico). Como Q depende so das contagens k_c(x) de
    lotes por classe e e monotono nessas contagens, vale:
        theta >= Q - (Q - L) * sum_{c : k_c > 0} (1 - w_{c, k_c})
    onde k_c e a contagem em x_barra e w_{c,l} = 1 sse x usa ao menos l lotes da classe c.
    Se x usa ao menos tantos lotes de cada classe quanto x_barra, theta >= Q; caso contrario o
    lado direito cai para L ou menos. Elimina de uma vez todas as configuracoes que dominam
    x_barra (inclusive todas as simetricas a ela), nao apenas o ponto x_barra.
    """
    cont = {}
    for u in U:
        cont[classe_lote[u]] = cont.get(classe_lote[u], 0) + 1
    faltantes = quicksum(1 - W[c][k - 1] for c, k in cont.items())
    return theta >= Q - (Q - L) * faltantes


def gera_corte(tipo_corte, X, W, theta, U, Q, L, classe_lote):
    if tipo_corte == "classe":
        return corte_classe(W, theta, U, Q, L, classe_lote)
    return corte_classico(X, theta, U, Q, L)


# =============================================================================
# Metodo 1: Benders iterativo (mestre re-resolvido a cada corte)
# =============================================================================

def benders_iterativo(master, X, W, theta, subp, L, logger, tipo_corte, classe_lote,
                      tempo_limite, max_iter):

    inicio = time.time()
    UB = math.inf
    melhor_U = None
    LB = L
    iteracao = 0
    n_cortes = 0
    status = "otimo"

    while True:
        iteracao += 1
        restante = tempo_limite - (time.time() - inicio)
        if restante <= 0:
            status = "tempo"
            iteracao -= 1
            break
        master.setParam("limits/time", restante)
        master.optimize()

        if master.getStatus() not in ("optimal",):
            status = "tempo" if master.getStatus() == "timelimit" else f"mestre_{master.getStatus()}"
            logger.info(f"Mestre terminou com status {master.getStatus()} na iteracao {iteracao}.")
            iteracao -= 1
            break

        LB = round(master.getObjVal())
        valor_x = [master.getVal(X[n]) for n in range(len(X))]
        U = [n for n, v in enumerate(valor_x) if v > 0.5]

        Q = subp.resolve(U)
        if Q < UB - EPS:
            UB, melhor_U = Q, U

        logger.info(f"Iteracao {iteracao:4d} | LB (theta) = {LB:7.1f} | Q(x) = {Q:7.1f} | "
                    f"UB = {UB:7.1f} | lotes = {len(U):3d} | t = {time.time() - inicio:8.1f}s")

        if LB >= UB - EPS:
            break
        if iteracao >= max_iter:
            status = "max_iter"
            break

        master.freeTransform()
        master.addCons(gera_corte(tipo_corte, X, W, theta, U, Q, L, classe_lote), f"corte_{iteracao}")
        n_cortes += 1

    return dict(status=status, LB=LB, UB=UB, lotes=melhor_U, iteracoes=iteracao,
                cortes=n_cortes, tempo=time.time() - inicio)


# =============================================================================
# Metodo 2: Branch-and-check (uma unica arvore de B&B; cortes via constraint handler)
# =============================================================================

class CortesBenders(Conshdlr):
    """
    Constraint handler do SCIP que representa a restricao implicita  theta >= Q(x).

    - conscheck : dada uma solucao candidata (inteira), diz se theta >= Q(x).
    - consenfolp: chamado em nos cuja solucao do LP e inteira; se theta < Q(x), adiciona o
                  corte (27) ao problema (valido globalmente) e o no e reavaliado.
    - consenfops: idem para solucoes pseudo (sem LP); pede que o LP seja resolvido.
    - conslock  : informa ao SCIP que alterar qualquer x (nos dois sentidos) ou reduzir theta
                  pode violar a restricao (impede que o presolve fixe variaveis por dualidade).
    """

    def __init__(self, X, W, theta, subp, L, A, logger, tipo_corte, classe_lote, log_a_cada=25):
        super().__init__()
        self.X = X
        self.W = W
        self.A = A
        self.tipo_corte = tipo_corte
        self.classe_lote = classe_lote
        self.theta = theta
        self.subp = subp
        self.L = L
        self.logger = logger
        self.log_a_cada = log_a_cada
        self.n_cortes = 0
        self.n_verificacoes = 0
        self.UB = math.inf
        self.melhor_U = None
        self.inicio = time.time()

    def _particao_valida(self, U):
        """Cada produto em exatamente um lote (solucoes de heuristicas podem violar isso)."""
        if not U:
            return False
        n_produtos = len(self.A[0])
        return all(sum(self.A[n][i] for n in U) == 1 for i in range(n_produtos))

    def _avalia(self, solucao):
        U = [n for n, v in enumerate(self.X) if self.model.getSolVal(solucao, v) > 0.5]
        if not self._particao_valida(U):
            return False, U, 0.0
        Q = self.subp.resolve(U)
        valor_theta = self.model.getSolVal(solucao, self.theta)
        self.n_verificacoes += 1
        if Q < self.UB - EPS:
            self.UB, self.melhor_U = Q, U
            self.logger.info(f"  novo incumbente Q = {Q:.1f} com {len(U)} lotes "
                             f"(verificacao {self.n_verificacoes}, t = {time.time() - self.inicio:.1f}s)")
        return valor_theta < Q - EPS, U, Q

    def conscheck(self, constraints, solution, checkintegrality, checklprows, printreason, completely):
        viola, U, Q = self._avalia(solution)
        return {"result": SCIP_RESULT.INFEASIBLE if viola else SCIP_RESULT.FEASIBLE}

    def _entrega_incumbente(self, Q):
        """A solucao inteira atual com theta := Q(x) e factivel para o problema completo.
        Entrega-la ao SCIP da um limite primal imediato para a poda da arvore.
        (Percorre as variaveis ATIVAS do problema transformado: variaveis agregadas pelo
        presolve nao aceitam atribuicao direta de valor.)"""
        sol = self.model.createSol()
        for v in self.model.getVars(transformed=True):
            valor = Q if v.name == "t_theta" else self.model.getSolVal(None, v)
            self.model.setSolVal(sol, v, valor)
        self.model.trySol(sol)

    def consenfolp(self, constraints, nusefulconss, solinfeasible):
        viola, U, Q = self._avalia(None)
        if viola:
            self._entrega_incumbente(Q)
            self.model.addCons(gera_corte(self.tipo_corte, self.X, self.W, self.theta, U, Q,
                                          self.L, self.classe_lote))
            self.n_cortes += 1
            if self.n_cortes % self.log_a_cada == 0:
                self.logger.info(f"  {self.n_cortes} cortes | Q(x) = {Q:.1f} | UB = {self.UB:.1f} | "
                                 f"subproblemas resolvidos = {self.subp.resolvidos} | "
                                 f"t = {time.time() - self.inicio:.1f}s")
            return {"result": SCIP_RESULT.CONSADDED}
        return {"result": SCIP_RESULT.FEASIBLE}

    def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):
        viola, U, Q = self._avalia(None)
        return {"result": SCIP_RESULT.SOLVELP if viola else SCIP_RESULT.FEASIBLE}

    def conslock(self, constraint, locktype, nlockspos, nlocksneg):
        try:
            for v in self.X:
                self.model.addVarLocks(v, nlockspos + nlocksneg, nlockspos + nlocksneg)
            self.model.addVarLocks(self.theta, nlockspos, nlocksneg)
        except ReferenceError:
            # chamado tambem durante a liberacao do modelo, quando a referencia ja nao existe
            pass


def branch_and_check(master, X, W, theta, subp, L, A, logger, tipo_corte, classe_lote, tempo_limite):

    inicio = time.time()
    handler = CortesBenders(X, W, theta, subp, L, A, logger, tipo_corte, classe_lote)
    # prioridades abaixo das do handler 'linear' (-1000000): as restricoes lineares do mestre
    # sao verificadas/impostas antes, e so solucoes que sao particoes validas chegam aqui.
    master.includeConshdlr(handler, "Benders", "cortes de otimalidade de Benders",
                           sepapriority=0, enfopriority=-2000000, chckpriority=-2000000,
                           sepafreq=-1, propfreq=-1, eagerfreq=-1, maxprerounds=0,
                           delaysepa=False, delayprop=False, needscons=False)
    master.setParam("limits/time", tempo_limite)
    master.optimize()

    st = master.getStatus()
    if st == "optimal":
        status = "otimo"
        UB = round(master.getObjVal())
        melhor_U = [n for n in range(len(X)) if master.getVal(X[n]) > 0.5]
        LB = UB
    elif st == "infeasible":
        # so ocorre com --ub: nao existe configuracao com Cmax <= ub
        status = "infactivel_ub"
        LB = math.inf
        UB = handler.UB
        melhor_U = handler.melhor_U
    else:
        status = "tempo" if st == "timelimit" else f"mestre_{st}"
        LB = master.getDualbound()
        UB = handler.UB
        melhor_U = handler.melhor_U

    return dict(status=status, LB=LB, UB=UB, lotes=melhor_U, iteracoes=handler.n_verificacoes,
                cortes=handler.n_cortes, tempo=time.time() - inicio, nos=master.getNNodes())


# =============================================================================
# Programa principal
# =============================================================================

def main(nome_arquivo, metodo="bc", tipo_corte="classe", tempo_limite=600.0,
         max_iter=100000, fortalecer=True, verbose=False, sub_por_lote=False, ub=None):

    (inst, peso, familia_produto, capacidade, tempo_proc,
     maquinas_familia, familia, produtos_por_familia) = ler_instancia(nome_arquivo)
    T, P, lotes_validos, A, maquinas, produtos, familia_lote = cria_lotes(
        capacidade, peso, produtos_por_familia, tempo_proc, familia_produto, maquinas_familia)
    compat = maquinas_compativeis(lotes_validos, P, familia_lote, maquinas, maquinas_familia, capacidade)
    classe_lote, lotes_da_classe = classes_de_lotes(familia_lote, compat)
    L = limite_inferior(T, tempo_proc, produtos_por_familia, peso, maquinas_familia, capacidade)

    sufixo = f"{metodo}_{tipo_corte}"
    pasta_instancia = pasta_resultados / f"Resumo_Instancia_{inst}"
    pasta_instancia.mkdir(parents=True, exist_ok=True)
    logger = configura_logger(pasta_instancia, sufixo)
    logger.info("=" * 70)
    logger.info(f"METODO DE BENDERS - {'branch-and-check' if metodo == 'bc' else 'iterativo'}, corte {tipo_corte}")
    logger.info("=" * 70)
    logger.info(f"Instancia: {inst}")
    logger.info(f"Numero de produtos: {len(produtos)}")
    logger.info(f"Numero de maquinas: {len(maquinas)}")
    logger.info(f"Numero de familias: {len(familia)}")
    logger.info(f"Numero de lotes validos: {len(lotes_validos)}")
    logger.info(f"Numero de classes de lotes: {len(lotes_da_classe)}")
    logger.info(f"Limite inferior L: {L}")
    if ub is not None:
        logger.info(f"Limite superior imposto a theta (--ub): {ub}")

    inicio = time.time()
    master, X, theta, W, n_validas = cria_master(lotes_validos, produtos, A, T, L, compat, maquinas,
                                                 lotes_da_classe, familia_lote, produtos_por_familia,
                                                 fortalecer, ub)
    logger.info(f"Desigualdades validas no mestre: {n_validas}")
    if verbose:
        master.hideOutput(False)
    master.writeProblem(str(pasta_instancia / f"master_{inst}produtos_{sufixo}.lp"))

    subp = Subproblema(maquinas, compat, T, classe_lote, lotes_da_classe, por_lote=sub_por_lote)
    logger.info(f"Subproblema: {'por lote (formulacao do TCC)' if sub_por_lote else 'agregado por classe'}")

    if metodo == "bc":
        res = branch_and_check(master, X, W, theta, subp, L, A, logger, tipo_corte, classe_lote,
                               tempo_limite)
    else:
        res = benders_iterativo(master, X, W, theta, subp, L, logger, tipo_corte, classe_lote,
                                tempo_limite, max_iter)

    tempo_total = time.time() - inicio
    if res["status"] == "infactivel_ub":
        logger.info(f"Mestre infactivel: nao existe configuracao com Cmax <= {ub}. "
                    f"Logo o otimo e maior que {ub}.")
    gap = (res["UB"] - res["LB"]) / res["UB"] * 100 if 0 < res["UB"] < math.inf and res["LB"] < math.inf else math.inf

    logger.info("")
    logger.info("=" * 70)
    logger.info("RESULTADO FINAL")
    logger.info("=" * 70)
    logger.info(f"Status: {res['status']}")
    logger.info(f"Cmax (UB) = {res['UB']}   LB = {res['LB']}   gap = {gap:.2f}%")
    if res["lotes"] is not None:
        aloc = subp.alocacao(res["lotes"])
        logger.info(f"Lotes selecionados ({len(res['lotes'])}):")
        for u in res["lotes"]:
            logger.info(f"   lote {u:5d} | familia {familia_lote[u]} | T = {T[u]:4d} | P = {P[u]:6.1f} | "
                        f"maquina {aloc[u]} | produtos {lotes_validos[u]}")
    logger.info(f"Iteracoes / verificacoes = {res['iteracoes']}")
    logger.info(f"Cortes adicionados = {res['cortes']}")
    logger.info(f"Subproblemas: chamadas = {subp.chamadas}, resolvidos = {subp.resolvidos}, "
                f"tempo = {subp.tempo:.2f}s")
    if "nos" in res:
        logger.info(f"Nos de B&B = {res['nos']}")
    logger.info(f"Tempo total = {tempo_total:.4f} segundos")

    salva_resultados_csv(pasta_resultados / "resultados.csv", {
        "instancia": inst,
        "metodo": sufixo,
        "produtos": len(produtos),
        "maquinas": len(maquinas),
        "familias": len(familia),
        "lotes_validos": len(lotes_validos),
        "L": L,
        "status": res["status"],
        "iteracoes": res["iteracoes"],
        "cortes": res["cortes"],
        "LB": round(res["LB"], 4) if res["LB"] < math.inf else "",
        "UB": res["UB"],
        "gap_pct": round(gap, 4) if gap < math.inf else "",
        "subproblemas_resolvidos": subp.resolvidos,
        "tempo_segundos": round(tempo_total, 4),
        "numero_lotes": len(res["lotes"]) if res["lotes"] is not None else "",
        "lotes_selecionados": str(res["lotes"]) if res["lotes"] is not None else "",
    })
    logger.info("Execucao finalizada.")
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decomposicao de Benders para formacao de lotes.")
    parser.add_argument("--instancia", default="30",
                        help="numero de produtos da instancia (ex.: 30) ou caminho do arquivo")
    parser.add_argument("--metodo", choices=["bc", "iterativo"], default="bc",
                        help="bc = branch-and-check (padrao); iterativo = mestre re-resolvido a cada corte")
    parser.add_argument("--corte", choices=["classico", "classe"], default="classe",
                        help="classico = eq. 27 do TCC (um ponto por corte); classe = corte por classe de lotes (padrao)")
    parser.add_argument("--tempo", type=float, default=10000.0, help="limite de tempo em segundos")
    parser.add_argument("--max-iter", type=int, default=100000, help="limite de iteracoes (modo iterativo)")
    parser.add_argument("--sem-fortalecer", action="store_true",
                        help="nao adiciona as desigualdades validas de carga por conjunto de maquinas")
    parser.add_argument("--verbose", action="store_true", help="mostra a saida do SCIP no mestre")
    parser.add_argument("--ub", type=int, default=None,
                        help="limite superior conhecido para Cmax (theta <= ub no mestre)")
    parser.add_argument("--sub-por-lote", action="store_true",
                        help="usa o subproblema com uma binaria por lote/maquina (formulacao original, mais lenta)")
    args = parser.parse_args()

    # main(localiza_instancia(args.instancia), metodo=args.metodo, tipo_corte=args.corte,
    #      tempo_limite=args.tempo, max_iter=args.max_iter, fortalecer=not args.sem_fortalecer,
    #      verbose=args.verbose, sub_por_lote=args.sub_por_lote, ub=args.ub)
    
    main(localiza_instancia("30"), metodo=args.metodo, tipo_corte=args.corte,
         tempo_limite=args.tempo, max_iter=args.max_iter, fortalecer=not args.sem_fortalecer,
         verbose=args.verbose, sub_por_lote=args.sub_por_lote, ub=args.ub)
