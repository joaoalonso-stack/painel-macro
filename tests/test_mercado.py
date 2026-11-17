"""Testes do movimento de mercado (sem rede)."""

import pandas as pd
import pytest

from analytics import mercado


def _taxas():
    d = pd.Timestamp("2026-11-12")
    return pd.DataFrame({
        "data": [d - pd.Timedelta(days=31), d - pd.Timedelta(days=8), d - pd.Timedelta(days=1), d],
        "1a": [13.0, 13.2, 13.4, 13.5], "2a": [13.5, 13.5, 13.5, 13.5], "5a": [14.0, 14.1, 14.2, 14.3],
    })


def test_variacoes_vertices_conferido_a_mao():
    v = mercado.variacoes_vertices(_taxas()).set_index("vertice")
    assert v.loc["1a", "taxa"] == 13.5
    assert v.loc["1a", ["d1_bp", "d7_bp", "d30_bp"]].round(6).tolist() == [10.0, 30.0, 50.0]
    assert v.loc["2a", ["d1_bp", "d7_bp", "d30_bp"]].round(6).tolist() == [0.0, 0.0, 0.0]
    assert v.attrs["datas"]["d7_bp"] == pd.Timestamp("2026-11-04")


def test_variacoes_com_um_so_pregao_da_nan():
    v = mercado.variacoes_vertices(_taxas().tail(1)).set_index("vertice")
    assert pd.isna(v.loc["1a", "d1_bp"]) and pd.isna(v.loc["1a", "d30_bp"])


def test_inclinacoes_em_bp():
    i = mercado.inclinacoes(_taxas())
    assert i["2a−1a"].round(6).tolist() == [50.0, 30.0, 10.0, 0.0]
    assert i["5a−2a"].round(6).tolist() == [50.0, 60.0, 70.0, 80.0]


def test_taxas_vertices_curva_flat():
    hist = pd.DataFrame({"data": [pd.Timestamp("2026-11-11")] * 3, "dias_uteis": [126, 504, 1500],
                         "taxa_ajuste": [13.0, 13.0, 13.0]})
    t = mercado.taxas_vertices(hist)
    assert t[["1a", "2a", "5a"]].iloc[0].tolist() == pytest.approx([13.0, 13.0, 13.0])


def test_curva_em_pega_ultimo_pregao_ate_a_data():
    hist = pd.DataFrame({"data": pd.to_datetime(["2026-10-09", "2026-10-13"]), "dias_uteis": [252, 252],
                         "taxa_ajuste": [13.0, 13.1]})
    assert mercado.curva_em(hist, "2026-10-12")["taxa_ajuste"].item() == 13.0


def test_movimento_proxima_reuniao():
    implic = pd.DataFrame({"reuniao": ["atual", "R8/2026", "R1/2027"],
                           "data_decisao": [pd.NaT, pd.Timestamp("2026-12-09"), pd.Timestamp("2027-01-27")],
                           "implicita": [13.655, 13.684, 13.818]})
    m = mercado.movimento_proxima_reuniao(implic)
    assert m["reuniao"] == "R8/2026" and m["sentido"] == "alta"
    assert m["variacao_pp"] == pytest.approx(0.029)
    assert m["probabilidade"] == pytest.approx(0.116)
    implic.loc[1, "implicita"] = 13.0  # -0.655 p.p. -> mais de um corte de 25 bp: satura em 100%
    m = mercado.movimento_proxima_reuniao(implic)
    assert m["sentido"] == "corte" and m["probabilidade"] == 1.0
