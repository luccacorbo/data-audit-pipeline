"""Testes das regras de comparação Hub x Tribunal."""

from decimal import Decimal

import pytest

from src.comparar_bases import comparar_bases

PROCESSO = "0012345-10.2019.8.26.0053"


def hub(ente="Município de São Paulo", valor="45000.00"):
    return {"processo": PROCESSO, "ente": ente, "valor_face": Decimal(valor)}


def tribunal(ente="Município de São Paulo", valor="45000.00"):
    return {"numero_processo": PROCESSO, "ente_devedor": ente, "valor_face": Decimal(valor)}


def test_ente_com_grafia_diferente_nao_e_divergencia():
    # Mesmo ente, só muda caixa e acento: deve persistir, sem inconsistência
    precatorios, presenca, inconsistencias = comparar_bases(
        [hub(ente="MUNICIPIO DE SAO PAULO")], [tribunal()], {PROCESSO})

    assert [p["ente_devedor"] for p in precatorios] == ["Município de São Paulo"]  # grafia do tribunal
    assert presenca == {PROCESSO: "hub e tribunal"}
    assert inconsistencias == []


@pytest.mark.parametrize("hub_registro, tribunal_registro, campo", [
    (hub(valor="31000.00"), tribunal(valor="30000.00"), "valor_face"),
    (hub(ente="Município de Santos"), tribunal(ente="União"), "ente"),
])
def test_divergencia_entre_as_bases_nao_persiste(hub_registro, tribunal_registro, campo):
    precatorios, presenca, inconsistencias = comparar_bases(
        [hub_registro], [tribunal_registro], {PROCESSO})

    assert precatorios == []
    assert presenca == {}
    assert [(i["campo"], i["classificacao"]) for i in inconsistencias] == [(campo, "duvidoso")]


@pytest.mark.parametrize("hub_lista, tribunal_lista, esperado", [
    ([hub()], [], "somente hub"),
    ([], [tribunal()], "somente tribunal"),
])
def test_processo_em_uma_base_persiste_se_existe_em_apresentacoes(
        hub_lista, tribunal_lista, esperado):
    precatorios, presenca, inconsistencias = comparar_bases(
        hub_lista, tribunal_lista, {PROCESSO})

    assert [p["numero_processo"] for p in precatorios] == [PROCESSO]
    assert presenca == {PROCESSO: esperado}
    assert len(inconsistencias) == 1  # a ausência continua sendo registrada


def test_processo_em_uma_base_fora_das_apresentacoes_nao_persiste():
    precatorios, presenca, inconsistencias = comparar_bases([hub()], [], set())

    assert precatorios == []
    assert presenca == {}
    assert len(inconsistencias) == 1
