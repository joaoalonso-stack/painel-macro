"""Histórico do prêmio curva x Focus: a implícita por reunião recalculada pregão a pregão.

Como o conjunto de "próximas reuniões" muda com o tempo, o histórico é
indexado pela ordem (1ª, 2ª, 3ª... próxima reunião) além do rótulo.
"""

from __future__ import annotations

import pandas as pd

from analytics import curva, indicadores
from data import copom as copom_cal


def pesquisa_ate(focus_selic: pd.DataFrame, data) -> pd.DataFrame:
    """Linhas da última pesquisa do Focus com data menor ou igual a ``data``."""
    ate = focus_selic[focus_selic["data"] <= pd.Timestamp(data)]
    if ate.empty:
        return ate
    return ate[ate["data"] == ate["data"].max()]


def premio_em(curva_dia: pd.DataFrame, data_ref: str, calendario: pd.DataFrame,
              selic_atual: float, focus_selic: pd.DataFrame, n: int = 4) -> pd.DataFrame:
    """Implícita x Focus nas ``n`` próximas reuniões vistas de ``data_ref``.

    Colunas: data, ordem (1 = próxima), reuniao, implicita, focus, premio.
    """
    reunioes = copom_cal.proximas(calendario, data_ref, n=n + 1)
    if len(reunioes) < 2:
        return pd.DataFrame(columns=["data", "ordem", "reuniao", "implicita", "focus", "premio"])
    implic = curva.selic_implicita(curva_dia, reunioes, data_ref, selic_atual)
    df = curva.comparar_com_focus(implic, pesquisa_ate(focus_selic, data_ref))
    df = df[df["reuniao"] != "atual"].reset_index(drop=True)
    df["ordem"] = range(1, len(df) + 1)
    df["data"] = pd.Timestamp(data_ref)
    return df[["data", "ordem", "reuniao", "implicita", "focus", "premio"]]


def historico_premio(di1_hist: pd.DataFrame, calendario: pd.DataFrame, sgs_long: pd.DataFrame,
                     focus_selic: pd.DataFrame, pregoes: int = 120, n: int = 4) -> pd.DataFrame:
    """Prêmio por ordem de reunião nos últimos ``pregoes`` pregões (formato longo)."""
    selic = indicadores.serie_de(sgs_long, "selic_meta")
    datas = sorted(di1_hist["data"].unique())[-pregoes:]
    partes = []
    for d in datas:
        obs = indicadores.observacao_em(selic, d)
        if obs is None:
            continue
        data_ref = pd.Timestamp(d).date().isoformat()
        partes.append(premio_em(di1_hist[di1_hist["data"] == d], data_ref, calendario, obs[1], focus_selic, n))
    if not partes:
        return pd.DataFrame(columns=["data", "ordem", "reuniao", "implicita", "focus", "premio"])
    return pd.concat(partes, ignore_index=True)


def premio_largo(hist: pd.DataFrame) -> pd.DataFrame:
    """Pivot do histórico: índice data, uma coluna por ordem ("1ª reunião", ...)."""
    largo = hist.pivot(index="data", columns="ordem", values="premio").sort_index()
    largo.columns = [f"{o}ª reunião" for o in largo.columns]
    return largo
