"""Testes das transformações do módulo DI1 (sem rede)."""

import pandas as pd

from data import di1


def _bruto():
    # Duas linhas copiadas do PYield em 2026-11-11, taxas em fração.
    return pd.DataFrame({
        "data_referencia": ["2026-11-11", "2026-11-11"],
        "codigo_negociacao": ["DI1F27", "DI1Z26"],
        "data_vencimento": ["2027-01-04", "2026-12-01"],
        "dias_uteis": [35, 13],
        "taxa_ajuste": [0.1366, 0.13649],
        "taxa_fechamento": [0.1366, 0.1365],
        "contratos_abertos": [1000, 2000],
        "numero_negocios": [10, 20],
        "dv01": [1.0, 2.0],  # coluna extra que deve ser descartada
    })


def test_normalizar_converte_taxa_para_percentual_e_ordena():
    df = di1.normalizar(_bruto())
    assert list(df.columns) == di1.COLUNAS
    # Conferido à mão: 0.13649 em fração = 13.649 % a.a.
    assert df["codigo"].tolist() == ["DI1Z26", "DI1F27"]  # ordenado por vencimento
    assert df["taxa_ajuste"].round(5).tolist() == [13.649, 13.66]
    assert df["taxa_fechamento"].round(5).tolist() == [13.65, 13.66]
    assert df["dias_uteis"].tolist() == [13, 35]
    assert df["vencimento"].iloc[0] == pd.Timestamp("2026-12-01")
    assert df["data"].dtype.kind == "M"


def test_normalizar_vazio():
    df = di1.normalizar(pd.DataFrame())
    assert df.empty and list(df.columns) == di1.COLUNAS


def test_combinar_substitui_pregao_repetido():
    antigo = di1.normalizar(_bruto())
    bruto_novo = _bruto()
    bruto_novo["taxa_ajuste"] = [0.14, 0.14]
    novo = di1.normalizar(bruto_novo)
    df = di1.combinar(antigo, novo)
    assert len(df) == 2
    assert df["taxa_ajuste"].round(6).tolist() == [14.0, 14.0]


def test_ultima_curva():
    a = di1.normalizar(_bruto())
    b = a.copy()
    b["data"] = pd.Timestamp("2026-11-12")
    hist = pd.concat([a, b], ignore_index=True)
    ultima = di1.ultima_curva(hist)
    assert len(ultima) == 2 and (ultima["data"] == "2026-11-12").all()
