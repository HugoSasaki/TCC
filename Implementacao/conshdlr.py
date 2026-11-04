from benders import cria_sub, resolve_sub

from pyscipopt import quicksum, Conshdlr, SCIP_RESULT

class BendersLazyCuts(Conshdlr):

    def __init__(self, master, X, theta, lotes_validos, maquinas, maquinas_familia, capacidade, T, P, familia_lote, L, logger, ub, cache_Q):
        
        self.master = master
        self.X = X
        self.theta = theta
        self.lotes_validos = lotes_validos
        self.maquinas = maquinas
        self.maquinas_familia = maquinas_familia
        self.capacidade = capacidade
        self.T = T
        self.P = P
        self.familia_lote = familia_lote
        self.L = L
        self.logger = logger
        self.numero_cortes = 0
        self.cache_Q = cache_Q
        self.cache_LB = L
        self.cache_UB = float("inf")
        self.ub = ub

    def _avalia(self, sol):
      
        x_vals = [round(self.master.getSolVal(sol, self.X[n])) for n in range(len(self.X))]
        U = tuple(n for n, v in enumerate(x_vals) if v > 0.5)

        if not U:
            return False, U, None, None

        if U not in self.cache_Q:
            sub, y, Cmax = cria_sub(self.maquinas, U, self.maquinas_familia,
                                     self.capacidade, self.T, self.P, self.familia_lote, self.ub)
            self.cache_Q[U] = resolve_sub(sub)

        Q = self.cache_Q[U]
        theta_val = self.master.getSolVal(sol, self.theta)

        if Q <= self.cache_UB:
            self.cache_UB = Q

        lb_hist = self.master.getLowerbound()
        if lb_hist >= self.cache_LB:
            self.cache_LB = lb_hist

        self.cache_GAP = ((self.cache_UB - self.cache_LB) / self.cache_UB) * 100
        violado = theta_val < Q - 1e-6
        return violado, U, Q, theta_val

    def _corte(self, U, Q):

        n_lotes = len(self.X)
        dentro_de_U = quicksum(self.X[n] for n in U)
        fora_de_U = quicksum(self.X[n] for n in range(n_lotes) if n not in U)

        return self.theta >= (Q - self.L) * (dentro_de_U - fora_de_U) - (Q - self.L) * (len(U) - 1) + self.L

    def _tenta_cortar(self, sol):

        violado, U, Q, theta_val = self._avalia(sol)

        if not violado:
            return {"result": SCIP_RESULT.FEASIBLE}

        self.master.addCons(self._corte(U, Q))
        self.numero_cortes += 1
        self.logger.info(
            f'''[lazy] corte {self.numero_cortes}
                lotes usados = {len(U)}
                Q = {Q:.2f}
                theta = {theta_val:.2f}
                UB = {self.cache_UB}
                LB = {self.cache_LB}
                Gap = {self.cache_GAP:.2f}%
                '''
        )

        return {"result": SCIP_RESULT.CONSADDED}

    def consenfolp(self, constraints, nusefulconss, solinfeasible):
        x = [self.master.getSolVal(None, v) for v in self.X]
        if any(1e-6 < v < 1 - 1e-6 for v in x):   # defesa: fracionária não é comigo
            return {"result": SCIP_RESULT.FEASIBLE}
        return self._tenta_cortar(None)

    def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):

        return self._tenta_cortar(None)

    def conscheck(self, constraints, solution, checkintegrality, checklprows, printreason, completely):

        violado, *_ = self._avalia(solution)
        return {"result": SCIP_RESULT.INFEASIBLE if violado else SCIP_RESULT.FEASIBLE}

    def conslock(self, constraint, locktype, nlockspos, nlocksneg):

        for x in self.X:
            self.master.addVarLocks(x, nlockspos + nlocksneg, nlockspos + nlocksneg)
        self.master.addVarLocks(self.theta, nlockspos + nlocksneg, nlockspos + nlocksneg)
