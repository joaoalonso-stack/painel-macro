"""Expectativas de mercado (boletim Focus) via API Olinda do BCB.

Dois conjuntos:

* ``focus_anual``: mediana (e dispersão) para IPCA, Selic, PIB e câmbio por
  ano de referência. Colunas: data, indicador, referencia, mediana, media,
  desvio, respondentes.
* ``focus_selic``: mediana da Selic esperada por reunião do Copom
  (rótulo ``R7/2028``). Colunas: data, reuniao, ano_reuniao, numero_reuniao,
  mediana, media, desvio, respondentes.

Só a base de cálculo 0 (todos os respondentes dos últimos 30 dias) é usada.
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from bcb import Expectativas

from data import cache
from data.sgs import janelas

log = logging.getLogger(__name__)

INICIO_PADRAO = "2010-01-01"
INDICADORES_ANUAIS = ["IPCA", "Selic", "PIB Total", "Câmbio"]
ENDPOINT_ANUAL = "ExpectativasMercadoAnuais"
ENDPOINT_SELIC = "ExpectativasMercadoSelic"
CACHE_ANUAL = "focus_anual"
CACHE_SELIC = "focus_selic"

_RENOMEAR = {
    "Data": "data",
    "Indicador": "indicador",
    "DataReferencia": "referencia",
    "Reuniao": "reuniao",
    "Mediana": "mediana",
    "Media": "media",
    "DesvioPadrao": "desvio",
    "numeroRespondentes": "respondentes",
}


def parse_reuniao(rotulo: str) -> tuple[int, int]:
    """Converte ``"R7/2028"`` em ``(2028, 7)``: (ano, número da reunião)."""
    numero, ano = rotulo.strip().upper().lstrip("R").split("/")
    return int(ano), int(numero)


def normalizar_anual(bruto: pd.DataFrame) -> pd.DataFrame:
    """Padroniza a saída do endpoint anual: nomes, tipos e ordem."""
    cols = ["data", "indicador", "referencia", "mediana", "media", "desvio", "respondentes"]
    if bruto.empty:
        return pd.DataFrame(columns=cols)
    df = bruto.rename(columns=_RENOMEAR)
    df["data"] = pd.to_datetime(df["data"])
    df["referencia"] = df["referencia"].astype(int)
    return df[cols].sort_values(["indicador", "data", "referencia"]).reset_index(drop=True)


def normalizar_selic(bruto: pd.DataFrame) -> pd.DataFrame:
    """Padroniza a saída do endpoint de Selic por reunião."""
    cols = ["data", "reuniao", "ano_reuniao", "numero_reuniao",
            "mediana", "media", "desvio", "respondentes"]
    if bruto.empty:
        return pd.DataFrame(columns=cols)
    df = bruto.rename(columns=_RENOMEAR)
    df["data"] = pd.to_datetime(df["data"])
    partes = df["reuniao"].map(parse_reuniao)
    df["ano_reuniao"] = [p[0] for p in partes]
    df["numero_reuniao"] = [p[1] for p in partes]
    return df[cols].sort_values(["data", "ano_reuniao", "numero_reuniao"]).reset_index(drop=True)


def _endpoint(nome: str):
    """Abre o endpoint OData ``nome`` do serviço Expectativas."""
    return Expectativas().get_endpoint(nome)


def baixar_anual(inicio: str = INICIO_PADRAO, fim: str | None = None,
                 indicadores: list[str] | None = None) -> pd.DataFrame:
    """Baixa as expectativas anuais (base de cálculo 0), um ano-calendário por vez."""
    fim = fim or date.today().isoformat()
    ep = _endpoint(ENDPOINT_ANUAL)
    partes = []
    for ind in indicadores or INDICADORES_ANUAIS:
        for ini, fim_janela in janelas(inicio, fim, anos=1):
            q = (ep.query()
                 .filter(ep.Indicador == ind, ep.baseCalculo == 0,
                         ep.Data >= ini, ep.Data <= fim_janela)
                 .select(ep.Data, ep.Indicador, ep.DataReferencia, ep.Mediana,
                         ep.Media, ep.DesvioPadrao, ep.numeroRespondentes))
            partes.append(q.collect())
            log.info("focus anual %s %s..%s: %d linhas", ind, ini, fim_janela, len(partes[-1]))
    return normalizar_anual(pd.concat(partes, ignore_index=True))


def baixar_selic(inicio: str = INICIO_PADRAO, fim: str | None = None) -> pd.DataFrame:
    """Baixa a Selic esperada por reunião (base de cálculo 0), um ano por vez."""
    fim = fim or date.today().isoformat()
    ep = _endpoint(ENDPOINT_SELIC)
    partes = []
    for ini, fim_janela in janelas(inicio, fim, anos=1):
        q = (ep.query()
             .filter(ep.baseCalculo == 0, ep.Data >= ini, ep.Data <= fim_janela)
             .select(ep.Data, ep.Reuniao, ep.Mediana, ep.Media,
                     ep.DesvioPadrao, ep.numeroRespondentes))
        partes.append(q.collect())
        log.info("focus selic %s..%s: %d linhas", ini, fim_janela, len(partes[-1]))
    return normalizar_selic(pd.concat(partes, ignore_index=True))


def combinar(antigo: pd.DataFrame, novo: pd.DataFrame, chave: list[str]) -> pd.DataFrame:
    """Une dois conjuntos, mantendo a linha mais nova para cada ``chave``."""
    df = pd.concat([antigo, novo], ignore_index=True)
    return df.drop_duplicates(subset=chave, keep="last").sort_values(chave).reset_index(drop=True)


def _desde(antigo: pd.DataFrame, inicio: str) -> str:
    """Data inicial do download incremental: última data em cache ou ``inicio``."""
    if antigo.empty:
        return inicio
    return antigo["data"].max().date().isoformat()


def atualizar(inicio: str = INICIO_PADRAO) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Atualiza os caches ``focus_anual`` e ``focus_selic`` de forma incremental."""
    antigo_anual = cache.ler(CACHE_ANUAL) if cache.existe(CACHE_ANUAL) else normalizar_anual(pd.DataFrame())
    anual = combinar(antigo_anual, baixar_anual(_desde(antigo_anual, inicio)),
                     ["indicador", "data", "referencia"])
    cache.gravar(CACHE_ANUAL, anual)

    antigo_selic = cache.ler(CACHE_SELIC) if cache.existe(CACHE_SELIC) else normalizar_selic(pd.DataFrame())
    selic = combinar(antigo_selic, baixar_selic(_desde(antigo_selic, inicio)),
                     ["data", "ano_reuniao", "numero_reuniao"])
    cache.gravar(CACHE_SELIC, selic)
    return anual, selic


def carregar_anual() -> pd.DataFrame:
    """Lê o cache anual; atualiza se ainda não existir."""
    return cache.ler(CACHE_ANUAL) if cache.existe(CACHE_ANUAL) else atualizar()[0]


def carregar_selic() -> pd.DataFrame:
    """Lê o cache da Selic por reunião; atualiza se ainda não existir."""
    return cache.ler(CACHE_SELIC) if cache.existe(CACHE_SELIC) else atualizar()[1]


def ultima_pesquisa(df: pd.DataFrame) -> pd.DataFrame:
    """Recorta as linhas da data mais recente disponível."""
    return df[df["data"] == df["data"].max()].reset_index(drop=True)
