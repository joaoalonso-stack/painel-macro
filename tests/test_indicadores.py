"""Testes das variações dos indicadores (sem rede)."""

import pandas as pd
import pytest

from analytics import indicadores


def _longo(linhas):
    df = pd.DataFrame(linhas, columns=["data", "serie", "valor"])
    df["data"] = pd.to_datetime(df["data"])
    return df


def test_ipca_acumulado():
    # Conferido à mão: 1.005 * 1.005 = 1.010025 -> 1.0025%
    assert indicadores.ipca_acumulado([0.5, 0.5]) == pytest.approx(1.0025)
    # 1.01 * 0.99 = 0.9999 -> -0.01%
    assert indicadores.ipca_acumulado([1.0, -1.0]) == pytest.approx(-0.01)
    assert indicadores.ipca_acumulado([]) == 0.0


def test_variar():
    assert indicadores.variar(102.0, 100.0, "pct") == pytest.approx(2.0)
    assert indicadores.variar(0.14, 0.82, "pp") == pytest.approx(-0.68)


def test_variacao_um_mes_serie_mensal_em_pp():
    s = _longo([("2026-09-01", "ipca", 0.82), ("2026-10-01", "ipca", 0.14)])
    v = indicadores.variacao_um_mes(s, "ipca")
    assert v["valor"] == 0.14 and v["valor_anterior"] == 0.82
    assert v["variacao"] == pytest.approx(-0.68) and v["tipo"] == "pp"
    assert v["data_anterior"] == pd.Timestamp("2026-09-01")


def test_variacao_um_mes_indice_em_pct():
    s = _longo([("2026-07-01", "ibc_br", 100.0), ("2026-08-01", "ibc_br", 102.0)])
    assert indicadores.variacao_um_mes(s, "ibc_br")["variacao"] == pytest.approx(2.0)


def test_variacao_um_mes_serie_diaria_usa_ultima_obs_ate_a_data():
    # Um mês antes de 2026-11-12 é 2026-10-12; a última cotação até lá é a de 10-10 (5.0).
    s = _longo([("2026-10-10", "cambio", 5.0), ("2026-10-13", "cambio", 5.1),
                ("2026-11-12", "cambio", 5.5)])
    v = indicadores.variacao_um_mes(s, "cambio")
    assert v["data_anterior"] == pd.Timestamp("2026-10-10")
    assert v["variacao"] == pytest.approx(10.0)


def test_variacao_sem_observacao_anterior_e_nan():
    s = _longo([("2026-10-01", "ipca", 0.14)])
    v = indicadores.variacao_um_mes(s, "ipca")
    assert pd.isna(v["variacao"]) and pd.isna(v["data_anterior"])


def test_tabela_variacoes_uma_linha_por_serie():
    s = _longo([("2026-09-01", "ipca", 0.82), ("2026-10-01", "ipca", 0.14),
                ("2026-07-01", "ibc_br", 100.0), ("2026-08-01", "ibc_br", 102.0)])
    t = indicadores.tabela_variacoes(s)
    assert t["serie"].tolist() == ["ibc_br", "ipca"]
    assert t["variacao"].round(2).tolist() == [2.0, -0.68]


def test_contra_focus():
    s = _longo([("2026-01-01", "ipca", 0.5), ("2026-02-01", "ipca", 0.5),
                ("2026-11-12", "selic_meta", 13.75), ("2026-11-12", "cambio", 5.6)])
    f = pd.DataFrame({"data": pd.to_datetime(["2026-11-05"] * 3 + ["2026-10-30"]),
                      "indicador": ["IPCA", "Selic", "Câmbio", "IPCA"],
                      "referencia": [2026, 2026, 2026, 2026],
                      "mediana": [5.2, 13.75, 5.35, 9.9]})
    df = indicadores.contra_focus(s, f, 2026).set_index("indicador")
    assert df.loc["IPCA", "realizado"] == pytest.approx(1.0025)
    assert df.loc["IPCA", "focus"] == 5.2  # última pesquisa, não a de 10-30
    assert df.loc["Selic", "diferenca"] == pytest.approx(0.0)
    assert df.loc["Câmbio", "diferenca"] == pytest.approx(0.25)
    assert "2026-02" in df.loc["IPCA", "nota"]
