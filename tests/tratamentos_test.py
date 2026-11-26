"""Testes da normalização de valor, processo e data."""

from datetime import date
from decimal import Decimal

import pytest

from src import tratamentos

PROCESSO = "0012345-10.2019.8.26.0053"


# ---------- valor ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("2.500,50", "2500.50"),        # formato brasileiro
    ("R$ 45.000,00", "45000.00"),   # com símbolo
    ("45000.00", "45000.00"),       # formato com ponto
    (15000.0, "15000.00"),          # float do JSON
    (8000, "8000.00"),              # inteiro
])
def test_normalizar_valor_aceita_formatos_validos(entrada, esperado):
    assert tratamentos.normalizar_valor(entrada) == Decimal(esperado)


@pytest.mark.parametrize("entrada", [
    None, True, "", "abc", 0, -200, "10,001",
])
def test_normalizar_valor_rejeita_invalidos(entrada):
    with pytest.raises(ValueError):
        tratamentos.normalizar_valor(entrada)


# ---------- processo ----------

def test_normalizar_processo_mantem_mascara():
    assert tratamentos.normalizar_processo(PROCESSO) == PROCESSO


def test_normalizar_processo_aplica_mascara_e_preserva_zeros():
    assert tratamentos.normalizar_processo("00123451020198260053") == PROCESSO


@pytest.mark.parametrize("entrada", [None, "", "123", "0012345-10.2019.8.26.005"])
def test_normalizar_processo_rejeita_invalidos(entrada):
    with pytest.raises(ValueError):
        tratamentos.normalizar_processo(entrada)


# ---------- data ----------

def test_normalizar_data_aceita_iso():
    assert tratamentos.normalizar_data("2025-03-10") == date(2025, 3, 10)


@pytest.mark.parametrize("entrada", [
    "10/04/2025",                  # formato brasileiro (ambíguo, não aceito)
    "2025-02-30",                  # data que não existe
    "20250310",                    # ISO sem hífens
    "2025-04-02T23:30:00-03:00",   # data com hora
    None,
])
def test_normalizar_data_rejeita_fora_do_padrao(entrada):
    with pytest.raises(ValueError):
        tratamentos.normalizar_data(entrada)
