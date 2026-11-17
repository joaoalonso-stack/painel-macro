"""Testes dos cálculos de curva (sem rede).

Caso base conferido à mão: vértices (21 du, 12% a.a.) e (63 du, 14% a.a.).
  F(21) = 1.12^(21/252) = 1.12^(1/12);  F(63) = 1.14^(63/252) = 1.14^(1/4)
  Termo 21→63: (F63/F21)^(252/42) − 1 = 1.14^1.5 / 1.12^0.5 − 1
             = 1.2171869 / 1.0583005 − 1 = 15.0133%
  Interpolada em 42 du (meio do caminho, flat forward):
             F(42)^6 − 1 = 1.12^0.5 · (1.150133)^0.5 − 1 = 13.4966%
"""

import numpy as np
import pandas as pd
import pytest

from analytics import curva


@pytest.fixture
def curva_2v():
    return pd.DataFrame({"dias_uteis": [63, 21], "taxa_ajuste": [14.0, 12.0]})


def test_fator_e_taxa_sao_inversos():
    assert curva.taxa(curva.fator(12.0, 126), 126) == pytest.approx(12.0)
    assert curva.fator(12.0, 252) == pytest.approx(1.12)


def test_interpolar_nos_vertices_e_no_meio(curva_2v):
    r = curva.interpolar(curva_2v, [21, 42, 63])
    assert r[0] == pytest.approx(12.0)
    assert r[1] == pytest.approx(13.4966, abs=1e-3)
    assert r[2] == pytest.approx(14.0)


def test_interpolar_fora_dos_vertices_e_flat(curva_2v):
    r = curva.interpolar(curva_2v, [0, 5, 100])
    assert list(r) == [12.0, 12.0, 14.0]


def test_taxa_a_termo(curva_2v):
    assert curva.taxa_a_termo(curva_2v, 21, 63) == pytest.approx(15.0133, abs=1e-3)
    assert curva.taxa_a_termo(curva_2v, 0, 21) == pytest.approx(12.0)
    # Depois do último vértice a curva é flat em 14%, logo o termo 63→84 é 14%.
    assert curva.taxa_a_termo(curva_2v, 63, 84) == pytest.approx(14.0)


def test_selic_implicita_por_reuniao(curva_2v):
    reunioes = pd.DataFrame({
        "reuniao": ["R1/2027", "R2/2027", "R3/2027"],
        "data_decisao": pd.to_datetime(["2027-01-27", "2027-03-17", "2027-05-05"]),
        "data_efetividade": pd.to_datetime(["2027-01-28", "2027-03-18", "2027-05-06"]),
    })
    df = curva.selic_implicita(curva_2v, reunioes, "2026-12-28", selic_atual=12.25,
                               dias_uteis=[21, 63, 84])
    assert df["reuniao"].tolist() == ["atual", "R1/2027", "R2/2027"]
    assert df["du_inicio"].tolist() == [0, 21, 63]
    assert df["du_fim"].tolist() == [21, 63, 84]
    assert df["implicita"].round(3).tolist() == [12.0, 15.013, 14.0]
    assert df["variacao"].round(3).tolist() == [-0.25, 3.013, -1.013]
    assert df["inicio"].iloc[0] == pd.Timestamp("2026-12-28")
    assert df["fim"].iloc[1] == pd.Timestamp("2027-03-18")


def test_comparar_com_focus():
    implic = pd.DataFrame({"reuniao": ["atual", "R1/2027"], "implicita": [12.0, 15.0]})
    f = pd.DataFrame({"reuniao": ["R1/2027", "R2/2027"], "mediana": [14.5, 14.0]})
    df = curva.comparar_com_focus(implic, f)
    assert np.isnan(df.loc[0, "focus"])
    assert df.loc[1, "focus"] == 14.5
    assert df.loc[1, "premio"] == pytest.approx(0.5)
