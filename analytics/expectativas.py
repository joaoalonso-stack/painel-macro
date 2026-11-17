"""Trajetória das expectativas do Focus e medida de desancoragem.

Entrada: Focus anual em formato longo (``data``, ``indicador``, ``referencia``, ``mediana``).
"""

from __future__ import annotations

import pandas as pd

META_IPCA = 3.0
TOLERANCIA = 1.5


def trajetoria(focus_anual: pd.DataFrame, indicador: str, referencias: list[int],
               semanas: int = 52) -> pd.DataFrame:
    """Mediana por data (últimas ``semanas``) para cada ano de referência; colunas são os anos."""
    f = focus_anual[(focus_anual["indicador"] == indicador) & focus_anual["referencia"].isin(referencias)]
    if f.empty:
        return pd.DataFrame(columns=[str(r) for r in referencias])
    inicio = f["data"].max() - pd.Timedelta(weeks=semanas)
    f = f[f["data"] >= inicio]
    largo = f.pivot_table(index="data", columns="referencia", values="mediana").sort_index()
    largo.columns = [str(c) for c in largo.columns]
    return largo


def desancoragem(focus_anual: pd.DataFrame, referencia: int, meta: float = META_IPCA,
                 tolerancia: float = TOLERANCIA) -> dict:
    """Distância da mediana mais recente do IPCA para ``referencia`` em relação à meta.

    Caso conferido à mão: mediana 4.0 com meta 3.0 e tolerância 1.5 dá
    distância +1.0 p.p., dentro da banda (teto 4.5).
    """
    f = focus_anual[(focus_anual["indicador"] == "IPCA") & (focus_anual["referencia"] == referencia)]
    if f.empty:
        return {"referencia": referencia, "data": pd.NaT, "mediana": float("nan"),
                "distancia": float("nan"), "dentro_banda": None}
    ult = f.sort_values("data").iloc[-1]
    dist = float(ult["mediana"] - meta)
    return {"referencia": referencia, "data": ult["data"], "mediana": float(ult["mediana"]),
            "distancia": dist, "dentro_banda": abs(dist) <= tolerancia}


def tabela_desancoragem(focus_anual: pd.DataFrame, ano: int, horizontes: int = 3) -> pd.DataFrame:
    """Desancoragem para ``ano``, ``ano+1``, ... (``horizontes`` anos)."""
    return pd.DataFrame([desancoragem(focus_anual, ano + i) for i in range(horizontes)])


def variacao_semanal(focus_anual: pd.DataFrame, indicador: str, referencia: int) -> dict:
    """Mediana atual e variação contra a pesquisa de 7 dias antes (p.p.)."""
    f = focus_anual[(focus_anual["indicador"] == indicador) & (focus_anual["referencia"] == referencia)]
    f = f.sort_values("data")
    if f.empty:
        return {"indicador": indicador, "referencia": referencia, "mediana": float("nan"),
                "variacao_7d": float("nan")}
    ult = f.iloc[-1]
    antes = f[f["data"] <= ult["data"] - pd.Timedelta(days=7)]
    var = float(ult["mediana"] - antes.iloc[-1]["mediana"]) if not antes.empty else float("nan")
    return {"indicador": indicador, "referencia": referencia, "mediana": float(ult["mediana"]),
            "variacao_7d": var}
