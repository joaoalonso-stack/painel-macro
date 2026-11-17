"""Painel Macro em Streamlit.

Uso (na raiz do projeto): ``streamlit run app/painel.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # raiz do projeto

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from analytics import expectativas, mercado  # noqa: E402
from app import dados, graficos  # noqa: E402
from copom import tom  # noqa: E402
from data.sgs import SERIES  # noqa: E402
from reports import nota  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"
ICONE = ASSETS / "icone.svg"
ICONE_BRANCO = ASSETS / "icone-branco.svg"
DISCLAIMER = ("Projeto de portfólio independente, feito só com dados públicos do BCB e da B3. "
              "Não é recomendação de investimento.")

st.set_page_config(page_title="Painel Macro", page_icon=str(ICONE), layout="wide")

ROTULOS = {
    "ipca": "IPCA (% a.m.)", "ibc_br": "IBC-Br (índice)", "selic_meta": "Selic meta (% a.a.)",
    "selic_efetiva": "Selic efetiva (% a.a.)", "cambio": "PTAX (BRL/USD)",
    "desemprego": "Desemprego (%)", "primario": "Resultado primário 12 m (% PIB, + = déficit)",
    "conta_corrente": "Conta corrente 12 m (% PIB)",
}


def modo_tema() -> str:
    """'dark' ou 'light', conforme o tema ativo do Streamlit."""
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:  # noqa: BLE001 - versões antigas não expõem o tema
        return "light"


def fmt_variacao(v: float, tipo: str) -> str:
    """Formata a variação com sinal e unidade."""
    if pd.isna(v):
        return "—"
    return f"{v:+.2f} {'%' if tipo == 'pct' else 'p.p.'}"


def secao_indicadores(modo: str) -> None:
    """Cartões com a última leitura, tabela realizado x Focus e histórico escolhido."""
    st.subheader("Indicadores")
    var = dados.tabela_variacoes().set_index("serie")
    ordem = ["ipca", "ibc_br", "selic_meta", "cambio", "desemprego", "primario", "conta_corrente"]
    colunas = st.columns(len(ordem))
    for col, nome in zip(colunas, ordem):
        r = var.loc[nome]
        col.metric(ROTULOS[nome], f"{r['valor']:.2f}", fmt_variacao(r["variacao"], r["tipo"]),
                   help=f"Última: {r['data']:%Y-%m-%d}. Variação contra {r['data_anterior']:%Y-%m-%d}.")
    ano, cf = dados.tabela_contra_focus()
    esq, dir_ = st.columns([1, 2])
    with esq:
        st.markdown(f"**Realizado x Focus ({ano})**")
        st.dataframe(cf.style.format({"realizado": "{:.2f}", "focus": "{:.2f}", "diferenca": "{:+.2f}"}),
                     hide_index=True, use_container_width=True)
    with dir_:
        nome = st.selectbox("Histórico", ordem, format_func=ROTULOS.get, label_visibility="collapsed")
        s = dados.sgs_longo()
        serie = s[(s["serie"] == nome) & s["valor"].notna()].sort_values("data")
        st.plotly_chart(graficos.historico(serie, ROTULOS[nome], SERIES[nome].unidade, modo),
                        use_container_width=True)


def fmt_bp(v: float) -> str:
    """Variação em bp com sinal; travessão para nulo."""
    return "—" if pd.isna(v) else f"{v:+.0f} bp"


def cartoes_mercado() -> None:
    """Cartões com os vértices de 1, 2 e 5 anos e as variações do dia, 7 e 30 dias."""
    var = dados.variacoes_curva().set_index("vertice")
    cols = st.columns(3)
    for col, v in zip(cols, ["1a", "2a", "5a"]):
        r = var.loc[v]
        col.metric(f"DI1 {v}", f"{r['taxa']:.2f}%", fmt_bp(r["d1_bp"]) + " no dia",
                   delta_color="inverse", help=f"7 dias: {fmt_bp(r['d7_bp'])} · 30 dias: {fmt_bp(r['d30_bp'])}")


def secao_curva(modo: str) -> None:
    """Movimento do dia, Selic implícita x Focus, curva x 30 dias, inclinação e prêmio histórico."""
    st.subheader("Curva de juros")
    data_ref, tabela = dados.implicita_x_focus()
    cartoes_mercado()
    mov = mercado.movimento_proxima_reuniao(tabela)
    atual = tabela.iloc[0]
    st.caption(f"Curva DI1 de {data_ref}. Taxa até a próxima reunião: {atual['implicita']:.2f}% a.a. "
               f"({atual['variacao']:+.2f} p.p. contra a meta; spread CDI-Selic). "
               f"Para {mov['reuniao']} ({mov['data_decisao']:%Y-%m-%d}) a curva precifica "
               f"{mov['variacao_pp'] * 100:+.0f} bp, equivalente a {mov['probabilidade']:.0%} de "
               f"probabilidade de {mov['sentido']} de 25 bp.")
    esq, dir_ = st.columns(2)
    with esq:
        st.markdown("**Selic implícita x Focus por reunião**")
        st.plotly_chart(graficos.implicita_vs_focus(tabela, modo), use_container_width=True)
    with dir_:
        hist = dados.di1_historico()
        hoje = hist[hist["data"] == hist["data"].max()]
        passada = dados.curva_passada(30)
        st.markdown("**Curva de hoje x 30 dias atrás**")
        st.plotly_chart(graficos.curvas_sobrepostas(hoje, passada, f"{hoje['data'].max():%Y-%m-%d}",
                                                    f"{passada['data'].max():%Y-%m-%d}", modo),
                        use_container_width=True)
    esq, dir_ = st.columns(2)
    with esq:
        st.markdown("**Prêmio curva − Focus** nas próximas reuniões (p.p., últimos 120 pregões)")
        st.plotly_chart(graficos.linhas(dados.historico_premio(120), "p.p.", modo, {"zero": 0.0}),
                        use_container_width=True)
    with dir_:
        st.markdown("**Inclinação** (bp)")
        st.plotly_chart(graficos.linhas(dados.inclinacoes().tail(250), "bp", modo, {"zero": 0.0}, casas=0),
                        use_container_width=True)
    with st.expander("Tabela: implícita, variação, Focus e prêmio por reunião"):
        mostrar = tabela[["reuniao", "data_decisao", "implicita", "variacao", "focus", "premio"]]
        st.dataframe(mostrar.style.format({"implicita": "{:.2f}", "variacao": "{:+.2f}",
                                           "focus": "{:.2f}", "premio": "{:+.2f}"}, na_rep="—")
                     .format({"data_decisao": lambda d: "" if pd.isna(d) else d.strftime("%Y-%m-%d")}),
                     hide_index=True, use_container_width=True)


def secao_expectativas(modo: str) -> None:
    """Trajetória das medianas do Focus e desancoragem do IPCA."""
    st.subheader("Expectativas (Focus)")
    f = dados.focus_anual()
    ano = int(f["data"].max().year)
    cards = [("IPCA", ano), ("IPCA", ano + 1), ("Selic", ano), ("Selic", ano + 1), ("Câmbio", ano)]
    cols = st.columns(len(cards))
    for col, (ind, ref) in zip(cols, cards):
        v = expectativas.variacao_semanal(f, ind, ref)
        col.metric(f"{ind} {ref}", f"{v['mediana']:.2f}",
                   "—" if pd.isna(v["variacao_7d"]) else f"{v['variacao_7d']:+.2f} em 7 dias",
                   delta_color="inverse" if ind in ("IPCA", "Câmbio") else "normal")
    esq, dir_ = st.columns(2)
    with esq:
        st.markdown(f"**IPCA esperado** ({ano}, {ano + 1}, {ano + 2}) e banda da meta")
        st.plotly_chart(graficos.linhas(dados.trajetoria_focus("IPCA", (ano, ano + 1, ano + 2)), "% a.a.", modo,
                                        {"meta 3,0": 3.0, "teto 4,5": 4.5}), use_container_width=True)
    with dir_:
        st.markdown(f"**Selic esperada no fim do ano** ({ano}, {ano + 1})")
        st.plotly_chart(graficos.linhas(dados.trajetoria_focus("Selic", (ano, ano + 1)), "% a.a.", modo),
                        use_container_width=True)
    esq, dir_ = st.columns(2)
    with esq:
        st.markdown(f"**Câmbio esperado no fim do ano** ({ano}, {ano + 1})")
        st.plotly_chart(graficos.linhas(dados.trajetoria_focus("Câmbio", (ano, ano + 1)), "BRL/USD", modo),
                        use_container_width=True)
    with dir_:
        st.markdown("**Desancoragem**: distância do IPCA esperado à meta de 3,0% (tolerância ±1,5 p.p.)")
        d = dados.desancoragem(ano)
        st.dataframe(d.assign(dentro_banda=d["dentro_banda"].map({True: "dentro", False: "fora"}))
                     .style.format({"mediana": "{:.2f}", "distancia": "{:+.2f}"})
                     .format({"data": lambda x: "" if pd.isna(x) else x.strftime("%Y-%m-%d")}),
                     hide_index=True, use_container_width=True)
        st.caption("Horizonte relevante do Copom costuma ser 18 meses à frente; "
                   "a distância em ano+2 é a leitura mais limpa da ancoragem.")


def secao_copom(modo: str) -> None:
    """Índice de tom por reunião, reação do DI1 e o último comunicado."""
    st.subheader("Copom")
    df = dados.tom_e_evento()
    n = st.slider("Reuniões mostradas", 8, int(df["nro_reuniao"].nunique()), 24)
    recorte = df[df["nro_reuniao"] >= sorted(df["nro_reuniao"].unique())[-n]]
    esq, dir_ = st.columns(2)
    with esq:
        st.markdown("**Índice de tom** (hawkish − dovish) / (hawkish + dovish)")
        st.plotly_chart(graficos.tom_copom(recorte, modo), use_container_width=True)
    with dir_:
        vertice = st.radio("Reação do DI1 ao comunicado", ["delta_1a_bp", "delta_2a_bp"],
                           format_func=lambda c: "1 ano" if c == "delta_1a_bp" else "2 anos", horizontal=True)
        st.plotly_chart(graficos.reacao_di1(recorte, vertice, modo), use_container_width=True)
    desc, mudanca = dados.mudanca_termos()
    if not mudanca.empty:
        st.markdown(f"**O que mudou no texto**: comunicado da {desc}")
        esq, dir_ = st.columns(2)
        with esq:
            st.caption("Termos hawkish")
            st.dataframe(mudanca[mudanca["categoria"] == "hawkish"].drop(columns="categoria"),
                         hide_index=True, use_container_width=True, height=240)
        with dir_:
            st.caption("Termos dovish")
            st.dataframe(mudanca[mudanca["categoria"] == "dovish"].drop(columns="categoria"),
                         hide_index=True, use_container_width=True, height=240)
    with st.expander("Distribuição das reações e relação com o tom"):
        esq, dir_ = st.columns(2)
        with esq:
            st.plotly_chart(graficos.histograma_reacao(df, vertice, modo), use_container_width=True)
        with dir_:
            st.plotly_chart(graficos.dispersao_tom_reacao(df, vertice, modo), use_container_width=True)
    textos = dados.textos_copom()
    ultimo = textos[textos["tipo"] == "comunicado"].sort_values("nro_reuniao").iloc[-1]
    with st.expander(f"Último comunicado: {ultimo['titulo']} ({ultimo['data_decisao']:%Y-%m-%d})"):
        termos = tom.termos_mais_frequentes(ultimo["texto"])
        st.caption("Termos hawkish: " + ", ".join(f"{t} ({c})" for t, c in termos["hawkish"])
                   + " · dovish: " + ", ".join(f"{t} ({c})" for t, c in termos["dovish"]))
        st.write(ultimo["texto"])
    with st.expander("Tabela completa"):
        cols = ["nro_reuniao", "tipo", "data_evento", "hawkish", "dovish", "indice",
                "delta_indice", "delta_1a_bp", "delta_2a_bp"]
        st.dataframe(df[cols].sort_values(["nro_reuniao", "tipo"], ascending=False),
                     hide_index=True, use_container_width=True)


def secao_nota() -> None:
    """Rascunho da nota matinal: gera dos caches, mostra, permite baixar."""
    st.subheader("Nota matinal")
    st.warning("Rascunho gerado automaticamente. Sempre revisar antes de distribuir.")
    hoje = pd.Timestamp.today().date()
    if st.button("Gerar rascunho de hoje", type="primary") or "nota" in st.session_state:
        if "nota" not in st.session_state:
            with st.spinner("Montando a nota..."):
                texto, caminho = nota.gerar(hoje)
            st.session_state["nota"] = (texto, str(caminho))
        texto, caminho = st.session_state["nota"]
        st.caption(f"Gravada em {caminho}")
        st.download_button("Baixar .md", texto, file_name=Path(caminho).name, mime="text/markdown")
        st.markdown(texto)


def cabecalho() -> None:
    """Título no topo da página."""
    st.markdown("### Painel Macro · visão de casa")
    st.caption("Dados de alta frequência, expectativas, curva de juros e comunicação do Copom.")


def main() -> None:
    """Monta a barra lateral, o cabeçalho e a seção escolhida."""
    modo = modo_tema()
    st.logo(str(ICONE_BRANCO), size="large", icon_image=str(ICONE_BRANCO))
    st.sidebar.markdown("#### Painel Macro")
    secao = st.sidebar.radio("Seção", ["Indicadores", "Curva", "Expectativas", "Copom", "Nota matinal"])
    if st.sidebar.button("Atualizar dados", help="Baixa SGS, Focus, DI1 e textos do Copom"):
        with st.spinner("Atualizando..."):
            resumo = dados.atualizar_tudo()
        st.sidebar.success("Atualizado")
        st.sidebar.dataframe(resumo, hide_index=True)
    st.sidebar.caption("Fontes públicas: BCB (SGS, Focus, Copom) e B3 via PYield. "
                       "Taxas em % a.a.; datas em ISO.")
    st.sidebar.caption(DISCLAIMER)
    cabecalho()
    {"Indicadores": lambda: secao_indicadores(modo), "Curva": lambda: secao_curva(modo),
     "Expectativas": lambda: secao_expectativas(modo), "Copom": lambda: secao_copom(modo),
     "Nota matinal": secao_nota}[secao]()
    st.divider()
    st.caption(DISCLAIMER)


main()
