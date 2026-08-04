from pyscipopt import Model, quicksum
from itertools import combinations
import time

arquivo = r"C:\TCC\Documentos\Instancias\Instância Teste 5 jobs.txt"

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

        # identificar seção
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

        # -------------------
        # PRODUTOS
        # -------------------
        if secao == "produtos":
            nome, p, f = linha.split("/")

            peso[produto_id] = float(p)
            familia_produto[produto_id] = int(f)

            produto_id += 1

        # -------------------
        # MÁQUINAS
        # -------------------
        elif secao == "maquinas":
            maq, cap = linha.split("/")

            capacidade[maq] = float(cap)

        # -------------------
        # FAMÍLIAS
        # -------------------
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

inst, peso, familia_produto, capacidade, tempo_proc, maquinas_familia, familia, produtos_por_familia = ler_instancia(arquivo)

mod = Model("Scheduling")

T = []
P = []
lotes_validos = []
A = []
maquinas = list(capacidade.keys())
produtos = list(peso.keys())

maior_capacidade = max(capacidade.values())

for fam, produtos_fam in produtos_por_familia.items():
    for r in range(1, len(produtos_fam) + 1):
        for lote in combinations(produtos_fam, r):

            if sum(peso[p] for p in lote) <= maior_capacidade:
                lotes_validos.append(lote)

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

#Variáveis------------------------------------------------------------------------------

#(Se lote n vai para a máquina j)
y = [[None for j in range(len(maquinas))] for n in range(len(lotes_validos))]
for n in range(len(y)):
    for j in range(len(maquinas)):
        y[n][j] = mod.addVar(f"Y{n},{j}", "binary")

Cmax = mod.addVar("Cmax", "continuous")

x = [None for n in range(len(lotes_validos))]
for n in range(len(x)):
    x[n] = mod.addVar(f"X{n}", "binary")

#Restrições-----------------------------------------------------------------------------

for i in range(len(produtos)):
    con1 = mod.addCons(quicksum(x[n] * A[n][i] for n in range(len(lotes_validos))) == 1)

for n, lote in enumerate(lotes_validos):
    for j, maquina in enumerate(maquinas):
        if maquina not in maquinas_familia[familia_produto[lote[0]]]:
            con2 = mod.addCons(y[n][j] == 0)

for j in range(len(maquinas)):
    con3 = mod.addCons(quicksum(y[n][j] * T[n] for n in range(len(lotes_validos))) <= Cmax)

for n in range(len(lotes_validos)):
    for j in range(len(maquinas)):
        con4 = mod.addCons(P[n] * y[n][j] <= capacidade[maquinas[j]])

mod.setObjective(Cmax, "minimize")

mod.writeProblem(filename = f"Resultados\\Teste_X_{inst}.lp")

mod.hideOutput(False)

mod.optimize()

print(mod.getStatus())
print(mod.getVal(Cmax))
