"""Pipeline: load -> tratamento -> comparar_bases -> persistência -> relatórios.

Uso:
    python main.py                 # gera todos os relatórios
    python main.py --atualizados   # só precatorios_atualizados.csv
    python main.py --inconsistencias   # inconsistencias_bases.csv e inconsistencias_pagamentos.csv
"""

import argparse
import os

from dotenv import load_dotenv

from src import load, tratamentos
from src.comparar_bases import comparar_bases
from src.persistencia import conectar, salvar_pagamentos, salvar_precatorios
from src.relatorios import gerar_atualizados, gerar_inconsistencias, nova_inconsistencia

load_dotenv()

HUB = "dados/hub.csv"
TRIBUNAL = "dados/tribunal.csv"
PAGAMENTOS = "dados/pagamentos.json"
APRESENTACOES = "dados/apresentacoes.json"


def tratar_lista(registros, arquivo, tratar, chave_processo, inconsistencias):
    """Aplica o tratamento linha a linha.

    Erro de validação -> descartado e registrado nas inconsistências.
    """
    tratados = []
    for numero, registro in enumerate(registros, start=1):
        try:
            tratados.append(tratar(registro))
        except (ValueError, KeyError) as erro:
            inconsistencias.append(nova_inconsistencia(
                arquivo, registro.get("evento_id") or f"linha {numero}",
                registro.get(chave_processo), "", "descartado", str(erro)))
    return tratados


def registrar_rejeitados(rejeitados, arquivo, chave_processo, inconsistencias):
    """Transforma os rejeitados da persistência em linhas de inconsistência."""
    for registro, campo, motivo in rejeitados:
        identificacao = registro.get("evento_id") or registro[chave_processo]
        inconsistencias.append(nova_inconsistencia(
            arquivo, identificacao, registro[chave_processo], campo,
            "descartado", motivo))


def main():
    parser = argparse.ArgumentParser(description="Processa precatórios e gera relatórios.")
    parser.add_argument("--inconsistencias", action="store_true",
                        help="gera os dois CSVs de inconsistências")
    parser.add_argument("--atualizados", action="store_true",
                        help="gera precatorios_atualizados.csv")
    args = parser.parse_args()
    if not (args.inconsistencias or args.atualizados):  # sem argumentos: tudo
        args.inconsistencias = args.atualizados = True

    inc_bases = []       # hub x tribunal
    inc_pagamentos = []  # pagamentos.json

    hub = tratar_lista(
        load.carregar_hub(HUB), "hub.csv",
        tratamentos.tratar_registro_hub, "processo", inc_bases)
    tribunal = tratar_lista(
        load.carregar_tribunal(TRIBUNAL), "tribunal.csv",
        tratamentos.tratar_registro_tribunal, "numero_processo", inc_bases)
    pagamentos = tratar_lista(
        load.carregar_json(PAGAMENTOS), "pagamentos.json",
        tratamentos.tratar_pagamento, "processo", inc_pagamentos)

    # Das apresentações só interessa o número do processo (prova de que ele existe)
    existentes = {tratamentos.normalizar_processo(a["processo"])
                  for a in load.carregar_json(APRESENTACOES)}

    precatorios, presenca, divergencias = comparar_bases(hub, tribunal, existentes)
    inc_bases.extend(divergencias)

    conn = conectar(os.environ["DATABASE_URL"])
    try:
        registrar_rejeitados(salvar_precatorios(conn, precatorios),
                             "banco de dados", "numero_processo", inc_bases)
        registrar_rejeitados(salvar_pagamentos(conn, pagamentos),
                             "pagamentos.json", "processo", inc_pagamentos)

        if args.atualizados:
            gerar_atualizados(conn, "precatorios_atualizados.csv", presenca)
    finally:
        conn.close()

    if args.inconsistencias:
        gerar_inconsistencias(inc_bases, "inconsistencias_bases.csv")
        gerar_inconsistencias(inc_pagamentos, "inconsistencias_pagamentos.csv")


if __name__ == "__main__":
    main()