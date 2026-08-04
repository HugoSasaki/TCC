from pyscipopt import Model

scip = Model(problemName = "Problema do Sapateiro")

#Declaração de variàveis
x1 = scip.addVar(vtype = 'C', lb = 0, ub = None, name = 'x1')
x2 = scip.addVar(vtype = 'C', lb = 0, ub = None, name = 'x2')

#Restrições
scip.addCons(10*x1 + 12*x2 <= 60, name = 'restr1')
scip.addCons(2*x1 + x2 <= 6, name = 'restr2')

#Função Objetivo
scip.setObjective(5*x1 + 2*x2, sense = "maximize")

#Otimizando o modelo
scip.optimize()

#Resultados
z = scip.getObjVal()
x1_val = scip.getVal(x1)
x2_val = scip.getVal(x2)

print("Valor objetivo :{}\nx1: {}\nx2: {}".format(z, x1_val, x2_val))

scip.writeProblem(filename = "resultado_sapateiro.lp")