from pyscipopt import Model, quicksum
import os

scip = Model(problemName="Solução do Vicente")

#Instâncias
pasta = "Documentos\\Instancias"
inst = [os.path.join(pasta, arq) for arq in os.listdir(pasta)]

#Parâmetros
J = []
M = []
K = []
F = []
FJ = []
MF = []
s = []
P = []
S = []
W = []

#Variáveis
x = [[[None for j in range(J)] for k in range(K)] for m in range(M)]
for j in range(len(x)):
    for k in range(len(x[0])):
        for m in range(len(x[0][0])):
            x[j][k][m] = scip.addVar(vtype="B", name=f"x{j}{k}{m}")

y = [[[None for k in range(K)] for m in range(M)] for f in range(F)]
for k in range(len(y)):
    for m in range(len(y[0])):
        for f in range(len(y[0][0])):
            y[k][m][f] = scip.addVar(vtype="B", name=f"x{k}{m}{f}")

Cmax = scip.addVar(vtype="C", name="Makespan")

#Função Objetivo
scip.setObjective(Cmax, sense="Minimize")

#Restrições
for j in range(J): #(1)
    scip.addCons(quicksum(quicksum(x[j][k][m] for m in range(M)) for k in range(K)) == 1)

for k in range(K): #(2)
    for m in range(M):
        for f in range(F):
            if m not in MF[f]:
                scip.addCons(y[k][m][f] == 0)

for k in range(K): #(3)
    for m in range(M):
        scip.addCons(quicksum(s[j] * x[j][k][m] for j in range(J)) <= S[m])

for m in range(M): #(4)
    scip.addCons(Cmax >= quicksum(quicksum(P[f] * y[k][m][f] for k in range(K)) for f in range(F)))

for m in range(M): #(5)
    for k in range(K):
        scip.addCons(quicksum(y[k][m][f] for f in range(F)) <= 1)

for f in range(F): #(6)
    for k in range(K):
        for m in range(M):
            scip.addCons(quicksum(x[j][k][m] for j in range(J) if FJ[j] == f) <= W[f] * y[k][m][f])

#Otimização
scip.optimize()
