"""Ponto de entrada para atualizar todos os caches.

Uso: ``python -m data.atualizar`` (na raiz do projeto, com o .venv ativo).
"""

from __future__ import annotations

import logging

import pandas as pd

from data import di1, focus, sgs


def _resumo(nome: str, df: pd.DataFrame) -> dict:
    """Uma linha de resumo: conjunto, nº de linhas e última data."""
    ultima = df["data"].max() if not df.empty else pd.NaT
    return {"conjunto": nome, "linhas": len(df),
            "ultima_data": ultima.date().isoformat() if pd.notna(ultima) else "-"}


def atualizar_tudo() -> pd.DataFrame:
    """Atualiza SGS, Focus e DI1 e devolve um resumo por conjunto."""
    linhas = [_resumo("sgs", sgs.atualizar())]
    anual, selic = focus.atualizar()
    linhas += [_resumo("focus_anual", anual), _resumo("focus_selic", selic)]
    linhas.append(_resumo("di1", di1.atualizar()))
    return pd.DataFrame(linhas)


def main() -> None:
    """Executa a atualização completa e imprime o resumo."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print(atualizar_tudo().to_string(index=False))


if __name__ == "__main__":
    main()
