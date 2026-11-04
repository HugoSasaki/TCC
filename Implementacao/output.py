import logging
import csv

def configura_logger(pasta_instancia):

    arquivo_log = pasta_instancia / "_resultado.log"
    logger = logging.getLogger(f"Benders_{pasta_instancia.name}")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(arquivo_log, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def salva_resultados_csv(arquivo_csv, dados):

    arquivo_existe = arquivo_csv.exists()

    with open(arquivo_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dados.keys())
        if not arquivo_existe:
            writer.writeheader()

        writer.writerow(dados)
