"""Testes do histórico do prêmio (sem rede; calendário de feriados do PYield é local)."""

import pandas as pd
import pytest

from analytics import premio


def _calendario():
    return pd.DataFrame({
        "reuniao": ["R8/2026", "R1/2027", "R2/2027", "R3/2027"],
        "data_decisao": pd.to_datetime(["2026-12-09", "2027-01-27", "2027-03-17", "2027-05-05"]),
        "data_efetividade": pd.to_datetime(["2026-12-10", "2027-01-28", "2027-03-18", "2027-05-06"]),
    })


def _curva_flat(data, taxa):
    return pd.DataFrame({"data": [pd.Timestamp(data)] * 3, "dias_uteis": [21, 252, 504],
                         "taxa_ajuste": [taxa] * 3})


def _focus():
    return pd.DataFrame({"data": pd.to_datetime(["2026-11-06"] * 3 + ["2026-11-13"] * 3),
                         "reuniao": ["R8/2026", "R1/2027", "R2/2027"] * 2,
                         "mediana": [13.75, 13.75, 13.5, 13.5, 13.5, 13.25]})


def test_pesquisa_ate_pega_a_ultima_disponivel():
    p = premio.pesquisa_ate(_focus(), "2026-11-12")
    assert (p["data"] == "2026-11-06").all() and len(p) == 3
    assert premio.pesquisa_ate(_focus(), "2026-11-01").empty


def test_premio_em_curva_flat():
    # Curva flat em 13.65: toda taxa a termo é 13.65, prêmio = 13.65 − Focus.
    df = premio.premio_em(_curva_flat("2026-11-12", 13.65), "2026-11-12", _calendario(), 13.75, _focus(), n=3)
    assert df["ordem"].tolist() == [1, 2, 3]
    assert df["reuniao"].tolist() == ["R8/2026", "R1/2027", "R2/2027"]
    assert df["implicita"].round(6).tolist() == [13.65] * 3
    assert df["premio"].round(6).tolist() == pytest.approx([-0.10, -0.10, 0.15])


def test_historico_e_pivot():
    hist = pd.concat([_curva_flat("2026-11-12", 13.65), _curva_flat("2026-11-13", 13.75)])
    sgs = pd.DataFrame({"data": pd.to_datetime(["2026-11-01"]), "serie": ["selic_meta"], "valor": [13.75]})
    h = premio.historico_premio(hist, _calendario(), sgs, _focus(), pregoes=10, n=2)
    assert len(h) == 4
    largo = premio.premio_largo(h)
    assert list(largo.columns) == ["1ª reunião", "2ª reunião"]
    # 13/11: Focus novo (13.5 e 13.5) e curva 13.75 -> prêmio +0.25 nas duas.
    assert largo.loc["2026-11-13"].round(6).tolist() == [0.25, 0.25]
