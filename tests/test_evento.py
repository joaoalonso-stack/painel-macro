"""Testes do estudo de evento (sem rede)."""

import pandas as pd
import pytest

from copom import evento


def _hist():
    """Três pregões com curvas flat: 13.00, 13.25 e 13.10 % a.a."""
    linhas = []
    for data, taxa in [("2026-11-03", 13.0), ("2026-11-04", 13.0), ("2026-11-05", 13.25),
                       ("2026-11-09", 13.25), ("2026-11-10", 13.10)]:
        for du in (126, 252, 378, 504, 630):
            linhas.append({"data": pd.Timestamp(data), "dias_uteis": du, "taxa_ajuste": taxa})
    return pd.DataFrame(linhas)


def test_taxas_por_pregao_interpola_1a_e_2a():
    t = evento.taxas_por_pregao(_hist())
    assert t["data"].tolist()[0] == pd.Timestamp("2026-11-03")
    assert t.loc[2, "taxa_1a"] == pytest.approx(13.25)
    assert t.loc[2, "taxa_2a"] == pytest.approx(13.25)


def test_janela_comunicado_e_ata():
    pregoes = evento.taxas_por_pregao(_hist())["data"]
    # Comunicado em 11-04 (após o fechamento): antes = 11-04, depois = 11-05.
    assert evento.janela(pregoes, "2026-11-04", True) == (pd.Timestamp("2026-11-04"), pd.Timestamp("2026-11-05"))
    # Ata em 11-10 (antes da abertura): antes = 11-09, depois = 11-10.
    assert evento.janela(pregoes, "2026-11-10", False) == (pd.Timestamp("2026-11-09"), pd.Timestamp("2026-11-10"))
    # Ata num dia sem pregão (sábado 11-07): antes = 11-05, depois = 11-09.
    assert evento.janela(pregoes, "2026-11-07", False) == (pd.Timestamp("2026-11-05"), pd.Timestamp("2026-11-09"))


def test_estudo_evento_caso_conferido_a_mao():
    taxas = evento.taxas_por_pregao(_hist())
    eventos = pd.DataFrame({"nro_reuniao": [282, 282], "tipo": ["comunicado", "ata"],
                            "data_evento": pd.to_datetime(["2026-11-04", "2026-11-10"]),
                            "apos_fechamento": [True, False]})
    df = evento.estudo_evento(taxas, eventos).set_index("tipo")
    # 13.00 -> 13.25 = +25 bp; 13.25 -> 13.10 = -15 bp.
    assert df.loc["comunicado", "delta_1a_bp"] == pytest.approx(25.0)
    assert df.loc["comunicado", "delta_2a_bp"] == pytest.approx(25.0)
    assert df.loc["ata", "delta_1a_bp"] == pytest.approx(-15.0)


def test_estudo_evento_sem_pregao_depois_da_nan():
    taxas = evento.taxas_por_pregao(_hist())
    eventos = pd.DataFrame({"nro_reuniao": [283], "tipo": ["comunicado"],
                            "data_evento": pd.to_datetime(["2026-11-10"]), "apos_fechamento": [True]})
    df = evento.estudo_evento(taxas, eventos)
    assert pd.isna(df.loc[0, "delta_1a_bp"]) and df.loc[0, "pregao_depois"] is None


def test_eventos_de_textos():
    textos = pd.DataFrame({"nro_reuniao": [282, 282], "tipo": ["comunicado", "ata"],
                           "data_decisao": pd.to_datetime(["2026-11-04"] * 2),
                           "data_publicacao": pd.to_datetime(["2026-11-04", "2026-11-10"])})
    ev = evento.eventos_de(textos).set_index("tipo")
    assert ev.loc["comunicado", "data_evento"] == pd.Timestamp("2026-11-04")
    assert ev.loc["ata", "data_evento"] == pd.Timestamp("2026-11-10")
    assert bool(ev.loc["comunicado", "apos_fechamento"]) and not bool(ev.loc["ata", "apos_fechamento"])


def test_correlacao_com_poucos_dados_e_nan():
    df = pd.DataFrame({"tipo": ["ata"], "indice": [0.1], "delta_1a_bp": [1.0], "delta_2a_bp": [1.0]})
    r = evento.correlacao(df, "ata")
    assert r["n"] == 1 and pd.isna(r["corr_nivel_1a"]) and pd.isna(r["corr_variacao_1a"])


def test_variacao_indice_por_tipo():
    tom = pd.DataFrame({"nro_reuniao": [281, 282, 281, 282],
                        "tipo": ["comunicado", "comunicado", "ata", "ata"],
                        "indice": [0.2, 0.5, -0.1, 0.1]})
    v = evento.variacao_indice(tom)
    # Conferido à mão: comunicados 0.2 -> 0.5 = +0.3; atas -0.1 -> 0.1 = +0.2.
    assert pd.isna(v[0]) and v[1] == pytest.approx(0.3)
    assert pd.isna(v[2]) and v[3] == pytest.approx(0.2)


def test_juntar_tom_e_evento_inclui_delta_indice():
    tom = pd.DataFrame({"nro_reuniao": [281, 282], "tipo": ["comunicado"] * 2, "indice": [0.2, 0.5]})
    ev = pd.DataFrame({"nro_reuniao": [282], "tipo": ["comunicado"],
                       "data_evento": pd.to_datetime(["2026-11-04"]),
                       "pregao_antes": pd.to_datetime(["2026-11-04"]),
                       "pregao_depois": pd.to_datetime(["2026-11-05"]),
                       "delta_1a_bp": [-11.1], "delta_2a_bp": [-11.2]})
    df = evento.juntar_tom_e_evento(tom, ev)
    assert df["delta_indice"].round(3).tolist()[1] == 0.3
    assert pd.isna(df.loc[0, "delta_1a_bp"]) and df.loc[1, "delta_2a_bp"] == -11.2
