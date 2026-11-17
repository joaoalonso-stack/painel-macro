"""Séries do SGS (Sistema Gerenciador de Séries Temporais) do BCB.

Formato longo padrão: colunas ``data`` (datetime), ``serie`` (str) e
``valor`` (float). Datas em ISO; taxas em % a.a. onde a fonte assim publica.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date

import pandas as pd
from bcb import sgs as _sgs

from data import cache

log = logging.getLogger(__name__)

NOME_CACHE = "sgs"
INICIO_PADRAO = "2010-01-01"
ANOS_POR_JANELA = 9  # o SGS limita séries diárias a 10 anos por consulta
TENTATIVAS = 3
PAUSA_SEGUNDOS = 2
COLUNAS = ["data", "serie", "valor"]


@dataclass(frozen=True)
class Serie:
    """Metadados de uma série do SGS."""

    codigo: int
    descricao: str
    unidade: str
    freq: str  # "D" diária, "M" mensal


SERIES: dict[str, Serie] = {
    "ipca": Serie(433, "IPCA, variação mensal", "% a.m.", "M"),
    "ibc_br": Serie(24364, "IBC-Br dessazonalizado (2002=100)", "índice", "M"),
    "selic_meta": Serie(432, "Meta Selic definida pelo Copom", "% a.a.", "D"),
    "selic_efetiva": Serie(4189, "Selic acumulada no mês, anualizada", "% a.a.", "M"),
    "cambio": Serie(1, "PTAX venda, BRL por USD", "BRL/USD", "D"),
    "desemprego": Serie(24369, "Taxa de desocupação PNAD Contínua, trimestre móvel", "%", "M"),
    "primario": Serie(
        5793,
        "Resultado primário do setor público consolidado, 12 meses "
        "(convenção NFSP: positivo = déficit)",
        "% PIB",
        "M",
    ),
    "conta_corrente": Serie(23079, "Transações correntes, 12 meses", "% PIB", "M"),
}


def vazio() -> pd.DataFrame:
    """DataFrame longo sem linhas, com as colunas padrão."""
    return pd.DataFrame({"data": pd.Series(dtype="datetime64[ns]"),
                         "serie": pd.Series(dtype="object"),
                         "valor": pd.Series(dtype="float64")})


def janelas(inicio: str, fim: str, anos: int = ANOS_POR_JANELA) -> list[tuple[str, str]]:
    """Divide [inicio, fim] em janelas de até ``anos`` anos-calendário, em ISO.

    Exemplo conferido à mão: ("2010-01-01", "2026-11-12", 9) vira
    [("2010-01-01", "2018-12-31"), ("2019-01-01", "2026-11-12")].
    """
    ini = date.fromisoformat(inicio)
    fim_d = date.fromisoformat(fim)
    saida: list[tuple[str, str]] = []
    while ini <= fim_d:
        corte = min(date(ini.year + anos - 1, 12, 31), fim_d)
        saida.append((ini.isoformat(), corte.isoformat()))
        ini = date(corte.year + 1, 1, 1)
    return saida


def normalizar(bruto: pd.DataFrame, nome: str) -> pd.DataFrame:
    """Converte a saída do ``bcb.sgs.get`` (índice Date, 1 coluna) para o formato longo."""
    if bruto.empty:
        return vazio()
    df = bruto.reset_index()
    df.columns = ["data", "valor"]
    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["serie"] = nome
    return df[COLUNAS]


def _get_com_tentativas(nome: str, codigo: int, ini: str, fim: str,
                        tentativas: int = TENTATIVAS) -> pd.DataFrame:
    """Chama ``bcb.sgs.get`` repetindo em falha transitória; relança na última."""
    for i in range(1, tentativas + 1):
        try:
            return _sgs.get({nome: codigo}, start=ini, end=fim)
        except Exception as exc:  # noqa: BLE001 - a API falha de formas variadas
            log.warning("sgs %s (%d) %s..%s tentativa %d/%d: %s",
                        nome, codigo, ini, fim, i, tentativas, exc)
            if i == tentativas:
                raise
            time.sleep(PAUSA_SEGUNDOS * i)
    raise RuntimeError("inalcançável")  # pragma: no cover


def baixar_serie(nome: str, inicio: str, fim: str | None = None) -> pd.DataFrame:
    """Baixa uma série do SGS entre ``inicio`` e ``fim`` (ISO), em formato longo.

    Falha (levanta exceção) se alguma janela não puder ser baixada, para não
    gravar cache com buracos.
    """
    serie = SERIES[nome]
    fim = fim or date.today().isoformat()
    partes = [normalizar(_get_com_tentativas(nome, serie.codigo, ini, fim_janela), nome)
              for ini, fim_janela in janelas(inicio, fim)]
    if not partes:
        return vazio()
    return pd.concat(partes, ignore_index=True)


def baixar(nomes: list[str] | None = None, inicio: str = INICIO_PADRAO) -> pd.DataFrame:
    """Baixa várias séries e concatena em formato longo."""
    nomes = nomes or list(SERIES)
    return pd.concat([baixar_serie(n, inicio) for n in nomes], ignore_index=True)


def combinar(antigo: pd.DataFrame, novo: pd.DataFrame) -> pd.DataFrame:
    """Une dois conjuntos longos, mantendo o valor mais novo em (serie, data)."""
    df = pd.concat([antigo, novo], ignore_index=True)
    df = df.drop_duplicates(subset=["serie", "data"], keep="last")
    return df.sort_values(["serie", "data"]).reset_index(drop=True)


def atualizar(inicio: str = INICIO_PADRAO) -> pd.DataFrame:
    """Atualiza o cache ``sgs.parquet`` buscando só o que falta desde a última data.

    Para cada série, rebaixa a partir da última data em cache (inclusive) para
    captar revisões da última observação.
    """
    antigo = cache.ler(NOME_CACHE) if cache.existe(NOME_CACHE) else vazio()
    partes = []
    for nome in SERIES:
        ultima = antigo.loc[antigo["serie"] == nome, "data"].max()
        desde = inicio if pd.isna(ultima) else ultima.date().isoformat()
        partes.append(baixar_serie(nome, desde))
    atualizado = combinar(antigo, pd.concat(partes, ignore_index=True))
    cache.gravar(NOME_CACHE, atualizado)
    return atualizado


def carregar() -> pd.DataFrame:
    """Lê o cache do SGS; atualiza se ainda não existir."""
    return cache.ler(NOME_CACHE) if cache.existe(NOME_CACHE) else atualizar()


def em_formato_largo(df: pd.DataFrame) -> pd.DataFrame:
    """Pivota o formato longo para colunas por série, índice ``data``."""
    return df.pivot(index="data", columns="serie", values="valor").sort_index()


def ultimo_valor(df: pd.DataFrame, nome: str) -> tuple[pd.Timestamp, float]:
    """Última observação não nula de ``nome``: (data, valor)."""
    s = df[(df["serie"] == nome) & df["valor"].notna()].sort_values("data").iloc[-1]
    return s["data"], float(s["valor"])
