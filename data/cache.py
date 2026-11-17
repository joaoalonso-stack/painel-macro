"""Cache local em parquet para os dados baixados.

Cada conjunto de dados vira um arquivo ``data/cache/<nome>.parquet``.
As funções são pequenas para que os módulos de coleta só precisem decidir
*o que* baixar, não *como* guardar.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data import CACHE_DIR

log = logging.getLogger(__name__)


def caminho(nome: str, pasta: Path | None = None) -> Path:
    """Retorna o caminho do parquet de ``nome`` dentro da pasta de cache."""
    return (pasta or CACHE_DIR) / f"{nome}.parquet"


def existe(nome: str, pasta: Path | None = None) -> bool:
    """Diz se já há cache gravado para ``nome``."""
    return caminho(nome, pasta).is_file()


def ler(nome: str, pasta: Path | None = None) -> pd.DataFrame:
    """Lê o parquet de ``nome``. Levanta ``FileNotFoundError`` se não existir."""
    return pd.read_parquet(caminho(nome, pasta))


def gravar(nome: str, df: pd.DataFrame, pasta: Path | None = None) -> Path:
    """Grava ``df`` como parquet de ``nome`` e devolve o caminho gravado."""
    destino = caminho(nome, pasta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(destino, index=False)
    log.info("cache gravado: %s (%d linhas)", destino.name, len(df))
    return destino


def idade_horas(nome: str, pasta: Path | None = None) -> float | None:
    """Horas desde a última gravação do cache, ou ``None`` se não existir."""
    arquivo = caminho(nome, pasta)
    if not arquivo.is_file():
        return None
    modificado = datetime.fromtimestamp(arquivo.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(tz=timezone.utc) - modificado).total_seconds() / 3600


def obter(
    nome: str,
    buscar: Callable[[], pd.DataFrame],
    ttl_horas: float = 12.0,
    forcar: bool = False,
    pasta: Path | None = None,
) -> pd.DataFrame:
    """Devolve o cache de ``nome`` se for recente; senão chama ``buscar`` e grava.

    ``ttl_horas`` define o que é "recente". ``forcar=True`` ignora o cache.
    """
    idade = idade_horas(nome, pasta)
    if not forcar and idade is not None and idade <= ttl_horas:
        return ler(nome, pasta)
    df = buscar()
    gravar(nome, df, pasta)
    return df
