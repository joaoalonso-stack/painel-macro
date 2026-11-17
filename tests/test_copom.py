"""Testes do calendário do Copom (sem rede)."""

import pandas as pd

from data import copom


def _cal():
    return pd.DataFrame({
        "data_decisao": pd.to_datetime(["2026-12-09", "2026-11-04", "2027-01-27", "2026-09-16"]),
        "data_efetividade": pd.to_datetime(["2026-12-10", "2026-11-05", "2027-01-28", "2026-09-17"]),
    })


def test_rotular_numera_por_ordem_no_ano():
    df = copom.rotular(_cal())
    # Conferido à mão: setembro, novembro e dezembro de 2026 são, nesta amostra,
    # a 1ª, 2ª e 3ª reuniões do ano; janeiro reinicia a contagem em 2027.
    assert df["reuniao"].tolist() == ["R1/2026", "R2/2026", "R3/2026", "R1/2027"]
    assert df["numero"].tolist() == [1, 2, 3, 1]


def test_proximas_usa_data_de_efetividade():
    cal = copom.rotular(_cal())
    # Em 2026-11-04 (dia da decisão) a nova taxa ainda não vigora: a reunião conta.
    assert copom.proximas(cal, "2026-11-04")["reuniao"].tolist() == ["R2/2026", "R3/2026", "R1/2027"]
    # Em 2026-11-05 ela já vigora: sai da lista.
    assert copom.proximas(cal, "2026-11-05", n=1)["reuniao"].tolist() == ["R3/2026"]
