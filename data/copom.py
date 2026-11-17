"""Calendário de reuniões do Copom (via PYield), com rótulo compatível com o Focus.

O Focus identifica a reunião como ``R7/2028`` (7ª reunião de 2028). Aqui o
rótulo é reconstruído pela ordem da data de decisão dentro do ano.

Colunas: numero_bcb, data_inicio, data_decisao, data_publicacao (ata),
data_efetividade, status, ano, numero, reuniao.
"""

from __future__ import annotations

import pandas as pd
from pyield import copom as _copom

from data import cache

NOME_CACHE = "copom_calendario"
COLUNAS_FONTE = {
    "nro_reuniao": "numero_bcb",
    "data_inicio": "data_inicio",
    "data_decisao": "data_decisao",
    "data_publicacao": "data_publicacao",
    "data_efetividade": "data_efetividade",
    "status": "status",
}


def rotular(cal: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta ``ano``, ``numero`` (ordem no ano) e ``reuniao`` (``R{n}/{ano}``).

    Caso conferido à mão: a reunião decidida em 2026-12-09 é a 8ª de 2026,
    logo ``R8/2026``.
    """
    df = cal.sort_values("data_decisao").reset_index(drop=True).copy()
    df["ano"] = df["data_decisao"].dt.year
    df["numero"] = df.groupby("ano").cumcount() + 1
    df["reuniao"] = "R" + df["numero"].astype(str) + "/" + df["ano"].astype(str)
    return df


def baixar() -> pd.DataFrame:
    """Baixa o calendário completo do Copom e devolve em pandas, rotulado."""
    bruto = _copom.calendario().to_pandas()
    df = bruto[list(COLUNAS_FONTE)].rename(columns=COLUNAS_FONTE)
    for col in ("data_inicio", "data_decisao", "data_publicacao", "data_efetividade"):
        df[col] = pd.to_datetime(df[col])
    return rotular(df)


def carregar(ttl_horas: float = 24.0) -> pd.DataFrame:
    """Calendário do Copom do cache (renovado a cada ``ttl_horas``)."""
    return cache.obter(NOME_CACHE, baixar, ttl_horas=ttl_horas)


def proximas(cal: pd.DataFrame, data_ref: str, n: int = 9) -> pd.DataFrame:
    """As ``n`` próximas reuniões cuja nova taxa ainda não vigora em ``data_ref``.

    Uma reunião conta como "próxima" enquanto ``data_efetividade > data_ref``:
    a decisão sai após o fechamento e só vale no dia seguinte.
    """
    ref = pd.Timestamp(data_ref)
    futuras = cal[cal["data_efetividade"] > ref].sort_values("data_efetividade")
    return futuras.head(n).reset_index(drop=True)
