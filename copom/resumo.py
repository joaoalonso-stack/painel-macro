"""Imprime a tabela por reunião: índice de tom e reação do DI1.

Uso: ``python -m copom.resumo`` (baixa os textos que faltarem; DI1 vem do cache).
"""

from __future__ import annotations

import logging

import pandas as pd

from copom import evento, fontes, tom
from data import di1


def tabela_completa(nro_minimo: int = 200) -> pd.DataFrame:
    """Índice de tom e variação do DI1 (1 e 2 anos) por documento."""
    textos = fontes.atualizar(nro_minimo)
    taxas = evento.taxas_por_pregao(di1.carregar())
    ev = evento.estudo_evento(taxas, evento.eventos_de(textos))
    return evento.juntar_tom_e_evento(tom.tabela_tom(textos), ev)


def main() -> None:
    """Mostra as últimas 16 linhas e as correlações tom x DI1."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    pd.set_option("display.width", 200)
    df = tabela_completa()
    cols = ["nro_reuniao", "tipo", "data_evento", "hawkish", "dovish", "indice",
            "delta_indice", "delta_1a_bp", "delta_2a_bp"]
    ultimos = df[cols].tail(16)
    numericas = ultimos.select_dtypes("number").columns
    print("\n== Tom e reação do DI1 (últimos documentos) ==")
    print(ultimos.assign(**{c: ultimos[c].round(3) for c in numericas}).to_string(index=False))
    print("\n== Correlação do índice (nível e variação) com a variação do DI1 ==")
    print(pd.DataFrame([evento.correlacao(df, "comunicado"), evento.correlacao(df, "ata")])
          .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
