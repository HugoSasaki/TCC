import gurobipy as gp
from gurobipy import GRB
from itertools import combinations
import time


arquivo = r"C:\TCC\Documentos\Instancias\Instância Teste 50 Jobs.txt"


# ----------------------------------------
# Leitura da instância (mantido igual)
# ----------------------------------------

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

            capacidade[maq] = int(cap)


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


# ----------------------------------------
# Construção dos lotes
# ----------------------------------------

mod = gp.Model("Scheduling")


T = []
P = []
lotes_validos = []
A = []

maquinas = list(capacidade.keys())
produtos = list(peso.keys())

maior_capacidade = max(capacidade.values())


for fam, produtos_fam in produtos_por_familia.items():

    for r in range(1, len(produtos_fam)+1):

        for lote in combinations(produtos_fam, r):

            if sum(peso[p] for p in lote) <= maior_capacidade:
                lotes_validos.append(lote)



for lote in lotes_validos:

    linha = [
        1 if n in lote else 0
        for n in produtos
    ]

    A.append(linha)



for lote in lotes_validos:

    T.append(
        tempo_proc[familia_produto[lote[0]]]
    )


for lote in lotes_validos:

    P.append(
        sum(peso[p] for p in lote)
    )


# ----------------------------------------
# Variáveis
# ----------------------------------------

y = [
    [
        None for j in range(len(maquinas))
    ]
    for n in range(len(lotes_validos))
]


for n in range(len(y)):

    for j in range(len(maquinas)):

        y[n][j] = mod.addVar(
            vtype=GRB.BINARY,
            name=f"Y{n},{j}"
        )


Cmax = mod.addVar(
    vtype=GRB.CONTINUOUS,
    name="Cmax"
)


mod.update()


inicio = time.time()


# ----------------------------------------
# Restrições
# ----------------------------------------

# Cada produto deve estar em exatamente um lote/máquina

for i in range(len(produtos)):

    mod.addConstr(
        gp.quicksum(
            gp.quicksum(
                y[n][j] * A[n][i]
                for j in range(len(maquinas))
            )
            for n in range(len(lotes_validos))
        )
        == 1
    )



# Máquina compatível com família

for n, lote in enumerate(lotes_validos):

    for j, maquina in enumerate(maquinas):

        if maquina not in maquinas_familia[familia_produto[lote[0]]]:

            mod.addConstr(
                y[n][j] == 0
            )



# Minimização do maior tempo de máquina

for j in range(len(maquinas)):

    mod.addConstr(
        gp.quicksum(
            y[n][j] * T[n]
            for n in range(len(lotes_validos))
        )
        <= Cmax
    )



# Capacidade da máquina

for n in range(len(lotes_validos)):

    for j in range(len(maquinas)):

        mod.addConstr(
            P[n] * y[n][j]
            <= capacidade[maquinas[j]]
        )


# ----------------------------------------
# Função objetivo
# ----------------------------------------

mod.setObjective(
    Cmax,
    GRB.MINIMIZE
)


# ----------------------------------------
# Otimização
# ----------------------------------------

mod.optimize()


fim = time.time()


print(f"Tempo de execução: {fim-inicio:.4f} segundos")

print("Status:",
      mod.Status)


if mod.Status == GRB.OPTIMAL:

    print(f"Cmax = {Cmax.X} minutos")

else:

    print("Solução não ótima encontrada")


print("")


for j in maquinas:

    print("--------------------------------")
    print(f"Máquina {j}")

    for n, lote in enumerate(lotes_validos):

        if y[n][maquinas.index(j)].X > 0.5:

            print(
                f"Lote {lote} | Tempo {T[n]}"
            )


print("--------------------------------")