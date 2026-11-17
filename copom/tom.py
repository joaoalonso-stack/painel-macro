"""Índice hawkish/dovish por documento, com léxico em português.

Método simples e transparente: conta ocorrências de termos de cada lista no
texto (minúsculas, com acentos) e calcula

    indice = (hawkish − dovish) / (hawkish + dovish)   em [−1, 1]

0 quando nenhum termo aparece. É um indicador de tom, não de decisão:
serve para comparar reuniões entre si, não para ler um documento isolado.
"""

from __future__ import annotations

import re
from collections import Counter

import pandas as pd

HAWKISH = [
    "cautela", "cauteloso", "cautelosa", "vigilante", "vigilância",
    "pressões inflacionárias", "pressão inflacionária",
    "desancoragem", "desancoradas", "desancorada", "distanciaram-se", "distanciou-se",
    "acima da meta", "acima do limite superior",
    "assimetria altista", "riscos de alta", "risco de alta", "altista", "altistas",
    "aceleraram", "acelerou", "aceleração",
    "elevação", "elevar", "elevou", "elevou-se", "elevado", "elevados", "elevada", "elevadas",
    "aperto", "contracionista", "restritiva", "restritivo", "restritivas",
    "persistência", "persistente", "persistentes", "persistentemente",
    "resiliente", "resiliência", "aquecido", "aquecida",
    "hiato do produto positivo", "interromper o ciclo", "interrupção do ciclo",
    "período prolongado", "período mais prolongado", "tempo prolongado",
    "deterioração", "piora", "depreciação", "depreciada", "depreciado",
    "segunda ordem", "incerteza", "adverso",
]

DOVISH = [
    "desinflação", "desinflacionário", "desinflacionária",
    "arrefecimento", "arrefecer", "arrefeceu",
    "ancoradas", "ancorada", "ancoragem", "reancoragem",
    "redução", "reduzir", "reduziu", "corte", "cortes",
    "flexibilização", "flexibilizar", "afrouxamento",
    "desaceleração", "desacelerou", "desaquecimento", "moderação",
    "riscos de baixa", "risco de baixa", "baixista", "baixistas", "assimetria baixista",
    "convergência", "convergindo", "convergir", "abaixo da meta",
    "hiato do produto negativo", "ociosidade", "estímulo", "expansionista", "acomodação",
    "melhora", "apreciação", "apreciada", "apreciado", "recuo", "recuou", "recuaram",
]


def _regex(termos: list[str]) -> re.Pattern:
    """Expressão que casa qualquer termo inteiro (limites de palavra)."""
    escapados = sorted((re.escape(t) for t in termos), key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(escapados) + r")(?!\w)", re.IGNORECASE)


_RE_HAWK = _regex(HAWKISH)
_RE_DOVE = _regex(DOVISH)


def contar(texto: str, padrao: re.Pattern) -> Counter:
    """Contagem de cada termo do ``padrao`` no ``texto``."""
    return Counter(m.group(1).lower() for m in padrao.finditer(texto or ""))


def n_palavras(texto: str) -> int:
    """Número de palavras (sequências de letras/dígitos)."""
    return len(re.findall(r"\w+", texto or ""))


def indice(texto: str) -> dict:
    """Contagens e índice de tom de um texto.

    Caso conferido à mão: "O Copom reforça a cautela e vê pressões inflacionárias
    persistentes, apesar da moderação da atividade." tem 3 termos hawkish
    (cautela, pressões inflacionárias, persistentes) e 1 dovish (moderação):
    índice = (3 − 1) / 4 = 0.5.
    """
    h = sum(contar(texto, _RE_HAWK).values())
    d = sum(contar(texto, _RE_DOVE).values())
    total = h + d
    return {"hawkish": h, "dovish": d, "palavras": n_palavras(texto),
            "indice": (h - d) / total if total else 0.0}


def termos_mais_frequentes(texto: str, n: int = 5) -> dict:
    """Os ``n`` termos hawkish e dovish mais frequentes, para explicar o índice."""
    return {"hawkish": contar(texto, _RE_HAWK).most_common(n),
            "dovish": contar(texto, _RE_DOVE).most_common(n)}


def tabela_tom(textos: pd.DataFrame) -> pd.DataFrame:
    """Índice por documento a partir do cache de textos (``copom.fontes``)."""
    linhas = []
    for _, r in textos.iterrows():
        linhas.append({"nro_reuniao": int(r["nro_reuniao"]), "tipo": r["tipo"],
                       "data_decisao": r["data_decisao"], "data_publicacao": r["data_publicacao"],
                       **indice(r["texto"])})
    return pd.DataFrame(linhas).sort_values(["nro_reuniao", "tipo"]).reset_index(drop=True)
