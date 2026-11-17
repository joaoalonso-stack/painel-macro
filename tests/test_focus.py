"""Testes das transformações do módulo Focus (sem rede)."""

import pandas as pd
import pytest

from data import focus


def test_parse_reuniao():
    # Conferido à mão: "R7/2028" é a 7ª reunião de 2028.
    assert focus.parse_reuniao("R7/2028") == (2028, 7)
    assert focus.parse_reuniao("r1/2027") == (2027, 1)


def test_parse_reuniao_invalido():
    with pytest.raises(ValueError):
        focus.parse_reuniao("2028")


def test_normalizar_anual():
    bruto = pd.DataFrame({
        "Data": ["2026-11-05", "2026-11-05"], "Indicador": ["IPCA", "IPCA"],
        "DataReferencia": ["2026", "2027"], "Mediana": [5.2166, 4.8052],
        "Media": [5.21, 4.80], "DesvioPadrao": [0.1, 0.2], "numeroRespondentes": [100, 95],
    })
    df = focus.normalizar_anual(bruto)
    assert df["referencia"].tolist() == [2026, 2027]
    assert df["referencia"].dtype.kind == "i"
    assert df["data"].iloc[0] == pd.Timestamp("2026-11-05")
    assert df.loc[df["referencia"] == 2027, "mediana"].item() == 4.8052


def test_normalizar_selic_ordena_por_reuniao():
    bruto = pd.DataFrame({
        "Data": ["2026-11-06"] * 3, "Reuniao": ["R1/2028", "R8/2027", "R7/2027"],
        "Mediana": [11.5, 11.75, 12.0], "Media": [11.5, 11.75, 12.0],
        "DesvioPadrao": [0.1, 0.1, 0.1], "numeroRespondentes": [90, 90, 90],
    })
    df = focus.normalizar_selic(bruto)
    assert df["reuniao"].tolist() == ["R7/2027", "R8/2027", "R1/2028"]
    assert df["ano_reuniao"].tolist() == [2027, 2027, 2028]
    assert df["numero_reuniao"].tolist() == [7, 8, 1]


def test_combinar_mantem_linha_mais_nova():
    antigo = pd.DataFrame({"data": pd.to_datetime(["2026-11-05"]), "indicador": ["IPCA"],
                           "referencia": [2026], "mediana": [5.20]})
    novo = pd.DataFrame({"data": pd.to_datetime(["2026-11-05", "2026-11-06"]),
                         "indicador": ["IPCA", "IPCA"], "referencia": [2026, 2026],
                         "mediana": [5.22, 5.25]})
    df = focus.combinar(antigo, novo, ["indicador", "data", "referencia"])
    assert len(df) == 2
    assert df["mediana"].tolist() == [5.22, 5.25]


def test_ultima_pesquisa():
    df = pd.DataFrame({"data": pd.to_datetime(["2026-11-05", "2026-11-06", "2026-11-06"]),
                       "mediana": [1.0, 2.0, 3.0]})
    assert focus.ultima_pesquisa(df)["mediana"].tolist() == [2.0, 3.0]
