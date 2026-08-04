from docplex.mp.model import Model
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

mod = Model("Scheduling")


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

    tempo_lote = tempo_proc[familia_produto[lote[0]]]
    T.append(tempo_lote)



for lote in lotes_validos:

    peso_lote = sum(peso[p] for p in lote)
    P.append(peso_lote)



# ----------------------------------------
# Variáveis
# ----------------------------------------

y = [
    [
        None for j in range(len(maquinas))
    ]
    for n in range(len(lotes_validos))
]


for n in range(len(lotes_validos)):

    for j in range(len(maquinas)):

        y[n][j] = mod.binary_var(
            name=f"Y{n},{j}"
        )


Cmax = mod.continuous_var(
    name="Cmax"
)



inicio = time.time()



# ----------------------------------------
# Restrições
# ----------------------------------------

# Cada produto em exatamente um lote

for i in range(len(produtos)):

    mod.add_constraint(
        sum(
            sum(
                y[n][j] * A[n][i]
                for j in range(len(maquinas))
            )
            for n in range(len(lotes_validos))
        )
        == 1
    )



# Compatibilidade família-máquina

for n, lote in enumerate(lotes_validos):

    for j, maquina in enumerate(maquinas):

        if maquina not in maquinas_familia[familia_produto[lote[0]]]:

            mod.add_constraint(
                y[n][j] == 0
            )



# Cmax

for j in range(len(maquinas)):

    mod.add_constraint(
        sum(
            y[n][j] * T[n]
            for n in range(len(lotes_validos))
        )
        <= Cmax
    )



# Capacidade

for n in range(len(lotes_validos)):

    for j in range(len(maquinas)):

        mod.add_constraint(
            P[n] * y[n][j]
            <= capacidade[maquinas[j]]
        )



# ----------------------------------------
# Função objetivo
# ----------------------------------------

mod.minimize(Cmax)



# ----------------------------------------
# Exportar LP
# ----------------------------------------

mod.export_as_lp("modelo_cplex.lp")



# ----------------------------------------
# Resolver
# ----------------------------------------

solucao = mod.solve(log_output=True)



fim = time.time()



print(f"Tempo de execução: {fim-inicio:.4f} segundos")


if solucao:

    print(f"Cmax = {Cmax.solution_value} minutos")

else:

    print("Nenhuma solução encontrada")



print("")


for j in maquinas:

    print("--------------------------------")
    print(f"Máquina {j}")

    for n, lote in enumerate(lotes_validos):

        if y[n][maquinas.index(j)].solution_value > 0.5:

            print(
                f"Lote {lote} | Tempo {T[n]}"
            )


print("--------------------------------")