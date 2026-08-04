from pyscipopt import Model, quicksum

scip = Model(problemName="Exercício 5(a) Lista Dualidade")

#Parâmetros
N_alimentos = 6
custoKG = [35, 30, 60, 50, 27, 22]
VitA = [1, 0, 2, 2, 1, 2]
VitC = [0, 1, 3, 1, 3, 2]

#Variáveis
X = [None for i in range(N_alimentos)] #Custo
for i in range(N_alimentos):
    X[i] = scip.addVar(vtype = 'C', lb = 0, ub = None, name = f"Kg do alimento {i}")

#Restrições
restr1 = scip.addCons(quicksum(VitA[i] * X[i] for i in range(N_alimentos)) >= 9)
restr2 = scip.addCons(quicksum(VitC[i] * X[i] for i in range(N_alimentos)) >= 19)

#Função Objetivo
scip.setObjective(quicksum(custoKG[i] * X[i] for i in range(N_alimentos)), sense='minimize')

#Otimização
scip.optimize()

#Resultados
z = scip.getObjVal()
Xval = [scip.getVal(X[i]) for i in range(N_alimentos)]


print("\n---------------------------------------------------")
print(f"Valor da função objetivo: {z}\n")
for i in range(N_alimentos):
    print(f"Quantidade do alimento {i + 1}: {Xval[i]} Kg")
print("---------------------------------------------------\n")

#Dual
pi1 = scip.getDualsolLinear(restr1)
pi2 = scip.getDualsolLinear(restr2)

print(f"Valor da pírula A: {pi1:.2f} reais")
print(f"Valor da pírula C: {pi2:.2f} reais")
print("---------------------------------------------------\n")

#Exportação
scip.writeProblem(filename="resultado_dieta.lp")