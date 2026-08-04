from pyscipopt import Model, quicksum
from itertools import combinations

mod = Model()

#Conjuntos------------------------------------------------------------------------------

produtos = {
    "produto_1": 2.5,
    "produto_2": 7.0,
    "produto_3": 1.2,
    "produto_4": 10.0,
    "produto_5": 4.5,
}
lotes_validos = []
A = []
maquinas = {
    "A": 30,
    "B": 25,
    "C": 20,
    "D": 50
}
  
#Parametros-----------------------------------------------------------------------------

pesos = [float(peso) for peso in produtos.values()]

capacidades = [int(cap) for cap in maquinas.values()]

tempos = [
    45,
    45,
    45,
    45,
    45 
]

T = []
P = []

#Lotes----------------------------------------------------------------------------------

maior_capacidade = max(capacidades)

for r in range(1, len(produtos) + 1):
    for lotes in combinations(produtos, r):

        if sum(pesos[i] for i in range(len(lotes))) <= maior_capacidade:
            lotes_validos.append(lotes)

#Binariza :)
for lotes in lotes_validos:
    linha = [1 if n in lotes else 0 for n in produtos]
    A.append(linha)

#tempos
for n in range(len(lotes_validos)):
    tempo_lote = sum(A[n][i] * tempos[i] for i in range(len(produtos)))
    T.append(tempo_lote)

#pesos
for n in range(len(lotes_validos)):
    peso_lote = sum(A[n][i] * pesos[i] for i in range(len(produtos)))
    P.append(peso_lote)

#Variáveis------------------------------------------------------------------------------

#(Se lote n vai para a máquina j)
y = [[None for j in range(len(maquinas))] for n in range(len(lotes_validos))]
for n in range(len(y)):
    for j in range(len(maquinas)):
        y[n][j] = mod.addVar(f"Y{n},{j}", "binary")

Cmax = mod.addVar("Cmax", "continuous")

#Restrições-----------------------------------------------------------------------------

for i in range(len(produtos)):
    con1 = mod.addCons(quicksum(quicksum(y[n][j] * A[n][i] for j in range(len(maquinas))) for n in range(len(lotes_validos))) == 1, "cons1")

for j in range(len(maquinas)):
    con2 = mod.addCons(quicksum(y[n][j] * T[n] for n in range(len(lotes_validos))) <= Cmax, "cons2")

for n in range(len(lotes_validos)):
    for j in range(len(maquinas)):
        con3 = mod.addCons(P[n] * y[n][j] <= capacidades[j], "cons3")

#Função Objetivo-------------------------------------------------------------------------

mod.setObjective(Cmax, "minimize")

#Otimização------------------------------------------------------------------------------

mod.optimize()

#Resultados------------------------------------------------------------------------------

valor = mod.getVal(Cmax)
print(f"Cmax = {valor} minutos")

mod.writeProblem(filename = "resultado_5.lp", trans = False, genericnames = False)
