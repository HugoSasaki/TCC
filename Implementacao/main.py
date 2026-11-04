from conshdlr import BendersLazyCuts
from benders import cria_master, cria_sub, resolve_master, resolve_sub, lowerBound
from leitura_arquivo import ler_instancia
from cria_lotes import cria_lotes
from output import configura_logger, salva_resultados_csv

from pyscipopt import quicksum
from pathlib import Path
import time


resultado_alns = None
arquivo = Path(__file__).parent.parent / "Instancias" / "Instância Teste 5 jobs.txt"
    
# caminho = Path(__file__).parent.parent / "Instancias"
# arquivos = sorted(caminho.glob("*.txt"), key=lambda arquivo: arquivo.stat().st_size)
# for arquivo in arquivos:
#     main(arquivo)

pasta_resultados = Path(__file__).parent.parent / "Resultados" / "Benders"
pasta_resultados.mkdir(parents=True, exist_ok=True)

inst, peso, familia_produto, capacidade, tempo_proc, maquinas_familia, familia, produtos_por_familia = ler_instancia(arquivo)
T, P, lotes_validos, A, maquinas, produtos, familia_lote = cria_lotes(capacidade, peso, produtos_por_familia, tempo_proc, familia_produto, maquinas_familia)
L = lowerBound(tempo_proc, produtos_por_familia, peso, maquinas_familia, capacidade)

#==============================================================================================
#Output Inicial ================================================================================

pasta_instancia = (pasta_resultados / f"Resumo_Instancia_{inst}")
pasta_instancia.mkdir(parents=True, exist_ok=True)
logger = configura_logger(pasta_instancia)
logger.info("=" * 60)
logger.info("MÉTODO DE BENDERS")
logger.info("=" * 60)
logger.info(f"Instância: {inst}")
logger.info(f"Número de produtos: {len(produtos)}")
logger.info(f"Número de máquinas: {len(maquinas)}")
logger.info(f"Número de lotes válidos: {len(lotes_validos)}")
logger.info(f"Número de famílias: {len(familia)}")
logger.info("=" * 60)
#=============================================================================

inicio = time.time()
    
master, X, theta = cria_master(lotes_validos, produtos, A, L, resultado_alns, T)
melhor_Z = 0
melhor_Q = float("inf")
cache_Q = {}
inicio_master_loop = time.time()

master.freeTransform()
for n in range(len(X)):
    master.addCons(theta >= X[n]*T[n])

#=============================================================================================
# Loop Inicial ==============================================================================

while True:

    Z, valor_theta, valor_x = resolve_master(master, X, theta)
    U = tuple(n for n, v in enumerate(valor_x) if v == 1)

    if resultado_alns == None:
        ub = melhor_Q
    elif resultado_alns < melhor_Q:
        ub = resultado_alns

    if U not in cache_Q:
        sub, y, Cmax = cria_sub(maquinas, U, maquinas_familia, capacidade, T, P, familia_lote, resultado_alns)
        cache_Q[U] = resolve_sub(sub)

    Q = cache_Q[U]

    if Z > melhor_Z:
        melhor_Z = Z
    if Q < melhor_Q:
        melhor_Q = Q

    gap = ((melhor_Q - melhor_Z)/melhor_Q) * 100
    fim_master_loop = time.time()
    tempo_master_loop = fim_master_loop - inicio_master_loop

    logger.info(
        f'''Tempo: {tempo_master_loop}
            Z = {Z}
            theta = {valor_theta} 
            Q = {Q}
            Gap = {gap:.2f}%
            U = {U}
            Número de lotes utilizados = {len(U)}
            '''
            )

    if Z >= Q - 1e-6 or gap <= 10 or tempo_master_loop > 10:
        break

    master.freeTransform()

    master.addCons(theta >= (Q - L) * (quicksum(X[n] for n in U) - quicksum(X[n] for n in range(len(lotes_validos)) if n not in U)) - (Q - L) * (len(U) - 1) + L)

#=====================================================================

if resultado_alns == None:
    resultado_alns = melhor_Q

master.freeTransform()
    
cortes_lazy = BendersLazyCuts(
    master, X, theta, lotes_validos, maquinas, maquinas_familia,
    capacidade, T, P, familia_lote, max(L, melhor_Z), logger, min(resultado_alns, melhor_Q), cache_Q
)
master.includeConshdlr(
    cortes_lazy, "BendersLazyCuts", "cortes de Benders gerados sob demanda (lazy constraints)",
    sepapriority=0, enfopriority=-10, chckpriority=-10,
    sepafreq=-1, propfreq=-1, eagerfreq=-1, maxprerounds=0,
    delaysepa=False, delayprop=False, needscons=False,
)
Z, valor_theta, valor_x = resolve_master(master, X, theta)
U_final = tuple(n for n, v in enumerate(valor_x) if v > 0.5)
Q = cortes_lazy.cache_Q[U_final]
numero_cortes = cortes_lazy.numero_cortes

fim = time.time()
tempo_total = fim - inicio
lotes_finais = [n for n, v in enumerate(valor_x) if v > 0.5]

#===================================================================================================
#Output Final =======================================================================================

logger.info("") 
logger.info("=" * 60) 
logger.info("RESULTADO FINAL") 
logger.info("=" * 60) 
logger.info(f"Solução ótima: " f"theta = {valor_theta:.2f}, " f"Q = {Q:.2f}") 
logger.info(f"Lotes selecionados: {lotes_finais}") 
logger.info(f"Número de lotes = {len(lotes_finais)}")
# logger.info(f"Número de iterações = {iteracao}")
logger.info(f"Número de cortes = {numero_cortes}")
logger.info(f"Tempo total = {tempo_total:.4f} segundos")
arquivo_csv = (pasta_resultados / "resultados.csv")
dados_resultado = {
    "instancia": arquivo,
    "produtos": len(produtos),
    "maquinas": len(maquinas),
    "familias": len(familia),
    "lotes_validos": len(lotes_validos),
    # "iteracoes": iteracao,
    "cortes": numero_cortes,
    "theta": round(valor_theta, 6),
    "Q": round(Q, 6),
    "tempo_segundos": round(tempo_total, 6),
    "numero_lotes": len(lotes_finais),
    "lotes_selecionados": str(lotes_finais),
    "Lower Bound": str(cortes_lazy.cache_LB),
    "Upper Bound": str(cortes_lazy.cache_UB),
    "Gap": str(cortes_lazy.cache_GAP)}

salva_resultados_csv(arquivo_csv, dados_resultado)
logger.info(f"Resultados salvos em: " f"{arquivo_csv.name}")
logger.info("")
logger.info("Execução finalizada.")

