"""Testes da orquestração: tratar_lista e o encadeamento das camadas."""

import csv
import json
import sys

import main

P1 = "0012345-10.2019.8.26.0053"  # nas duas bases, iguais
P2 = "0023456-21.2020.8.26.0053"  # nas duas bases, valor diverge
P3 = "0056789-54.2017.4.03.6100"  # só no hub


# ---------- tratar_lista ----------

def tratar_falso(registro):
    """Tratamento mínimo só para testar o tratar_lista."""
    if registro["valor"] < 0:
        raise ValueError("valor negativo")
    return registro


def tratar_lista_falsa(registros, inconsistencias):
    return main.tratar_lista(registros, "arquivo", tratar_falso, "processo", inconsistencias)


def test_tratar_lista_separa_validos_de_descartados():
    registros = [
        {"evento_id": "ev-1", "processo": "P1", "valor": 10},
        {"evento_id": "ev-2", "processo": "P2", "valor": -1},
    ]
    inconsistencias = []

    tratados = tratar_lista_falsa(registros, inconsistencias)

    assert tratados == [registros[0]]
    assert len(inconsistencias) == 1
    assert inconsistencias[0]["registro"] == "ev-2"
    assert inconsistencias[0]["processo"] == "P2"
    assert inconsistencias[0]["classificacao"] == "descartado"
    assert inconsistencias[0]["motivo"] == "valor negativo"


def test_tratar_lista_descarta_registro_sem_coluna_obrigatoria():
    inconsistencias = []

    tratados = tratar_lista_falsa([{"processo": "P1"}], inconsistencias)

    assert tratados == []  # o pipeline não quebra
    assert inconsistencias[0]["registro"] == "linha 1"  # sem evento_id, usa a posição


# ---------- encadeamento das camadas (sem banco) ----------

def ler_csv(caminho):
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def evento(evento_id, processo, valor, tipo="pagamento"):
    return {"evento_id": evento_id, "processo": processo, "valor": valor, "tipo": tipo,
            "data_pagamento": "2025-03-10", "atualizado_em": "2025-03-10T10:00:00-03:00"}


def test_pipeline_encadeia_as_camadas(tmp_path, monkeypatch):
    (tmp_path / "hub.csv").write_text(
        "processo,ente,valor_face,prazo_pagamento\n"
        "00123451020198260053,MUNICIPIO DE SAO PAULO,45000.00,2025-12-31\n"  # sem máscara
        f"{P2},Município de São Paulo,31000.00,2025-12-31\n"
        f"{P3},Estado de São Paulo,22000.00,2025-12-31\n", encoding="utf-8")
    (tmp_path / "tribunal.csv").write_bytes(
        ("numero_processo;ente_devedor;valor_face\n"
         f"{P1};Município de São Paulo;45.000,00\n"
         f"{P2};Município de São Paulo;30.000,00\n").encode("cp1252"))
    (tmp_path / "pagamentos.json").write_text(json.dumps([
        evento("ev-1", P1, 15000.0),
        evento("ev-2", P1, 500, tipo="estorno"),
        evento("ev-3", P2, 8000),
        evento("ev-4", P1, None),     # valor ausente: não passa no tratamento
    ]), encoding="utf-8")
    (tmp_path / "apresentacoes.json").write_text(json.dumps(
        [{"processo": p, "apresentado_em": "2025-04-02"} for p in (P1, P2, P3)]),
        encoding="utf-8")

    # Persistência e relatório de atualizados trocados por funções que só anotam o que receberam
    recebido = {}

    class ConexaoFalsa:
        def close(self):
            pass

    def salvar_precatorios_falso(conn, precatorios):
        recebido["precatorios"] = precatorios
        return []

    def salvar_pagamentos_falso(conn, pagamentos):
        recebido["pagamentos"] = pagamentos
        return []

    def gerar_atualizados_falso(conn, caminho, presenca):
        recebido["presenca"] = presenca

    for nome, arquivo in [("HUB", "hub.csv"), ("TRIBUNAL", "tribunal.csv"),
                          ("PAGAMENTOS", "pagamentos.json"),
                          ("APRESENTACOES", "apresentacoes.json")]:
        monkeypatch.setattr(main, nome, str(tmp_path / arquivo))
    monkeypatch.setattr(main, "conectar", lambda dsn: ConexaoFalsa())
    monkeypatch.setattr(main, "salvar_precatorios", salvar_precatorios_falso)
    monkeypatch.setattr(main, "salvar_pagamentos", salvar_pagamentos_falso)
    monkeypatch.setattr(main, "gerar_atualizados", gerar_atualizados_falso)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setenv("DATABASE_URL", "ignorada")
    monkeypatch.chdir(tmp_path)  # os CSVs de inconsistências são gravados aqui

    main.main()

    # Só P1 (consistente, já com máscara) e P3 (só no hub, existe nas apresentações) são persistidos
    assert [p["numero_processo"] for p in recebido["precatorios"]] == [P1, P3]
    assert recebido["presenca"] == {P1: "hub e tribunal", P3: "somente hub"}
    # ev-4 foi descartado no tratamento e não chega à persistência
    assert {p["evento_id"] for p in recebido["pagamentos"]} == {"ev-1", "ev-2", "ev-3"}

    bases = ler_csv("inconsistencias_bases.csv")
    assert {(i["processo"], i["campo"]) for i in bases} == {(P2, "valor_face"), (P3, "processo")}
    assert {i["registro"] for i in ler_csv("inconsistencias_pagamentos.csv")} == {"ev-4"}