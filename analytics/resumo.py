"""Imprime as tabelas da Etapa 2 a partir dos caches.

Uso: ``python -m analytics.resumo`` (rode ``python -m data.atualizar`` antes).
"""

from __future__ import annotations

import pandas as pd

from analytics import curva, indicadores
from data import copom, di1, focus, sgs


def tabela_selic_implicita() -> pd.DataFrame:
    """Selic implícita na última curva x Focus por reunião."""
    ultima = di1.ultima_curva(di1.carregar())
    data_ref = ultima["data"].max().date().isoformat()
    reunioes = copom.proximas(copom.carregar(), data_ref, n=9)
    _, selic_atual = sgs.ultimo_valor(sgs.carregar(), "selic_meta")
    implic = curva.selic_implicita(ultima, reunioes, data_ref, selic_atual)
    f = focus.ultima_pesquisa(focus.carregar_selic())
    return curva.comparar_com_focus(implic, f)


def mostrar(titulo: str, df: pd.DataFrame, casas: int = 3) -> None:
    """Imprime ``df`` com título, arredondando só as colunas numéricas."""
    numericas = df.select_dtypes("number").columns
    print(f"\n== {titulo} ==")
    print(df.assign(**{c: df[c].round(casas) for c in numericas}).to_string(index=False))


def main() -> None:
    """Mostra variações de um mês, realizado x Focus e Selic implícita x Focus."""
    pd.set_option("display.width", 160)
    s = sgs.carregar()
    mostrar("Variação contra um mês antes", indicadores.tabela_variacoes(s))
    ano = int(s["data"].max().year)
    mostrar(f"Realizado x Focus ({ano})", indicadores.contra_focus(s, focus.carregar_anual(), ano))
    mostrar("Selic implícita (DI1) x Focus por reunião", tabela_selic_implicita())


if __name__ == "__main__":
    main()
