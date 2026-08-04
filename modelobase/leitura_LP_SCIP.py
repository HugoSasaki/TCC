from pyscipopt import Model

scip = Model()

scip.readProblem("C:\\TCC\\Resultados\\resultado_60.lp")

scip.optimize()
