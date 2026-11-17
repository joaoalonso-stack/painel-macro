"""O que mudou no texto: termos do léxico que entraram, saíram ou mudaram de frequência
entre dois documentos do Copom.
"""

from __future__ import annotations

import pandas as pd

from copom import tom


def contagens(texto: str) -> dict[str, tuple[str, int]]:
    """Termo -> (categoria, contagem) para todos os termos do léxico presentes no texto."""
    saida = {t: ("hawkish", c) for t, c in tom.contar(texto, tom._RE_HAWK).items()}
    saida.update({t: ("dovish", c) for t, c in tom.contar(texto, tom._RE_DOVE).items()})
    return saida


def _status(antes: int, depois: int) -> str:
    if antes == 0:
        return "entrou"
    if depois == 0:
        return "saiu"
    return "subiu" if depois > antes else "desceu"


def diferenca_termos(texto_atual: str, texto_anterior: str) -> pd.DataFrame:
    """Termos cuja contagem mudou entre o documento anterior e o atual.

    Colunas: termo, categoria, antes, depois, variacao, status
    (entrou / saiu / subiu / desceu), ordenadas pela maior |variacao|.

    Caso conferido à mão: anterior "cautela e moderação", atual "cautela,
    cautela e desinflação" -> cautela subiu (1→2), moderação saiu,
    desinflação entrou.
    """
    a, d = contagens(texto_anterior), contagens(texto_atual)
    linhas = []
    for termo in sorted(set(a) | set(d)):
        cat = (d.get(termo) or a.get(termo))[0]
        antes, depois = a.get(termo, (cat, 0))[1], d.get(termo, (cat, 0))[1]
        if antes != depois:
            linhas.append({"termo": termo, "categoria": cat, "antes": antes, "depois": depois,
                           "variacao": depois - antes, "status": _status(antes, depois)})
    cols = ["termo", "categoria", "antes", "depois", "variacao", "status"]
    if not linhas:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(linhas, columns=cols)
    return (df.assign(_abs=df["variacao"].abs()).sort_values(["_abs", "termo"], ascending=[False, True])
              .drop(columns="_abs").reset_index(drop=True))


def ultimos_dois(textos: pd.DataFrame, tipo: str = "comunicado") -> tuple[pd.Series, pd.Series] | None:
    """(atual, anterior) do ``tipo`` no cache de textos, ou ``None`` se houver menos de dois."""
    t = textos[textos["tipo"] == tipo].sort_values("nro_reuniao")
    if len(t) < 2:
        return None
    return t.iloc[-1], t.iloc[-2]
