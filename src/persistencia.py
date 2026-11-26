"""Gravação dos dados tratados no PostgreSQL.

As funções de salvar retornam os registros rejeitados como tuplas
(registro, campo, motivo), para que o main os registre nas inconsistências.
"""

import psycopg2

SQL_PRECATORIO = """
    INSERT INTO precatorio (numero_processo, ente_devedor, valor_face)
    VALUES (%s, %s, %s)
    ON CONFLICT (numero_processo) DO NOTHING
"""

SQL_PAGAMENTO = """
    INSERT INTO pagamento (precatorio_id, evento_id, tipo, valor, pago_em)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (evento_id) DO NOTHING
"""


def conectar(dsn):
    return psycopg2.connect(dsn)


def salvar_precatorios(conn, precatorios):
    """Insere precatórios novos; processo já cadastrado é rejeitado."""
    rejeitados = []
    with conn, conn.cursor() as cur:  # 'with conn' faz commit (ou rollback se der erro)
        for p in precatorios:
            cur.execute(
                SQL_PRECATORIO,
                (p["numero_processo"], p["ente_devedor"], p["valor_face"]),
            )
            if cur.rowcount == 0:  # ON CONFLICT ignorou a linha
                rejeitados.append((p, "numero_processo", "processo já cadastrado"))
    return rejeitados


def salvar_pagamentos(conn, pagamentos):
    """Insere pagamentos/estornos; rejeita processo inexistente e evento duplicado."""
    rejeitados = []
    with conn, conn.cursor() as cur:
        cur.execute("SELECT numero_processo, id FROM precatorio")
        ids = dict(cur.fetchall())  # {numero_processo: id}

        for p in pagamentos:
            precatorio_id = ids.get(p["processo"])
            if precatorio_id is None:
                rejeitados.append((p, "processo", "processo não persistido (ver inconsistencias_bases.csv)"))
                continue

            cur.execute(
                SQL_PAGAMENTO,
                (precatorio_id, p["evento_id"], p["tipo"], p["valor"], p["data_pagamento"]),
            )
            if cur.rowcount == 0:
                rejeitados.append((p, "evento_id", "evento duplicado"))
    return rejeitados