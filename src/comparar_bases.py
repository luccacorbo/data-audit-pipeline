"""Comparação entre Hub e Tribunal (roda depois do tratamento).

Regras:
- nas duas bases e iguais em ente e valor_face -> persiste
- nas duas bases mas divergentes -> não persiste
- em só uma das bases -> persiste se o processo existe em apresentacoes.json
Toda diferença entre as bases é registrada nas inconsistências.
"""

import unicodedata

from src.relatorios import nova_inconsistencia


def chave_ente(ente):
    """Ignora acento e maiúscula: 'MUNICIPIO DE SAO PAULO' == 'Município de São Paulo'."""
    sem_acento = unicodedata.normalize("NFKD", ente).encode("ascii", "ignore").decode()
    return sem_acento.casefold()


def divergencia(arquivo, processo, campo, motivo):
    return nova_inconsistencia(arquivo, processo, processo, campo, "duvidoso", motivo)


def montar_precatorio(processo, ente, valor_face):
    """Formato único que a persistência espera, venha do Hub ou do Tribunal."""
    return {"numero_processo": processo, "ente_devedor": ente, "valor_face": valor_face}


def comparar_processo(processo, hub, tribunal, existentes):
    """Retorna (precatorio, presenca, inconsistencias).

    precatorio é None quando o processo não deve ser persistido.
    """
    if hub and tribunal:
        problemas = []
        if hub["valor_face"] != tribunal["valor_face"]:
            problemas.append(divergencia(
                "hub.csv x tribunal.csv", processo, "valor_face",
                f"valor_face diverge (hub={hub['valor_face']}, "
                f"tribunal={tribunal['valor_face']}); não persistido"))
        if chave_ente(hub["ente"]) != chave_ente(tribunal["ente_devedor"]):
            problemas.append(divergencia(
                "hub.csv x tribunal.csv", processo, "ente",
                f"ente diverge (hub={hub['ente']}, "
                f"tribunal={tribunal['ente_devedor']}); não persistido"))
        if problemas:
            return None, None, problemas
        precatorio = montar_precatorio(processo, tribunal["ente_devedor"], tribunal["valor_face"])
        return precatorio, "hub e tribunal", []

    # Processo em apenas uma das bases
    if hub:
        arquivo, ausente, presenca = "hub.csv", "tribunal", "somente hub"
        precatorio = montar_precatorio(processo, hub["ente"], hub["valor_face"])
    else:
        arquivo, ausente, presenca = "tribunal.csv", "hub", "somente tribunal"
        precatorio = montar_precatorio(processo, tribunal["ente_devedor"], tribunal["valor_face"])

    if processo not in existentes:
        motivo = f"ausente no {ausente} e em apresentacoes.json; não persistido"
        return None, None, [divergencia(arquivo, processo, "processo", motivo)]

    motivo = f"ausente no {ausente}; persistido (existe em apresentacoes.json)"
    return precatorio, presenca, [divergencia(arquivo, processo, "processo", motivo)]


def comparar_bases(hub, tribunal, existentes):
    """Recebe registros já tratados e o conjunto de processos de apresentacoes.json.

    Retorna (precatorios, presenca, inconsistencias):
    - precatorios: dicts prontos para a persistência
    - presenca: {processo: 'hub e tribunal' | 'somente hub' | 'somente tribunal'}
    - inconsistencias: linhas para o inconsistencias_bases.csv
    """
    hub_por_processo = {r["processo"]: r for r in hub}
    tribunal_por_processo = {r["numero_processo"]: r for r in tribunal}

    precatorios = []
    presenca = {}
    inconsistencias = []
    for processo in sorted(hub_por_processo.keys() | tribunal_por_processo.keys()):
        precatorio, origem, problemas = comparar_processo(
            processo, hub_por_processo.get(processo),
            tribunal_por_processo.get(processo), existentes)
        inconsistencias.extend(problemas)
        if precatorio:
            precatorios.append(precatorio)
            presenca[processo] = origem
    return precatorios, presenca, inconsistencias