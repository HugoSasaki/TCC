from pyscipopt import Model, quicksum
import math

def cria_master(lotes_validos, produtos, A, L, ub, T):

    modelo = Model("Master")
    modelo.hideOutput()

    X = [None for n in range(len(lotes_validos))]
    for n in range(len(X)):
        X[n] = modelo.addVar(f"X{n}", vtype="B")

    theta = modelo.addVar("theta", vtype="C")

    for i in range(len(produtos)):
        modelo.addCons(quicksum(X[n] * A[n][i] for n in range(len(lotes_validos))) == 1)

    modelo.addCons(theta >= L)

    for n in range(len(X)):
        modelo.addCons(theta >= X[n] * T[n])

    # modelo.addCons(theta <= ub)

    modelo.setObjective(theta, "minimize")

    return(modelo, X, theta)


def cria_sub(maquinas, lotes_utilizados, maquinas_familia, capacidade, T, P, familia_lote, ub):

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
