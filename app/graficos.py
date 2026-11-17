"""Figuras Plotly do painel. Funções puras: recebem DataFrames, devolvem ``go.Figure``.

Tema neutro, sem marca: slots 1-3 da paleta categórica de referência do guia
de dataviz (azul, laranja, verde-água), em ordem fixa e com um passo próprio
para o modo escuro; os valores são os documentados como validados para
daltonismo e contraste. Polaridade: vermelho (alta) e azul (queda), par
quente/frio do guia. Tinta de texto neutra e grade em linha fina.
Marcas finas: linhas de 2 px, marcadores de 8 px, grade discreta, uma só
escala por gráfico.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

SERIE = {"light": ["#2a78d6", "#eb6834", "#1baf7a"],
         "dark": ["#3987e5", "#d95926", "#199e70"]}
POLARIDADE = {"light": {"alta": "#e34948", "queda": "#2a78d6"},
              "dark": {"alta": "#e66767", "queda": "#3987e5"}}
TEXTO = {"light": {"primario": "#0b0b0b", "secundario": "#52514e", "grade": "#e1e0d9"},
         "dark": {"primario": "#f0efec", "secundario": "#c3c2b7", "grade": "#2c2c2a"}}


def _layout(fig: go.Figure, modo: str, titulo_y: str, altura: int = 380) -> go.Figure:
    """Aplica o layout comum: fundo transparente, grade discreta, legenda no topo."""
    t = TEXTO[modo]
    fig.update_layout(
        height=altura, margin=dict(l=8, r=8, t=28, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["primario"], size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=t["secundario"])),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=t["grade"], tickfont=dict(color=t["secundario"]))
    fig.update_yaxes(title=titulo_y, gridcolor=t["grade"], zeroline=False,
                     tickfont=dict(color=t["secundario"]), title_font=dict(color=t["secundario"]))
    return fig


def implicita_vs_focus(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Selic implícita na curva x mediana do Focus, por reunião (eixo categórico)."""
    c = SERIE[modo]
    d = df[df["reuniao"] != "atual"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["reuniao"], y=d["implicita"], name="Selic implícita (DI1)",
                             mode="lines+markers", line=dict(color=c[0], width=2),
                             marker=dict(size=8), hovertemplate="%{y:.2f}% a.a.<extra>DI1</extra>"))
    fig.add_trace(go.Scatter(x=d["reuniao"], y=d["focus"], name="Focus (mediana)",
                             mode="lines+markers", line=dict(color=c[1], width=2, dash="dot"),
                             marker=dict(size=8), hovertemplate="%{y:.2f}% a.a.<extra>Focus</extra>"))
    return _layout(fig, modo, "% a.a.")


def curva_di1(curva_dia: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Curva DI1 do pregão (taxa de ajuste por vencimento). Série única: sem legenda."""
    d = curva_dia.sort_values("vencimento")
    fig = go.Figure(go.Scatter(x=d["vencimento"], y=d["taxa_ajuste"], mode="lines+markers",
                               line=dict(color=SERIE[modo][0], width=2), marker=dict(size=6),
                               customdata=d["codigo"], showlegend=False,
                               hovertemplate="%{customdata}: %{y:.2f}% a.a.<extra></extra>"))
    return _layout(fig, modo, "% a.a.", altura=320)


def historico(serie: pd.DataFrame, nome: str, unidade: str, modo: str = "light") -> go.Figure:
    """Histórico de uma série (``data``, ``valor``). Série única: sem legenda."""
    fig = go.Figure(go.Scatter(x=serie["data"], y=serie["valor"], mode="lines", name=nome,
                               line=dict(color=SERIE[modo][0], width=2), showlegend=False,
                               hovertemplate="%{y:.2f}<extra></extra>"))
    return _layout(fig, modo, unidade, altura=320)


def tom_copom(df: pd.DataFrame, modo: str = "light") -> go.Figure:
    """Índice de tom por reunião: barras agrupadas para comunicado e ata."""
    c = SERIE[modo]
    fig = go.Figure()
    for i, tipo in enumerate(["comunicado", "ata"]):
        d = df[df["tipo"] == tipo]
        fig.add_trace(go.Bar(x=d["nro_reuniao"].astype(str), y=d["indice"], name=tipo,
                             marker_color=c[i], hovertemplate="%{y:.2f}<extra>" + tipo + "</extra>"))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.1)
    fig = _layout(fig, modo, "índice (−1 dovish … +1 hawkish)")
    fig.update_xaxes(title="reunião", type="category")
    return fig


def reacao_di1(df: pd.DataFrame, coluna: str = "delta_1a_bp", modo: str = "light") -> go.Figure:
    """Variação do DI1 (bp) no pregão seguinte a cada comunicado; cor pela polaridade."""
    d = df[(df["tipo"] == "comunicado")].dropna(subset=[coluna])
    cores = [POLARIDADE[modo]["alta"] if v >= 0 else POLARIDADE[modo]["queda"] for v in d[coluna]]
    fig = go.Figure(go.Bar(x=d["nro_reuniao"].astype(str), y=d[coluna], marker_color=cores,
                           showlegend=False, hovertemplate="%{y:+.1f} bp<extra></extra>"))
    fig = _layout(fig, modo, "bp")
    fig.update_xaxes(title="reunião", type="category")
    fig.update_yaxes(zeroline=True, zerolinecolor=TEXTO[modo]["secundario"], zerolinewidth=1)
    return fig


def linhas(largo: pd.DataFrame, titulo_y: str, modo: str = "light",
           linhas_ref: dict[str, float] | None = None, altura: int = 340, casas: int = 2) -> go.Figure:
    """Até três séries (colunas de ``largo``, índice = datas) com legenda e linhas de referência.

    ``linhas_ref`` desenha referências horizontais tracejadas (meta, banda) em cinza.
    """
    c = SERIE[modo]
    fig = go.Figure()
    for i, col in enumerate(list(largo.columns)[:3]):
        fig.add_trace(go.Scatter(x=largo.index, y=largo[col], name=str(col), mode="lines",
                                 line=dict(color=c[i], width=2),
                                 hovertemplate="%{y:." + str(casas) + "f}<extra>" + str(col) + "</extra>"))
    for rotulo, y in (linhas_ref or {}).items():
        fig.add_hline(y=y, line=dict(color=TEXTO[modo]["secundario"], width=1, dash="dash"),
                      annotation_text=rotulo, annotation_position="top left",
                      annotation_font=dict(color=TEXTO[modo]["secundario"], size=11))
    fig = _layout(fig, modo, titulo_y, altura=altura)
    if len(largo.columns) == 1:
        fig.update_layout(showlegend=False)
    return fig


def curvas_sobrepostas(curva_hoje: pd.DataFrame, curva_passada: pd.DataFrame,
                       rotulo_hoje: str, rotulo_passada: str, modo: str = "light") -> go.Figure:
    """Curva de hoje sobre a curva passada, eixo em anos (dias úteis / 252)."""
    c = SERIE[modo]
    fig = go.Figure()
    for i, (cv, rot, tracejado) in enumerate([(curva_hoje, rotulo_hoje, None), (curva_passada, rotulo_passada, "dot")]):
        d = cv.sort_values("dias_uteis")
        fig.add_trace(go.Scatter(x=d["dias_uteis"] / 252, y=d["taxa_ajuste"], name=rot, mode="lines+markers",
                                 line=dict(color=c[i], width=2, dash=tracejado), marker=dict(size=6),
                                 hovertemplate="%{y:.2f}% a.a.<extra>" + rot + "</extra>"))
    fig = _layout(fig, modo, "% a.a.", altura=340)
    fig.update_xaxes(title="prazo (anos)")
    return fig


def histograma_reacao(df: pd.DataFrame, coluna: str = "delta_1a_bp", modo: str = "light") -> go.Figure:
    """Distribuição da variação do DI1 por tipo de documento (histogramas sobrepostos)."""
    c = SERIE[modo]
    fig = go.Figure()
    for i, tipo in enumerate(["comunicado", "ata"]):
        d = df[df["tipo"] == tipo].dropna(subset=[coluna])
        fig.add_trace(go.Histogram(x=d[coluna], name=tipo, marker_color=c[i], opacity=0.65,
                                   xbins=dict(size=5), hovertemplate="%{x} bp: %{y}<extra>" + tipo + "</extra>"))
    fig.update_layout(barmode="overlay")
    fig = _layout(fig, modo, "nº de documentos", altura=320)
    fig.update_xaxes(title="variação (bp)")
    fig.update_layout(hovermode="x")
    return fig


def dispersao_tom_reacao(df: pd.DataFrame, coluna: str = "delta_1a_bp", modo: str = "light") -> go.Figure:
    """Índice de tom do comunicado x reação do DI1 (um ponto por reunião)."""
    d = df[df["tipo"] == "comunicado"].dropna(subset=[coluna])
    fig = go.Figure(go.Scatter(x=d["indice"], y=d[coluna], mode="markers", showlegend=False,
                               marker=dict(size=9, color=SERIE[modo][0], opacity=0.8,
                                           line=dict(width=1, color="rgba(255,255,255,0.6)")),
                               customdata=d["nro_reuniao"],
                               hovertemplate="reunião %{customdata}: tom %{x:.2f}, %{y:+.1f} bp<extra></extra>"))
    fig = _layout(fig, modo, "variação (bp)", altura=320)
    fig.update_xaxes(title="índice de tom", showgrid=True, gridcolor=TEXTO[modo]["grade"], zeroline=False)
    fig.update_yaxes(zeroline=True, zerolinecolor=TEXTO[modo]["secundario"], zerolinewidth=1)
    fig.update_layout(hovermode="closest")
    return fig
