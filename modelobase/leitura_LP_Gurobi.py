import gurobipy as gp
from gurobipy import GRB

modelo = gp.read("C:\\TCC\\Resultados\\Teste_X_5.lp")

modelo.optimize()