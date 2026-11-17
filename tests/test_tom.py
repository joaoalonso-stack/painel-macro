"""Testes do índice hawkish/dovish (sem rede)."""

import pandas as pd
import pytest

from copom import tom

FRASE = ("O Copom reforça a cautela e vê pressões inflacionárias persistentes, "
         "apesar da moderação da atividade.")


def test_indice_caso_conferido_a_mao():
    r = tom.indice(FRASE)
    # hawkish: cautela, pressões inflacionárias, persistentes = 3; dovish: moderação = 1
    assert (r["hawkish"], r["dovish"]) == (3, 1)
    assert r["indice"] == pytest.approx(0.5)
    assert r["palavras"] == 15


def test_indice_sem_termos_e_zero():
    r = tom.indice("Reunião realizada em Brasília.")
    assert r == {"hawkish": 0, "dovish": 0, "palavras": 4, "indice": 0.0}


def test_termo_composto_nao_conta_duas_vezes():
    # "riscos de baixa" é um termo; "baixa" sozinha não está no léxico.
    assert tom.indice("Os riscos de baixa predominam.")["dovish"] == 1


def test_limite_de_palavra():
    # "altamente" não deve casar com "alta"/"altista".
    assert tom.indice("Cenário altamente incerto.")["hawkish"] == 0


def test_termos_mais_frequentes():
    t = tom.termos_mais_frequentes(FRASE + " Cautela, cautela.")
    assert t["hawkish"][0] == ("cautela", 3)


def test_tabela_tom():
    textos = pd.DataFrame({
        "nro_reuniao": [282, 282], "tipo": ["comunicado", "ata"],
        "data_decisao": pd.to_datetime(["2026-11-04"] * 2),
        "data_publicacao": pd.to_datetime(["2026-11-04", "2026-11-10"]),
        "texto": [FRASE, "Desinflação e convergência."],
    })
    t = tom.tabela_tom(textos).set_index("tipo")
    assert t.loc["comunicado", "indice"] == pytest.approx(0.5)
    assert t.loc["ata", "indice"] == pytest.approx(-1.0)
