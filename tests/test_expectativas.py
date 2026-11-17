"""Testes das expectativas do Focus (sem rede)."""

import pandas as pd
import pytest

from analytics import expectativas as ex


def _focus():
    datas = pd.to_datetime(["2026-10-30", "2026-11-06", "2026-11-13"])
    linhas = []
    for d in datas:
        for ref, med in [(2026, 5.2), (2027, 4.8), (2028, 4.0)]:
            linhas.append((d, "IPCA", ref, med + (0.1 if d == datas[-1] else 0.0)))
        linhas.append((d, "Selic", 2026, 13.75))
    return pd.DataFrame(linhas, columns=["data", "indicador", "referencia", "mediana"])


def test_trajetoria_pivota_por_referencia():
    t = ex.trajetoria(_focus(), "IPCA", [2026, 2027, 2028])
    assert list(t.columns) == ["2026", "2027", "2028"] and len(t) == 3
    assert t.loc["2026-11-13", "2028"] == pytest.approx(4.1)


def test_trajetoria_indicador_ausente_vazia():
    assert ex.trajetoria(_focus(), "PIB Total", [2026]).empty


def test_desancoragem_conferida_a_mao():
    d = ex.desancoragem(_focus(), 2028)
    # mediana 4.1, meta 3.0 -> +1.1 p.p., dentro da banda (teto 4.5)
    assert d["mediana"] == pytest.approx(4.1) and d["distancia"] == pytest.approx(1.1)
    assert d["dentro_banda"] is True and d["data"] == pd.Timestamp("2026-11-13")
    assert ex.desancoragem(_focus(), 2026)["dentro_banda"] is False  # 5.3 > 4.5


def test_tabela_desancoragem():
    t = ex.tabela_desancoragem(_focus(), 2026)
    assert t["referencia"].tolist() == [2026, 2027, 2028]
    assert t["dentro_banda"].tolist() == [False, False, True]


def test_variacao_semanal():
    v = ex.variacao_semanal(_focus(), "IPCA", 2027)
    assert v["mediana"] == pytest.approx(4.9) and v["variacao_7d"] == pytest.approx(0.1)
    assert pd.isna(ex.variacao_semanal(_focus(), "Selic", 2030)["mediana"])
