"""Testes da leitura dos arquivos."""

from decimal import Decimal

import pytest

from src import load


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_carregar_hub_aceita_utf8_com_e_sem_bom(tmp_path, encoding):
    arquivo = tmp_path / "hub.csv"
    arquivo.write_bytes("processo,ente\n0012345,Município\n".encode(encoding))

    # Com BOM mal tratado, a primeira chave viraria '\ufeffprocesso'
    assert load.carregar_hub(arquivo) == [{"processo": "0012345", "ente": "Município"}]


def test_carregar_tribunal_le_cp1252_e_ponto_e_virgula(tmp_path):
    arquivo = tmp_path / "tribunal.csv"
    arquivo.write_bytes("numero_processo;ente_devedor\n0012345;São Paulo\n".encode("cp1252"))

    assert load.carregar_tribunal(arquivo) == [
        {"numero_processo": "0012345", "ente_devedor": "São Paulo"}
    ]


def test_carregar_json_preserva_decimais(tmp_path):
    arquivo = tmp_path / "pagamentos.json"
    arquivo.write_text('[{"valor": 1500.10, "quantidade": 2}]', encoding="utf-8")

    registro = load.carregar_json(arquivo)[0]

    assert registro["valor"] == Decimal("1500.10")
    assert isinstance(registro["valor"], Decimal)  # nada de float
    assert registro["quantidade"] == 2