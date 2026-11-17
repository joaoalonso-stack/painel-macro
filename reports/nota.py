"""Rascunho da nota matinal em markdown, montado a partir das tabelas do painel.

É um rascunho: a nota só sai depois de revisão humana. O texto deixa isso
explícito no cabeçalho e no rodapé.

Uso: ``python -m reports.nota`` grava ``reports/saida/nota_AAAA-MM-DD.md``.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from data.sgs import SERIES

PASTA_SAIDA = Path(__file__).resolve().parent / "saida"
AVISO = "_Rascunho gerado automaticamente a partir de dados públicos (BCB, B3). Revisar antes de distribuir._"
ORDEM = ["ipca", "ibc_br", "selic_meta", "cambio", "desemprego", "primario", "conta_corrente"]


def fmt(v, casas: int = 2, sinal: bool = False) -> str:
    """Número com vírgula decimal; ``—`` para nulo."""
    if v is None or pd.isna(v):
        return "—"
    s = f"{v:+.{casas}f}" if sinal else f"{v:.{casas}f}"
    return s.replace(".", ",")


def bloco_indicadores(variacoes: pd.DataFrame) -> str:
    """Lista com a última leitura de cada série e a variação contra um mês antes."""
    v = variacoes.set_index("serie")
    linhas = ["## Indicadores", ""]
    for nome in ORDEM:
        if nome not in v.index:
            continue
        r = v.loc[nome]
        unidade = "%" if r["tipo"] == "pct" else "p.p."
        linhas.append(f"- **{SERIES[nome].descricao}**: {fmt(r['valor'])} {SERIES[nome].unidade} "
                      f"({r['data']:%Y-%m-%d}); {fmt(r['variacao'], sinal=True)} {unidade} contra um mês antes.")
    return "\n".join(linhas)


def bloco_focus(ano: int, contra_focus: pd.DataFrame) -> str:
    """Tabela realizado x Focus do ano."""
    linhas = [f"## Realizado x Focus ({ano})", "", "| Indicador | Realizado | Focus | Diferença | Nota |",
              "|---|---:|---:|---:|---|"]
    for _, r in contra_focus.iterrows():
        linhas.append(f"| {r['indicador']} | {fmt(r['realizado'])} | {fmt(r['focus'])} | "
                      f"{fmt(r['diferenca'], sinal=True)} | {r['nota']} |")
    return "\n".join(linhas)


def bloco_curva(data_ref: str, implicita: pd.DataFrame, n: int = 4) -> str:
    """Leitura da curva: implícita x Focus nas próximas reuniões e o prêmio."""
    d = implicita[implicita["reuniao"] != "atual"].head(n)
    atual = implicita.iloc[0]
    linhas = [f"## Curva de juros (DI1 de {data_ref})", "",
              f"Taxa até a próxima reunião: {fmt(atual['implicita'])}% a.a. "
              f"({fmt(atual['variacao'], sinal=True)} p.p. contra a meta, spread CDI-Selic).", "",
              "| Reunião | Implícita | Focus | Prêmio |", "|---|---:|---:|---:|"]
    for _, r in d.iterrows():
        linhas.append(f"| {r['reuniao']} | {fmt(r['implicita'])} | {fmt(r['focus'])} | {fmt(r['premio'], sinal=True)} |")
    premio = d["premio"].dropna()
    if not premio.empty:
        sentido = "acima" if premio.mean() > 0 else "abaixo"
        linhas += ["", f"A curva precifica Selic em média {fmt(abs(premio.mean()))} p.p. {sentido} do Focus "
                       f"nas próximas {len(premio)} reuniões."]
    return "\n".join(linhas)


def bloco_mercado(variacoes: pd.DataFrame, movimento: dict | None) -> str:
    """Vértices do DI1 com variações e o que a curva precifica para a próxima reunião."""
    linhas = ["## Mercado (DI1)", "", "| Vértice | Taxa | Dia | 7 dias | 30 dias |", "|---|---:|---:|---:|---:|"]
    for _, r in variacoes.iterrows():
        linhas.append(f"| {r['vertice']} | {fmt(r['taxa'])}% | {fmt(r['d1_bp'], 0, True)} bp | "
                      f"{fmt(r['d7_bp'], 0, True)} bp | {fmt(r['d30_bp'], 0, True)} bp |")
    if movimento:
        linhas += ["", f"Para {movimento['reuniao']} a curva precifica {fmt(movimento['variacao_pp'] * 100, 0, True)} bp, "
                       f"equivalente a {movimento['probabilidade']:.0%} de probabilidade de {movimento['sentido']} de 25 bp."]
    return "\n".join(linhas)


def bloco_copom(ultimo: dict | None) -> str:
    """Último comunicado: índice de tom, mudança contra o anterior e reação do DI1."""
    if not ultimo:
        return "## Copom\n\nSem comunicado em cache."
    tom = "hawkish" if ultimo["indice"] > 0 else "dovish"
    linhas = ["## Copom", "",
              f"Último comunicado ({ultimo['data']:%Y-%m-%d}, {ultimo['nro_reuniao']}ª reunião): "
              f"índice de tom {fmt(ultimo['indice'])} ({tom}), {fmt(ultimo['delta_indice'], sinal=True)} "
              f"contra o comunicado anterior."]
    if not pd.isna(ultimo.get("delta_1a_bp")):
        linhas.append(f"Reação do DI1 no pregão seguinte: {fmt(ultimo['delta_1a_bp'], 1, True)} bp em 1 ano, "
                      f"{fmt(ultimo['delta_2a_bp'], 1, True)} bp em 2 anos.")
    return "\n".join(linhas)


def montar_nota(dia: date, variacoes: pd.DataFrame, ano: int, contra_focus: pd.DataFrame,
                data_ref: str, implicita: pd.DataFrame, ultimo_copom: dict | None,
                mercado: tuple[pd.DataFrame, dict | None] | None = None) -> str:
    """Monta o markdown completo da nota do dia ``dia``.

    ``mercado`` é opcional: (variações dos vértices, movimento da próxima reunião).
    """
    partes = [f"# Nota matinal, {dia:%Y-%m-%d}", "", AVISO, ""]
    if mercado is not None:
        partes += [bloco_mercado(*mercado), ""]
    partes += [bloco_indicadores(variacoes), "", bloco_focus(ano, contra_focus), "",
               bloco_curva(data_ref, implicita), "", bloco_copom(ultimo_copom), "", "---", AVISO]
    return "\n".join(partes) + "\n"


def salvar(texto: str, dia: date, pasta: Path | None = None) -> Path:
    """Grava ``nota_AAAA-MM-DD.md`` em ``pasta`` (padrão: reports/saida/) e devolve o caminho."""
    destino = (pasta or PASTA_SAIDA) / f"nota_{dia:%Y-%m-%d}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    return destino


def ultimo_comunicado(tom_evento: pd.DataFrame) -> dict | None:
    """Linha do comunicado mais recente da tabela tom x evento, como dicionário."""
    c = tom_evento[tom_evento["tipo"] == "comunicado"].sort_values("nro_reuniao")
    if c.empty:
        return None
    r = c.iloc[-1]
    return {"nro_reuniao": int(r["nro_reuniao"]), "data": r["data_evento"], "indice": r["indice"],
            "delta_indice": r["delta_indice"], "delta_1a_bp": r["delta_1a_bp"], "delta_2a_bp": r["delta_2a_bp"]}


def gerar(dia: date | None = None) -> tuple[str, Path]:
    """Gera a nota do dia a partir dos caches e grava em reports/saida/."""
    from analytics import curva, indicadores, mercado
    from copom import evento, fontes, tom
    from data import copom as copom_cal
    from data import di1, focus, sgs

    dia = dia or date.today()
    s = sgs.carregar()
    ano = int(s["data"].max().year)
    ultima = di1.ultima_curva(di1.carregar())
    data_ref = ultima["data"].max().date().isoformat()
    reunioes = copom_cal.proximas(copom_cal.carregar(), data_ref, n=9)
    _, selic_atual = sgs.ultimo_valor(s, "selic_meta")
    implic = curva.comparar_com_focus(curva.selic_implicita(ultima, reunioes, data_ref, selic_atual),
                                      focus.ultima_pesquisa(focus.carregar_selic()))
    textos = fontes.carregar()
    ev = evento.estudo_evento(evento.taxas_por_pregao(di1.carregar()), evento.eventos_de(textos))
    te = evento.juntar_tom_e_evento(tom.tabela_tom(textos), ev)
    hist = di1.carregar()
    merc = (mercado.variacoes_vertices(mercado.taxas_vertices(hist)), mercado.movimento_proxima_reuniao(implic))
    texto = montar_nota(dia, indicadores.tabela_variacoes(s), ano,
                        indicadores.contra_focus(s, focus.carregar_anual(), ano),
                        data_ref, implic, ultimo_comunicado(te), merc)
    return texto, salvar(texto, dia)


if __name__ == "__main__":
    _, caminho = gerar()
    print(f"nota gravada em {caminho}")
