"""Carregadores do painel: cache do Streamlit em cima dos caches parquet.

Nada aqui baixa dados por conta própria, exceto ``atualizar_tudo`` (botão).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import curva, expectativas, indicadores, mercado, premio
from copom import evento, fontes, termos, tom
from data import atualizar as _atualizar
from data import copom as copom_cal
from data import di1, focus, sgs

TTL = 3600  # 1 hora


@st.cache_data(ttl=TTL, show_spinner=False)
def sgs_longo() -> pd.DataFrame:
    """Séries do SGS em formato longo."""
    return sgs.carregar()


@st.cache_data(ttl=TTL, show_spinner=False)
def focus_anual() -> pd.DataFrame:
    """Expectativas anuais do Focus."""
    return focus.carregar_anual()


@st.cache_data(ttl=TTL, show_spinner=False)
def focus_selic() -> pd.DataFrame:
    """Selic esperada por reunião (Focus)."""
    return focus.carregar_selic()


@st.cache_data(ttl=TTL, show_spinner=False)
def di1_historico() -> pd.DataFrame:
    """Histórico da curva DI1."""
    return di1.carregar()


@st.cache_data(ttl=TTL, show_spinner=False)
def textos_copom() -> pd.DataFrame:
    """Comunicados e atas em cache (sem baixar)."""
    return fontes.carregar()


@st.cache_data(ttl=TTL, show_spinner=False)
def tabela_variacoes() -> pd.DataFrame:
    """Variação de cada série contra um mês antes."""
    return indicadores.tabela_variacoes(sgs_longo())


@st.cache_data(ttl=TTL, show_spinner=False)
def tabela_contra_focus() -> tuple[int, pd.DataFrame]:
    """(ano, realizado x Focus no ano corrente)."""
    s = sgs_longo()
    ano = int(s["data"].max().year)
    return ano, indicadores.contra_focus(s, focus_anual(), ano)


@st.cache_data(ttl=TTL, show_spinner=False)
def implicita_x_focus() -> tuple[str, pd.DataFrame]:
    """(data da curva, Selic implícita por reunião x Focus)."""
    ultima = di1.ultima_curva(di1_historico())
    data_ref = ultima["data"].max().date().isoformat()
    reunioes = copom_cal.proximas(copom_cal.carregar(), data_ref, n=9)
    _, selic_atual = sgs.ultimo_valor(sgs_longo(), "selic_meta")
    implic = curva.selic_implicita(ultima, reunioes, data_ref, selic_atual)
    return data_ref, curva.comparar_com_focus(implic, focus.ultima_pesquisa(focus_selic()))


@st.cache_data(ttl=TTL, show_spinner=False)
def tom_e_evento() -> pd.DataFrame:
    """Índice de tom e reação do DI1 por documento do Copom."""
    textos = textos_copom()
    taxas = evento.taxas_por_pregao(di1_historico())
    ev = evento.estudo_evento(taxas, evento.eventos_de(textos))
    return evento.juntar_tom_e_evento(tom.tabela_tom(textos), ev)


@st.cache_data(ttl=TTL, show_spinner=False)
def taxas_vertices() -> pd.DataFrame:
    """Taxas de 1, 2 e 5 anos por pregão."""
    return mercado.taxas_vertices(di1_historico())


@st.cache_data(ttl=TTL, show_spinner=False)
def variacoes_curva() -> pd.DataFrame:
    """Variação dos vértices contra ontem, 7 e 30 dias."""
    return mercado.variacoes_vertices(taxas_vertices())


@st.cache_data(ttl=TTL, show_spinner=False)
def inclinacoes() -> pd.DataFrame:
    """Inclinações 2a−1a e 5a−2a (bp) por pregão, índice data."""
    return mercado.inclinacoes(taxas_vertices()).set_index("data")


@st.cache_data(ttl=TTL, show_spinner=False)
def curva_passada(dias: int = 30) -> pd.DataFrame:
    """Curva do último pregão até ``dias`` corridos atrás."""
    hist = di1_historico()
    return mercado.curva_em(hist, hist["data"].max() - pd.Timedelta(days=dias))


@st.cache_data(ttl=TTL, show_spinner=False)
def historico_premio(pregoes: int = 120) -> pd.DataFrame:
    """Prêmio implícita−Focus por ordem de reunião, últimos ``pregoes`` pregões (largo)."""
    hist = premio.historico_premio(di1_historico(), copom_cal.carregar(), sgs_longo(), focus_selic(), pregoes)
    return premio.premio_largo(hist)


@st.cache_data(ttl=TTL, show_spinner=False)
def trajetoria_focus(indicador: str, referencias: tuple[int, ...], semanas: int = 52) -> pd.DataFrame:
    """Trajetória das medianas do Focus por ano de referência."""
    return expectativas.trajetoria(focus_anual(), indicador, list(referencias), semanas)


@st.cache_data(ttl=TTL, show_spinner=False)
def desancoragem(ano: int) -> pd.DataFrame:
    """Distância do IPCA esperado à meta para ano, ano+1 e ano+2."""
    return expectativas.tabela_desancoragem(focus_anual(), ano)


@st.cache_data(ttl=TTL, show_spinner=False)
def mudanca_termos() -> tuple[str, pd.DataFrame]:
    """(descrição do par comparado, termos que mudaram entre os dois últimos comunicados)."""
    par = termos.ultimos_dois(textos_copom())
    if par is None:
        return "", pd.DataFrame()
    atual, anterior = par
    desc = f"{atual['nro_reuniao']}ª ({atual['data_decisao']:%Y-%m-%d}) contra {anterior['nro_reuniao']}ª ({anterior['data_decisao']:%Y-%m-%d})"
    return desc, termos.diferenca_termos(atual["texto"], anterior["texto"])


def atualizar_tudo() -> pd.DataFrame:
    """Atualiza todos os caches (SGS, Focus, DI1, textos do Copom) e limpa o cache do app."""
    resumo = _atualizar.atualizar_tudo()
    fontes.atualizar()
    st.cache_data.clear()
    return resumo
