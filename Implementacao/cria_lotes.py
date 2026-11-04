from itertools import combinations

def cria_lotes(capacidade, peso, produtos_por_familia, tempo_proc, familia_produto, maquinas_familia):
    
    T = []
    P = []
    lotes_validos = []
    A = []
    maquinas = list(capacidade.keys())
    produtos = list(peso.keys())
    familia_lote = []

    for fam, produtos_fam in produtos_por_familia.items():
    
            maior_capacidade = max(capacidade[m] for m in maquinas_familia[fam])
    
            for r in range(1, len(produtos_fam) + 1):
                for lote in combinations(produtos_fam, r):
                    if sum(peso[p] for p in lote) <= maior_capacidade:
                        lotes_validos.append(lote)
                        familia_lote.append(fam)
                        
    #Binariza :)
    for lotes in lotes_validos:
        linha = [1 if n in lotes else 0 for n in produtos]
        A.append(linha)

    #tempos
    for lote in lotes_validos:
        tempo_lote = tempo_proc[familia_produto[lote[0]]]
        T.append(tempo_lote)

    #pesos
    for lote in lotes_validos:
        peso_lote = sum(peso[p] for p in lote)
        P.append(peso_lote)

    return (
        T,
        P,
        lotes_validos,
        A,
        maquinas,
        produtos,
        familia_lote
    )
