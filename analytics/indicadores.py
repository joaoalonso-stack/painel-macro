"""Variação dos indicadores contra um mês antes e contra o Focus.

Entrada: formato longo do SGS (``data``, ``serie``, ``valor``) e o Focus
anual (``data``, ``indicador``, ``referencia``, ``mediana``).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

# Séries cuja variação faz sentido em %; as demais variam em pontos percentuais.
TIPO_VARIACAO = {"ibc_br": "pct", "cambio": "pct"}


def ipca_acumulado(variacoes: Sequence[float]) -> float:
    """Acumula variações mensais em % de forma composta.

    Caso conferido à mão: [0.5, 0.5] acumula 1.0025%.
    """
    return float((np.prod(1 + np.asarray(variacoes, float) / 100) - 1) * 100)


def serie_de(sgs_long: pd.DataFrame, nome: str) -> pd.DataFrame:
    """Recorta uma série do formato longo, sem nulos, ordenada por data."""
    s = sgs_long[(sgs_long["serie"] == nome) & sgs_long["valor"].notna()]
    return s[["data", "valor"]].sort_values("data").reset_index(drop=True)


def observacao_em(serie: pd.DataFrame, data) -> tuple[pd.Timestamp, float] | None:
    """Última observação com ``data`` menor ou igual à data pedida."""
    ate = serie[serie["data"] <= pd.Timestamp(data)]
    if ate.empty:
        return None
    ult = ate.iloc[-1]
    return ult["data"], float(ult["valor"])


def variar(atual: float, anterior: float, tipo: str) -> float:
    """Variação em % (``tipo='pct'``) ou em p.p. (``tipo='pp'``)."""
    if tipo == "pct":
        return (atual / anterior - 1) * 100
    return atual - anterior


def variacao_um_mes(sgs_long: pd.DataFrame, nome: str) -> dict:
    """Última observação de ``nome`` e sua variação contra a observação de um mês antes.

    Para séries mensais, "um mês antes" é a observação anterior; para diárias,
    a última observação até a mesma data do mês anterior.
    """
    serie = serie_de(sgs_long, nome)
    tipo = TIPO_VARIACAO.get(nome, "pp")
    data, valor = observacao_em(serie, serie["data"].max())
    anterior = observacao_em(serie, data - pd.DateOffset(months=1))
    data_ant, valor_ant = anterior if anterior else (pd.NaT, np.nan)
    return {"serie": nome, "data": data, "valor": valor, "data_anterior": data_ant,
            "valor_anterior": valor_ant, "variacao": variar(valor, valor_ant, tipo), "tipo": tipo}


def tabela_variacoes(sgs_long: pd.DataFrame, nomes: Sequence[str] | None = None) -> pd.DataFrame:
    """Uma linha de ``variacao_um_mes`` por série."""
    nomes = list(nomes) if nomes else sorted(sgs_long["serie"].unique())
    return pd.DataFrame([variacao_um_mes(sgs_long, n) for n in nomes])


def ipca_no_ano(sgs_long: pd.DataFrame, ano: int) -> tuple[pd.Timestamp | None, float]:
    """IPCA acumulado em ``ano`` até o último mês divulgado: (último mês, acumulado %)."""
    serie = serie_de(sgs_long, "ipca")
    no_ano = serie[serie["data"].dt.year == ano]
    if no_ano.empty:
        return None, float("nan")
    return no_ano["data"].max(), ipca_acumulado(no_ano["valor"])


def focus_para(focus_anual: pd.DataFrame, indicador: str, ano: int) -> float:
    """Mediana da última pesquisa do Focus para ``indicador`` no ano ``ano``."""
    f = focus_anual[(focus_anual["indicador"] == indicador) & (focus_anual["referencia"] == ano)]
    if f.empty:
        return float("nan")
    return float(f.sort_values("data").iloc[-1]["mediana"])


def contra_focus(sgs_long: pd.DataFrame, focus_anual: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Realizado no ano contra a mediana do Focus para o mesmo ano.

    IPCA compara o acumulado até o último mês com a projeção do ano fechado;
    Selic e câmbio comparam o nível atual com a projeção de fim de ano.
    """
    mes, ipca_acum = ipca_no_ano(sgs_long, ano)
    _, selic = observacao_em(serie_de(sgs_long, "selic_meta"), pd.Timestamp.max)
    _, cambio = observacao_em(serie_de(sgs_long, "cambio"), pd.Timestamp.max)
    linhas = [
        {"indicador": "IPCA", "realizado": ipca_acum, "focus": focus_para(focus_anual, "IPCA", ano),
         "nota": f"acumulado até {mes:%Y-%m} x ano fechado" if mes is not None else "sem dado"},
        {"indicador": "Selic", "realizado": selic, "focus": focus_para(focus_anual, "Selic", ano),
         "nota": "meta vigente x fim de ano"},
        {"indicador": "Câmbio", "realizado": cambio, "focus": focus_para(focus_anual, "Câmbio", ano),
         "nota": "PTAX atual x fim de ano"},
    ]
    df = pd.DataFrame(linhas)
    df["diferenca"] = df["realizado"] - df["focus"]
    return df[["indicador", "realizado", "focus", "diferenca", "nota"]]
