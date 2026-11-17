"""Curva DI1: interpolação flat-forward, taxas a termo e Selic implícita por reunião.

Taxas em % a.a., capitalização composta em dias úteis base 252.
A curva é um DataFrame com ``dias_uteis`` e uma coluna de taxa (padrão
``taxa_ajuste``), como sai de ``data.di1``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pyield import du as _du

BASE = 252


def fator(taxa: float | np.ndarray, dias_uteis: float | np.ndarray) -> np.ndarray:
    """Fator de capitalização de ``taxa`` (% a.a.) por ``dias_uteis``."""
    return (1 + np.asarray(taxa, float) / 100) ** (np.asarray(dias_uteis, float) / BASE)


def taxa(fator_: float | np.ndarray, dias_uteis: float | np.ndarray) -> np.ndarray:
    """Taxa (% a.a.) equivalente a ``fator_`` em ``dias_uteis``."""
    return (np.asarray(fator_, float) ** (BASE / np.asarray(dias_uteis, float)) - 1) * 100


def _vertices(curva: pd.DataFrame, coluna: str) -> tuple[np.ndarray, np.ndarray]:
    """Vértices (dias úteis, taxa) ordenados e sem duplicatas."""
    v = (curva[["dias_uteis", coluna]].dropna()
         .drop_duplicates("dias_uteis").sort_values("dias_uteis"))
    return v["dias_uteis"].to_numpy(float), v[coluna].to_numpy(float)


def interpolar(curva: pd.DataFrame, dias_uteis, coluna: str = "taxa_ajuste") -> np.ndarray:
    """Taxa interpolada flat-forward nos prazos ``dias_uteis``.

    Entre vértices, o log do fator é linear no prazo (taxa a termo constante).
    Antes do primeiro vértice e depois do último, repete a taxa do vértice.

    Caso conferido à mão: vértices (21 du, 12%) e (63 du, 14%) dão 13.4966% em 42 du.
    """
    du_v, r_v = _vertices(curva, coluna)
    alvo = np.asarray(dias_uteis, float)
    log_fator = np.interp(alvo, du_v, np.log(fator(r_v, du_v)))
    with np.errstate(divide="ignore", invalid="ignore"):
        saida = taxa(np.exp(log_fator), alvo)
    saida = np.where(alvo <= du_v[0], r_v[0], saida)
    return np.where(alvo >= du_v[-1], r_v[-1], saida)


def taxa_a_termo(curva: pd.DataFrame, du_inicio, du_fim, coluna: str = "taxa_ajuste") -> np.ndarray:
    """Taxa a termo (% a.a.) entre ``du_inicio`` e ``du_fim``. ``du_inicio = 0`` é a data base.

    Caso conferido à mão: vértices (21, 12%) e (63, 14%) dão 15.0133% entre 21 e 63.
    """
    ini = np.asarray(du_inicio, float)
    fim = np.asarray(du_fim, float)
    f_ini = np.where(ini > 0, fator(interpolar(curva, ini, coluna), ini), 1.0)
    f_fim = fator(interpolar(curva, fim, coluna), fim)
    return taxa(f_fim / f_ini, fim - ini)


def contar_dias_uteis(data_ref: str, datas) -> np.ndarray:
    """Dias úteis de ``data_ref`` (inclusive) até cada data (exclusive), feriados BR."""
    dias = pd.to_datetime(pd.Series(list(datas))).dt.date.tolist()
    return np.asarray(_du.contar(data_ref, dias).to_list(), int)


def selic_implicita(curva: pd.DataFrame, reunioes: pd.DataFrame, data_ref: str,
                    selic_atual: float, dias_uteis=None,
                    coluna: str = "taxa_ajuste") -> pd.DataFrame:
    """Selic implícita na curva por período entre reuniões do Copom.

    ``reunioes`` tem ``reuniao``, ``data_decisao`` e ``data_efetividade`` das
    próximas reuniões, em ordem. A implícita da reunião *i* é a taxa a termo
    entre a efetividade de *i* e a de *i+1*; a última reunião só fecha o
    período anterior. A linha ``atual`` cobre de ``data_ref`` até a primeira
    efetividade e serve de conferência com a Selic vigente (o DI segue o
    CDI, que costuma rodar cerca de 0,10 p.p. abaixo da meta).

    ``dias_uteis`` permite passar os prazos já contados (útil em testes).
    """
    r = reunioes.sort_values("data_efetividade").reset_index(drop=True)
    du_fim = np.asarray(dias_uteis, int) if dias_uteis is not None \
        else contar_dias_uteis(data_ref, r["data_efetividade"])
    du_ini = np.concatenate([[0], du_fim[:-1]])
    implic = taxa_a_termo(curva, du_ini, du_fim, coluna)
    df = pd.DataFrame({
        "reuniao": ["atual", *r["reuniao"].iloc[:-1]],
        "data_decisao": [pd.NaT, *r["data_decisao"].iloc[:-1]],
        "inicio": [pd.Timestamp(data_ref), *r["data_efetividade"].iloc[:-1]],
        "fim": r["data_efetividade"].to_list(),
        "du_inicio": du_ini, "du_fim": du_fim, "implicita": implic,
    })
    df["variacao"] = df["implicita"].diff()
    df.loc[0, "variacao"] = df.loc[0, "implicita"] - selic_atual
    return df


def comparar_com_focus(implicita: pd.DataFrame, focus_selic: pd.DataFrame) -> pd.DataFrame:
    """Junta a Selic implícita com a mediana do Focus por reunião; ``premio`` = implícita − Focus."""
    f = focus_selic[["reuniao", "mediana"]].rename(columns={"mediana": "focus"})
    df = implicita.merge(f, on="reuniao", how="left")
    df["premio"] = df["implicita"] - df["focus"]
    return df
