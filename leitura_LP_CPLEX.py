import cplex

modelo = cplex.Cplex(r"C:\TCC\Resultados\resultado_60.lp")

modelo.solve()

print(modelo.solution.get_objective_value())