"""Movimento de mercado: vértices da curva DI1, variações, inclinação e o que a
curva precifica para a próxima reunião.

Taxas em % a.a.; variações em pontos-base (bp).
"""

from __future__ import annotations

import pandas as pd

from analytics import curva

VERTICES = {"1a": 252, "2a": 504, "5a": 1260}


def taxas_vertices(di1_hist: pd.DataFrame, vertices: dict[str, int] = VERTICES) -> pd.DataFrame:
    """Uma linha por pregão com a taxa interpolada em cada vértice (colunas = nomes)."""
    nomes, dus = list(vertices), list(vertices.values())
    linhas = []
    for d, g in di1_hist.groupby("data"):
        linhas.append({"data": d, **dict(zip(nomes, map(float, curva.interpolar(g, dus))))})
    return pd.DataFrame(linhas).sort_values("data").reset_index(drop=True)


def pregao_ate(datas: pd.Series, data) -> pd.Timestamp | None:
    """Último pregão até ``data`` (inclusive)."""
    ate = datas[datas <= pd.Timestamp(data)]
    return ate.max() if not ate.empty else None


def variacoes_vertices(taxas: pd.DataFrame) -> pd.DataFrame:
    """Taxa de hoje por vértice e variação (bp) contra ontem, 7 e 30 dias corridos atrás.

    "Ontem" é o pregão anterior; "7 dias" e "30 dias" usam o último pregão até
    hoje − 7 e hoje − 30 dias corridos.

    Caso conferido à mão: 1a em 13.00 (d−31), 13.20 (d−8), 13.40 (d−1), 13.50 (d)
    dá +10, +30 e +50 bp.
    """
    t = taxas.set_index("data").sort_index()
    hoje = t.index.max()
    referencias = {"d1_bp": t.index[t.index < hoje].max() if len(t) > 1 else None,
                   "d7_bp": pregao_ate(t.index.to_series(), hoje - pd.Timedelta(days=7)),
                   "d30_bp": pregao_ate(t.index.to_series(), hoje - pd.Timedelta(days=30))}
    linhas = []
    for v in t.columns:
        linha = {"vertice": v, "taxa": t.loc[hoje, v]}
        for nome, ref in referencias.items():
            linha[nome] = (t.loc[hoje, v] - t.loc[ref, v]) * 100 if ref is not None else float("nan")
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    df.attrs["datas"] = {"hoje": hoje, **referencias}
    return df


def inclinacoes(taxas: pd.DataFrame) -> pd.DataFrame:
    """Inclinações em bp por pregão: 2a−1a e 5a−2a."""
    return pd.DataFrame({"data": taxas["data"],
                         "2a−1a": (taxas["2a"] - taxas["1a"]) * 100,
                         "5a−2a": (taxas["5a"] - taxas["2a"]) * 100})


def curva_em(di1_hist: pd.DataFrame, data) -> pd.DataFrame:
    """Curva do último pregão até ``data``."""
    d = pregao_ate(di1_hist["data"].drop_duplicates(), data)
    return di1_hist[di1_hist["data"] == d].reset_index(drop=True)


def movimento_proxima_reuniao(implicita: pd.DataFrame, passo: float = 0.25) -> dict:
    """O que a curva precifica para a próxima reunião.

    Diferença entre a taxa do período após a próxima reunião e a do período
    atual (ambas em CDI, o spread para a Selic cancela), em p.p., e a
    probabilidade equivalente de um movimento de ``passo`` p.p.

    Caso conferido à mão: 13.655 → 13.684 é +0.029 p.p. = 12% de alta de 25 bp.
    """
    atual, prox = implicita.iloc[0], implicita.iloc[1]
    variacao = float(prox["implicita"] - atual["implicita"])
    prob = max(-1.0, min(1.0, variacao / passo))
    return {"reuniao": prox["reuniao"], "data_decisao": prox["data_decisao"],
            "variacao_pp": variacao, "sentido": "alta" if variacao >= 0 else "corte",
            "probabilidade": abs(prob), "passo_pp": passo}
