"""Curva de DI1 (futuro de DI da B3) via PYield.

O PYield devolve polars com taxas em fração (0.1365). Aqui tudo vira pandas
com taxas em % a.a. (13.65), seguindo a convenção do projeto.

Colunas: data, codigo, vencimento, dias_uteis, taxa_ajuste, taxa_fechamento,
contratos_abertos, numero_negocios.
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from pyield import di1 as _di1

from data import cache

log = logging.getLogger(__name__)

NOME_CACHE = "di1"
INICIO_PADRAO = "2010-01-01"
_RENOMEAR = {
    "data_referencia": "data",
    "codigo_negociacao": "codigo",
    "data_vencimento": "vencimento",
}
COLUNAS_TAXA = ["taxa_ajuste", "taxa_fechamento"]
COLUNAS = ["data", "codigo", "vencimento", "dias_uteis",
           *COLUNAS_TAXA, "contratos_abertos", "numero_negocios"]


def vazio() -> pd.DataFrame:
    """DataFrame sem linhas, com as colunas padrão."""
    return pd.DataFrame(columns=COLUNAS)


def normalizar(bruto: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas, converte datas e passa as taxas de fração para % a.a.

    Caso conferido à mão: taxa_ajuste 0.13649 vira 13.649.
    """
    if bruto.empty:
        return vazio()
    df = bruto.rename(columns=_RENOMEAR)
    df["data"] = pd.to_datetime(df["data"])
    df["vencimento"] = pd.to_datetime(df["vencimento"])
    for col in COLUNAS_TAXA:
        df[col] = pd.to_numeric(df[col], errors="coerce") * 100
    df["dias_uteis"] = df["dias_uteis"].astype(int)
    return df[COLUNAS].sort_values(["data", "vencimento"]).reset_index(drop=True)


def datas_disponiveis(inicio: str, fim: str | None = None) -> list[date]:
    """Datas de pregão com curva disponível no PYield dentro de [inicio, fim]."""
    fim_d = date.fromisoformat(fim) if fim else date.today()
    ini_d = date.fromisoformat(inicio)
    todas = _di1.datas_disponiveis().to_list()
    return [d for d in todas if ini_d <= d <= fim_d]


def curva(data: str) -> pd.DataFrame:
    """Curva de um dia de pregão (ISO). Vazio se não houver pregão na data."""
    return normalizar(_di1.dados(data).to_pandas())


def historico(inicio: str, fim: str | None = None) -> pd.DataFrame:
    """Curvas de todos os pregões em [inicio, fim]."""
    datas = datas_disponiveis(inicio, fim)
    if not datas:
        return vazio()
    log.info("di1: baixando %d pregões (%s..%s)", len(datas), datas[0], datas[-1])
    return normalizar(_di1.dados(datas).to_pandas())


def combinar(antigo: pd.DataFrame, novo: pd.DataFrame) -> pd.DataFrame:
    """Une dois históricos, mantendo a linha mais nova por (data, codigo)."""
    df = pd.concat([antigo, novo], ignore_index=True)
    df = df.drop_duplicates(subset=["data", "codigo"], keep="last")
    return df.sort_values(["data", "vencimento"]).reset_index(drop=True)


def atualizar(inicio: str = INICIO_PADRAO) -> pd.DataFrame:
    """Atualiza o cache ``di1.parquet`` a partir do último pregão em cache."""
    antigo = cache.ler(NOME_CACHE) if cache.existe(NOME_CACHE) else vazio()
    desde = inicio if antigo.empty else antigo["data"].max().date().isoformat()
    atualizado = combinar(antigo, historico(desde))
    cache.gravar(NOME_CACHE, atualizado)
    return atualizado


def carregar() -> pd.DataFrame:
    """Lê o cache do DI1; atualiza se ainda não existir."""
    return cache.ler(NOME_CACHE) if cache.existe(NOME_CACHE) else atualizar()


def ultima_curva(df: pd.DataFrame) -> pd.DataFrame:
    """Recorta a curva do pregão mais recente do histórico."""
    return df[df["data"] == df["data"].max()].reset_index(drop=True)
