"""Estudo de evento: variação do DI1 de 1 e 2 anos em torno de cada documento do Copom.

Comunicado: sai após o fechamento do dia da decisão, logo a janela é
``fechamento do dia da decisão → fechamento do pregão seguinte``.
Ata: sai às 8h do dia de publicação, logo a janela é
``fechamento do pregão anterior → fechamento do dia de publicação``.

Taxas em % a.a. interpoladas (flat-forward) em 252 e 504 dias úteis;
variações em pontos-base (1 p.p. = 100 bp).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics import curva

VERTICES = {"taxa_1a": 252, "taxa_2a": 504}


def taxas_1a_2a(curva_dia: pd.DataFrame) -> dict:
    """Taxas interpoladas em 1 e 2 anos (252 e 504 du) de uma curva de um pregão."""
    valores = curva.interpolar(curva_dia, list(VERTICES.values()))
    return dict(zip(VERTICES, (float(v) for v in valores)))


def taxas_por_pregao(di1_hist: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por pregão: data, taxa_1a, taxa_2a."""
    linhas = [{"data": d, **taxas_1a_2a(g)} for d, g in di1_hist.groupby("data")]
    return pd.DataFrame(linhas).sort_values("data").reset_index(drop=True)


def pregao_apos(pregoes: pd.Series, data) -> pd.Timestamp | None:
    """Primeiro pregão estritamente depois de ``data``."""
    depois = pregoes[pregoes > pd.Timestamp(data)]
    return depois.min() if not depois.empty else None


def pregao_ate(pregoes: pd.Series, data) -> pd.Timestamp | None:
    """Último pregão até ``data`` (inclusive)."""
    ate = pregoes[pregoes <= pd.Timestamp(data)]
    return ate.max() if not ate.empty else None


def janela(pregoes: pd.Series, data_evento, apos_fechamento: bool) -> tuple:
    """(pregão antes, pregão depois) do evento.

    Evento após o fechamento (comunicado): antes = último pregão até a data,
    depois = pregão seguinte. Evento antes da abertura (ata): antes = último
    pregão anterior à data, depois = pregão da própria data (ou o seguinte).
    """
    d = pd.Timestamp(data_evento)
    if apos_fechamento:
        return pregao_ate(pregoes, d), pregao_apos(pregoes, d)
    return pregao_ate(pregoes, d - pd.Timedelta(days=1)), pregao_ate(pregoes, pregao_apos(pregoes, d - pd.Timedelta(days=1)))


def estudo_evento(taxas: pd.DataFrame, eventos: pd.DataFrame) -> pd.DataFrame:
    """Variação em bp das taxas de 1 e 2 anos em torno de cada evento.

    ``taxas`` vem de ``taxas_por_pregao``; ``eventos`` tem ``nro_reuniao``,
    ``tipo``, ``data_evento`` e ``apos_fechamento``.

    Caso conferido à mão: curva flat em 13.00% no pregão anterior e 13.25% no
    seguinte dá +25 bp nos dois vértices.
    """
    t = taxas.set_index("data")
    pregoes = taxas["data"]
    linhas = []
    for _, e in eventos.iterrows():
        antes, depois = janela(pregoes, e["data_evento"], bool(e["apos_fechamento"]))
        linha = {"nro_reuniao": int(e["nro_reuniao"]), "tipo": e["tipo"],
                 "data_evento": pd.Timestamp(e["data_evento"]),
                 "pregao_antes": antes, "pregao_depois": depois}
        for col in VERTICES:
            ok = antes is not None and depois is not None
            linha[f"{col}_antes"] = t.loc[antes, col] if ok else np.nan
            linha[f"{col}_depois"] = t.loc[depois, col] if ok else np.nan
            linha[f"delta_{col[-2:]}_bp"] = (linha[f"{col}_depois"] - linha[f"{col}_antes"]) * 100
        linhas.append(linha)
    return pd.DataFrame(linhas)


def eventos_de(textos: pd.DataFrame) -> pd.DataFrame:
    """Converte o cache de textos em eventos: comunicado após o fechamento, ata antes da abertura."""
    ev = textos[["nro_reuniao", "tipo", "data_decisao", "data_publicacao"]].copy()
    ev["data_evento"] = np.where(ev["tipo"] == "comunicado", ev["data_decisao"], ev["data_publicacao"])
    ev["data_evento"] = pd.to_datetime(ev["data_evento"])
    ev["apos_fechamento"] = ev["tipo"] == "comunicado"
    return ev[["nro_reuniao", "tipo", "data_evento", "apos_fechamento"]]


def variacao_indice(tom: pd.DataFrame) -> pd.Series:
    """Mudança do índice contra o documento anterior do mesmo tipo (a "surpresa" de tom).

    Caso conferido à mão: índices 0.2, 0.5 em comunicados seguidos dão NaN, +0.3.
    """
    ordenado = tom.sort_values(["tipo", "nro_reuniao"])
    return ordenado.groupby("tipo")["indice"].diff().reindex(tom.index)


def juntar_tom_e_evento(tom: pd.DataFrame, evento: pd.DataFrame) -> pd.DataFrame:
    """Tabela final por documento: índice de tom, sua variação e a variação do DI1."""
    cols = ["nro_reuniao", "tipo", "data_evento", "pregao_antes", "pregao_depois",
            "delta_1a_bp", "delta_2a_bp"]
    df = tom.merge(evento[cols], on=["nro_reuniao", "tipo"], how="left")
    df["delta_indice"] = variacao_indice(df)
    return df.sort_values(["nro_reuniao", "tipo"]).reset_index(drop=True)


def correlacao(df: pd.DataFrame, tipo: str) -> dict:
    """Correlação do índice (nível e variação) com a variação do DI1 para documentos de ``tipo``."""
    d = df[df["tipo"] == tipo].dropna(subset=["delta_1a_bp", "delta_2a_bp"])
    poucos = len(d) <= 2
    dv = d.dropna(subset=["delta_indice"]) if "delta_indice" in d else d.iloc[0:0]
    return {"tipo": tipo, "n": len(d),
            "corr_nivel_1a": np.nan if poucos else d["indice"].corr(d["delta_1a_bp"]),
            "corr_nivel_2a": np.nan if poucos else d["indice"].corr(d["delta_2a_bp"]),
            "corr_variacao_1a": np.nan if len(dv) <= 2 else dv["delta_indice"].corr(dv["delta_1a_bp"]),
            "corr_variacao_2a": np.nan if len(dv) <= 2 else dv["delta_indice"].corr(dv["delta_2a_bp"])}
