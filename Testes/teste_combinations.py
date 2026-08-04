from itertools import combinations

produtos = {
    "produto_1": 2.5,
    "produto_2": 7.0,
    "produto_3": 1.2,
    "produto_4": 10.0,
    "produto_5": 4.5,
    "produto_6": 0.8,
    "produto_7": 12.0,
    "produto_8": 3.0,
    "produto_9": 6.0,
    "produto_10": 5.5,
    "produto_11": 2.0,
    "produto_12": 9.0,
    "produto_13": 1.8,
    "produto_14": 8.0,
    "produto_15": 0.6
}
lotes_validos = []
A = []
capacidade = {
    "A": 30,
    "B": 25,
    "C": 20,
    "D": 50
}

maior_capacidade = max(capacidade.values())

for r in range(1, len(produtos) + 1):
    for lotes in combinations(produtos, r):

        if sum(produtos[p] for p in lotes) <= maior_capacidade:
            lotes_validos.append(lotes)

#Binariza :)
for lotes in lotes_validos:
    linha = [1 if n in lotes else 0 for n in produtos]
    A.append(linha)

print(A)