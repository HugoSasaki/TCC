def ler_instancia(nome_arquivo):
    with open(nome_arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    peso = {}
    familia_produto = {}
    capacidade = {}
    tempo_proc = {}
    maquinas_familia = {}

    secao = None
    produto_id = 1

    for linha in linhas:
        # identificar seção
        if "NOME DO PRODUTO" in linha:
            secao = "produtos"
            continue

        elif "MÁQUINAS/CAPACIDADE" in linha:
            secao = "maquinas"
            continue

        elif "FAMÍLIA/TEMPO" in linha:
            secao = "familias"
            continue

        elif "---" in linha:
            continue

        # -------------------
        # PRODUTOS
        # -------------------
        if secao == "produtos":
            nome, p, f = linha.split("/")

            peso[produto_id] = float(p)
            familia_produto[produto_id] = int(f)

            produto_id += 1

        # -------------------
        # MÁQUINAS
        # -------------------
        elif secao == "maquinas":
            maq, cap = linha.split("/")

            capacidade[maq] = int(cap)

        # -------------------
        # FAMÍLIAS
        # -------------------
        elif secao == "familias":
            fam, tempo, maq = linha.split("/")

            fam = int(fam)

            tempo_proc[fam] = int(tempo)
            maquinas_familia[fam] = maq.split(",")

    return (
        peso,
        familia_produto,
        capacidade,
        tempo_proc,
        maquinas_familia
    )

peso, familia_produto, capacidade, tempo_proc, maquinas_familia = ler_instancia(
    r"C:\Users\hugo2\OneDrive - aps3.com.br\TCC\Documentos\Instancias\Instância Teste 5 jobs.txt"
    )

from pyscipopt import Model

model = Model("Scheduling")

x = {}

for n in peso:
    for m in capacidade:
        x[n, m] = model.addVar(
            vtype="B",
            name=f"x_{n}_{m}"
        )

for n in peso:
    f = familia_produto[n]

    for m in capacidade:
        if m not in maquinas_familia[f]:
            model.addCons(x[n, m] == 0)