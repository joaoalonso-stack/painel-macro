"""Testes da montagem da nota matinal (sem rede)."""

from datetime import date

import pandas as pd

from reports import nota


def _variacoes():
    return pd.DataFrame({
        "serie": ["ipca", "cambio"], "data": pd.to_datetime(["2026-10-01", "2026-11-12"]),
        "valor": [0.14, 5.614], "data_anterior": pd.to_datetime(["2026-09-01", "2026-10-09"]),
        "valor_anterior": [0.82, 4.989], "variacao": [-0.68, 12.529], "tipo": ["pp", "pct"],
    })


def _implicita():
    return pd.DataFrame({"reuniao": ["atual", "R8/2026", "R1/2027"],
                         "implicita": [13.655, 13.684, 13.818], "variacao": [-0.095, 0.029, 0.134],
                         "focus": [None, 13.75, 13.75], "premio": [None, -0.066, 0.068]})


def test_fmt_usa_virgula_e_sinal():
    assert nota.fmt(13.684) == "13,68"
    assert nota.fmt(-0.68, sinal=True) == "-0,68"
    assert nota.fmt(0.029, sinal=True) == "+0,03"
    assert nota.fmt(None) == "—"


def test_bloco_indicadores_conferido_a_mao():
    b = nota.bloco_indicadores(_variacoes())
    assert "**IPCA, variação mensal**: 0,14 % a.m. (2026-10-01); -0,68 p.p. contra um mês antes." in b
    assert "PTAX venda, BRL por USD**: 5,61 BRL/USD (2026-11-12); +12,53 % contra um mês antes." in b


def test_bloco_curva_resume_premio():
    b = nota.bloco_curva("2026-11-11", _implicita())
    # 13.655 em binário fica um pouco abaixo de 13,655 e arredonda para 13,65.
    assert "Taxa até a próxima reunião: 13,65% a.a. (-0,10 p.p." in b
    assert "| R8/2026 | 13,68 | 13,75 | -0,07 |" in b
    # prêmio médio = (-0.066 + 0.068) / 2 = +0.001 -> "acima"
    assert "0,00 p.p. acima do Focus nas próximas 2 reuniões" in b


def test_bloco_copom_sem_dado_e_com_dado():
    assert "Sem comunicado" in nota.bloco_copom(None)
    b = nota.bloco_copom({"nro_reuniao": 282, "data": pd.Timestamp("2026-11-04"), "indice": 0.436,
                          "delta_indice": 0.064, "delta_1a_bp": -11.121, "delta_2a_bp": -11.183})
    assert "282ª reunião): índice de tom 0,44 (hawkish), +0,06 contra o comunicado anterior." in b
    assert "-11,1 bp em 1 ano, -11,2 bp em 2 anos" in b


def test_montar_e_salvar(tmp_path):
    cf = pd.DataFrame({"indicador": ["Selic"], "realizado": [13.75], "focus": [13.75],
                       "diferenca": [0.0], "nota": ["meta vigente x fim de ano"]})
    texto = nota.montar_nota(date(2026, 11, 12), _variacoes(), 2026, cf, "2026-11-11", _implicita(), None)
    assert texto.startswith("# Nota matinal, 2026-11-12")
    assert texto.count("Revisar antes de distribuir") == 2  # cabeçalho e rodapé
    assert "| Selic | 13,75 | 13,75 | +0,00 | meta vigente x fim de ano |" in texto
    caminho = nota.salvar(texto, date(2026, 11, 12), pasta=tmp_path)
    assert caminho.name == "nota_2026-11-12.md" and caminho.read_text(encoding="utf-8") == texto


def test_bloco_mercado_conferido_a_mao():
    var = pd.DataFrame({"vertice": ["1a"], "taxa": [13.5], "d1_bp": [10.0], "d7_bp": [30.0], "d30_bp": [None]})
    mov = {"reuniao": "R8/2026", "variacao_pp": 0.029, "probabilidade": 0.116, "sentido": "alta"}
    b = nota.bloco_mercado(var, mov)
    assert "| 1a | 13,50% | +10 bp | +30 bp | — bp |" in b
    assert "Para R8/2026 a curva precifica +3 bp, equivalente a 12% de probabilidade de alta de 25 bp." in b
    assert "Para" not in nota.bloco_mercado(var, None)


def test_ultimo_comunicado():
    te = pd.DataFrame({"nro_reuniao": [281, 282, 282], "tipo": ["comunicado", "ata", "comunicado"],
                       "data_evento": pd.to_datetime(["2026-09-16", "2026-11-10", "2026-11-04"]),
                       "indice": [0.37, 0.27, 0.44], "delta_indice": [0.04, 0.09, 0.06],
                       "delta_1a_bp": [-6.3, -1.9, -11.1], "delta_2a_bp": [-5.8, 2.7, -11.2]})
    u = nota.ultimo_comunicado(te)
    assert u["nro_reuniao"] == 282 and u["indice"] == 0.44
    assert nota.ultimo_comunicado(te[te["tipo"] == "ata"]) is None
