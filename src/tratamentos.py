"""Normalização e validação dos dados do case."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation


def normalizar_valor(valor):
    """Converte valor monetário para Decimal com duas casas."""
    if valor is None or isinstance(valor, bool):
        raise ValueError("valor ausente ou inválido")

    if isinstance(valor, (int, float, Decimal)):
        numero = Decimal(str(valor))
    elif isinstance(valor, str):
        texto = valor.strip().replace("R$", "").replace(" ", "")
        if not texto:
            raise ValueError("valor vazio")
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", ".")
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", texto):
            raise ValueError(f"formato monetário inválido: {valor!r}")
        try:
            numero = Decimal(texto)
        except InvalidOperation:
            raise ValueError(f"valor inválido: {valor!r}") from None
    else:
        raise ValueError(f"tipo não suportado: {type(valor).__name__}")

    if not numero.is_finite() or numero <= 0:
        raise ValueError("valor deve ser finito e maior que zero")
    if numero != numero.quantize(Decimal("0.01")):
        raise ValueError("valor possui mais de duas casas decimais")
    return numero.quantize(Decimal("0.01"))


def normalizar_processo(processo):
    """Padroniza CNJ com máscara, preservando zeros à esquerda."""
    if processo is None:
        raise ValueError("processo ausente")

    texto = str(processo).strip()
    digitos = re.sub(r"\D", "", texto)
    mascarado = re.fullmatch(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", texto)
    sem_mascara = re.fullmatch(r"\d{20}", texto)
    if not (mascarado or sem_mascara):
        raise ValueError(f"formato de processo inválido: {processo!r}")

    return (
        f"{digitos[:7]}-{digitos[7:9]}.{digitos[9:13]}."
        f"{digitos[13]}.{digitos[14:16]}.{digitos[16:]}"
    )


def normalizar_data(valor):
    """Aceita somente datas no formato AAAA-MM-DD."""
    if not isinstance(valor, str):
        raise ValueError("data deve ser uma string AAAA-MM-DD")
    try:
        resultado = date.fromisoformat(valor)
    except ValueError:
        raise ValueError(f"data inválida: {valor!r}") from None
    if resultado.isoformat() != valor:
        raise ValueError(f"data fora do padrão AAAA-MM-DD: {valor!r}")
    return resultado


def normalizar_texto(valor):
    """Remove espaços excedentes sem alterar acentos ou conteúdo."""
    if valor is None:
        raise ValueError("texto ausente")
    texto = " ".join(str(valor).split())
    if not texto:
        raise ValueError("texto vazio")
    return texto


def tratar_registro_hub(registro):
    return {
        **registro,
        "processo": normalizar_processo(registro["processo"]),
        "ente": normalizar_texto(registro["ente"]),
        "valor_face": normalizar_valor(registro["valor_face"]),
        "prazo_pagamento": normalizar_data(registro["prazo_pagamento"]),
    }


def tratar_registro_tribunal(registro):
    return {
        **registro,
        "numero_processo": normalizar_processo(registro["numero_processo"]),
        "ente_devedor": normalizar_texto(registro["ente_devedor"]),
        "valor_face": normalizar_valor(registro["valor_face"]),
    }


def tratar_pagamento(registro):
    return {
        **registro,
        "processo": normalizar_processo(registro["processo"]),
        "evento_id": normalizar_texto(registro["evento_id"]),
        "valor": normalizar_valor(registro["valor"]),
        "data_pagamento": normalizar_data(registro["data_pagamento"]),
        "tipo": normalizar_texto(registro["tipo"]).lower(),
    }


def tratar_apresentacao(registro):
    return {
        **registro,
        "processo": normalizar_processo(registro["processo"]),
        "apresentado_em": normalizar_data(registro["apresentado_em"]),
    }
