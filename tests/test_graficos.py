"""Testes de fumaça das figuras do painel (sem Streamlit, sem rede)."""

import pandas as pd

from app import graficos


def test_implicita_vs_focus_tem_duas_series_e_ignora_linha_atual():
    df = pd.DataFrame({"reuniao": ["atual", "R8/2026", "R1/2027"],
                       "implicita": [13.65, 13.68, 13.82], "focus": [None, 13.75, 13.75]})
    fig = graficos.implicita_vs_focus(df)
    assert [t.name for t in fig.data] == ["Selic implícita (DI1)", "Focus (mediana)"]
    assert list(fig.data[0].x) == ["R8/2026", "R1/2027"]
    assert fig.data[0].line.color == "#2a78d6" and fig.data[1].line.color == "#eb6834"


def test_curva_di1_serie_unica_sem_legenda():
    c = pd.DataFrame({"vencimento": pd.to_datetime(["2027-01-04", "2026-12-01"]),
                      "taxa_ajuste": [13.66, 13.649], "codigo": ["DI1F27", "DI1Z26"]})
    fig = graficos.curva_di1(c)
    assert len(fig.data) == 1 and fig.data[0].showlegend is False
    assert list(fig.data[0].customdata) == ["DI1Z26", "DI1F27"]  # ordenado por vencimento


def test_tom_copom_duas_series_em_modo_escuro():
    df = pd.DataFrame({"nro_reuniao": [281, 281, 282, 282], "tipo": ["comunicado", "ata"] * 2,
                       "indice": [0.37, 0.17, 0.44, 0.27]})
    fig = graficos.tom_copom(df, modo="dark")
    assert [t.name for t in fig.data] == ["comunicado", "ata"]
    assert fig.data[0].marker.color == "#3987e5"
    assert fig.layout.barmode == "group"


def test_reacao_di1_cor_por_polaridade():
    df = pd.DataFrame({"nro_reuniao": [280, 281, 282], "tipo": ["comunicado"] * 3,
                       "delta_1a_bp": [4.7, -6.3, None]})
    fig = graficos.reacao_di1(df)
    assert list(fig.data[0].marker.color) == ["#e34948", "#2a78d6"]  # alta vermelha, queda azul
    assert list(fig.data[0].x) == ["280", "281"]  # linha sem dado é descartada
