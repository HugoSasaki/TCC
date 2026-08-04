from pyscipopt import Model, quicksum
scip = Model(problemName = "Problema do Transporte")


ll_custos      = [[2.5,1.7,1.8],[2.5,1.8,1.4]]
l_demandas     = [300,300,300]
l_capacidades  = [350,650]
n_fabricas  = 2
n_depositos = 3

# Variáveis
var_list    = [ [None for j in range(n_depositos)] for i in range(n_fabricas)] 
for i in range(len(var_list)):
  for j in range(len(var_list[0])):
    var_list[i][j] =  scip.addVar(vtype = 'C', name = f"x_{i}_{j}")

# Restrições de capacidade
for i in range(n_fabricas):
  scip.addCons(quicksum(var_list[i][j] for j in range(n_depositos)) <= l_capacidades[i], name = "cap. {}".format(i))
  
# Restrições de demanda
for j in range(n_depositos):
  scip.addCons(quicksum(var_list[i][j] for i in range(n_fabricas))  >= l_demandas[i], name = "dem. {}".format(j))

# Função objetivo
scip.setObjective( quicksum(ll_custos[i][j] * var_list[i][j] for i in range(n_fabricas) for j in range(n_depositos)), sense = "minimize")

scip.optimize()
z = scip.getObjVal()
print(z)

scip.writeProblem(filename = "resultado_transporte.lp", trans = False, genericnames = False)
