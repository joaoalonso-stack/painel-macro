"""Testes da limpeza de texto e da lógica de pendências (sem rede)."""

import pandas as pd

from copom import fontes


def test_limpar_html_remove_tags_e_entidades():
    # Conferido à mão: parágrafos viram linhas, &nbsp; vira espaço, <em> some.
    assert fontes.limpar_html("<p>Olá&nbsp;<em>mundo</em></p><p>x</p>") == "Olá mundo\nx"


def test_limpar_html_normaliza_espacos():
    html = '<div class="x"><p style="a">  A   B </p>\n\n<p>C</p></div>'
    assert fontes.limpar_html(html) == "A B\nC"


def test_limpar_html_vazio():
    assert fontes.limpar_html("") == ""
    assert fontes.limpar_html(None) == ""


def test_faltantes_ignora_ja_baixados_e_abaixo_do_minimo():
    antigo = pd.DataFrame({"nro_reuniao": [281, 282], "tipo": ["ata", "comunicado"]})
    lista = pd.DataFrame({"nro_reuniao": [282, 281, 280, 199]})
    assert fontes.faltantes(antigo, lista, "ata", 200) == [280, 282]
    assert fontes.faltantes(antigo, lista, "comunicado", 200) == [280, 281]
