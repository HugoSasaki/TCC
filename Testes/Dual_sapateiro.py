from pyscipopt import Model, SCIP_PARAMSETTING

# Criando um objeto do tipo Model()
scip = Model()

scip.setPresolve(SCIP_PARAMSETTING.OFF)
scip.setHeuristics(SCIP_PARAMSETTING.OFF)
scip.disablePropagation()

# Declarando as variaveis
x1 = scip.addVar(vtype = 'C', lb = 0, ub = None, name = 'x1')
x2 = scip.addVar(vtype = 'C', lb = 0, ub = None, name = 'x2')

# Restricoes
res1 = scip.addCons(10*x1 + 12*x2 <= 60, name = "res1")
res2 = scip.addCons(2*x1  + x2    <= 6,  name = "res2")

# Funcao objetivo
scip.setObjective(5*x1 + 2*x2, sense = "maximize")

# Otimizando o modelo
scip.optimize()

# Coletando os valores duais:
pi1 = scip.getDualsolLinear(res1)
pi2 = scip.getDualsolLinear(res2)

print("pis",pi1,pi2)