"""Testes das transformações do módulo SGS (sem rede)."""

import pandas as pd

from data import sgs


def test_janelas_divide_em_blocos_de_9_anos():
    # Conferido à mão: 2010..2018 (9 anos) e 2019..2026-11-12.
    assert sgs.janelas("2010-01-01", "2026-11-12", anos=9) == [
        ("2010-01-01", "2018-12-31"),
        ("2019-01-01", "2026-11-12"),
    ]


def test_janelas_intervalo_curto_vira_uma_janela():
    assert sgs.janelas("2026-03-10", "2026-11-12") == [("2026-03-10", "2026-11-12")]


def test_janelas_inicio_depois_do_fim_e_vazio():
    assert sgs.janelas("2027-01-01", "2026-11-12") == []


def test_normalizar_converte_saida_do_bcb():
    bruto = pd.DataFrame({"ipca": [0.82, 0.14]},
                         index=pd.to_datetime(["2026-09-01", "2026-10-01"]))
    bruto.index.name = "Date"
    df = sgs.normalizar(bruto, "ipca")
    assert list(df.columns) == ["data", "serie", "valor"]
    assert df["serie"].tolist() == ["ipca", "ipca"]
    assert df["valor"].tolist() == [0.82, 0.14]
    assert df["data"].iloc[1] == pd.Timestamp("2026-10-01")


def test_normalizar_vazio():
    df = sgs.normalizar(pd.DataFrame(), "ipca")
    assert df.empty and list(df.columns) == ["data", "serie", "valor"]


def test_combinar_mantem_valor_mais_novo():
    antigo = pd.DataFrame({"data": pd.to_datetime(["2026-09-01", "2026-10-01"]),
                           "serie": ["ipca", "ipca"], "valor": [0.82, 0.10]})
    novo = pd.DataFrame({"data": pd.to_datetime(["2026-10-01", "2026-11-01"]),
                         "serie": ["ipca", "ipca"], "valor": [0.14, 0.30]})
    df = sgs.combinar(antigo, novo)
    assert len(df) == 3
    assert df.loc[df["data"] == "2026-10-01", "valor"].item() == 0.14  # revisão venceu


def test_em_formato_largo_e_ultimo_valor():
    longo = pd.DataFrame({
        "data": pd.to_datetime(["2026-09-01", "2026-10-01", "2026-09-01", "2026-10-01"]),
        "serie": ["ipca", "ipca", "desemprego", "desemprego"],
        "valor": [0.82, 0.14, 5.3, None],
    })
    largo = sgs.em_formato_largo(longo)
    assert largo.loc["2026-10-01", "ipca"] == 0.14
    assert pd.isna(largo.loc["2026-10-01", "desemprego"])
    data, valor = sgs.ultimo_valor(longo, "desemprego")
    assert (data, valor) == (pd.Timestamp("2026-09-01"), 5.3)
