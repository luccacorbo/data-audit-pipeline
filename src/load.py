"""Leitura dos arquivos originais do case."""

import csv
import json
from decimal import Decimal


def carregar_hub(caminho):
    """Lê o CSV do Hub (UTF-8, com ou sem BOM)."""
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def carregar_tribunal(caminho):
    """Lê o CSV do Tribunal (Windows-1252 e separador ';')."""
    with open(caminho, encoding="cp1252", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def carregar_json(caminho):
    """Lê JSON preservando números decimais."""
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo, parse_float=Decimal)
