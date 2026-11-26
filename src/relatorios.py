"""Geração dos relatórios CSV."""

import csv

COLUNAS_INCONSISTENCIAS = [
    "arquivo", "registro", "processo", "campo", "classificacao", "motivo",
]

COLUNAS_ATUALIZADOS = [
    "numero_processo", "ente_devedor", "valor_face",
    "total_pago", "total_estornado", "saldo_devedor", "presenca_bases",
]

# Soma pagamentos e estornos por precatório (LEFT JOIN mantém quem não tem pagamento)
SQL_ATUALIZADOS = """
    SELECT p.numero_processo,
           p.ente_devedor,
           p.valor_face,
           COALESCE(SUM(g.valor) FILTER (WHERE g.tipo = 'pagamento'), 0.00) AS total_pago,
           COALESCE(SUM(g.valor) FILTER (WHERE g.tipo = 'estorno'), 0.00)   AS total_estornado
    FROM precatorio p
    LEFT JOIN pagamento g ON g.precatorio_id = p.id
    GROUP BY p.id
    ORDER BY p.numero_processo
"""


def nova_inconsistencia(arquivo, registro, processo, campo, classificacao, motivo):
    """Monta uma linha de inconsistência."""
    return dict(zip(
        COLUNAS_INCONSISTENCIAS,
        [arquivo, registro, processo, campo, classificacao, motivo],
    ))


def gerar_inconsistencias(inconsistencias, caminho):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_INCONSISTENCIAS)
        escritor.writeheader()
        escritor.writerows(inconsistencias)


def gerar_atualizados(conn, caminho, presenca):
    """Consulta o banco e grava a base consolidada.

    presenca: {numero_processo: 'hub e tribunal' | 'somente hub' | 'somente tribunal'}
    """
    with conn.cursor() as cur:
        cur.execute(SQL_ATUALIZADOS)
        linhas = cur.fetchall()

    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(COLUNAS_ATUALIZADOS)
        for processo, ente, valor_face, pago, estornado in linhas:
            saldo = valor_face - (pago - estornado)
            escritor.writerow([processo, ente, valor_face, pago, estornado, saldo,
                               presenca.get(processo, "não informado")])