"""Testes da diferença de termos entre documentos (sem rede)."""

import pandas as pd

from copom import termos


def test_diferenca_termos_conferida_a_mao():
    df = termos.diferenca_termos("cautela, cautela e desinflação", "cautela e moderação").set_index("termo")
    assert df.loc["cautela", ["antes", "depois", "status"]].tolist() == [1, 2, "subiu"]
    assert df.loc["moderação", ["antes", "depois", "status"]].tolist() == [1, 0, "saiu"]
    assert df.loc["desinflação", ["antes", "depois", "status", "categoria"]].tolist() == [0, 1, "entrou", "dovish"]
    assert df["variacao"].abs().tolist() == sorted(df["variacao"].abs().tolist(), reverse=True)


def test_diferenca_sem_mudanca_e_vazia():
    df = termos.diferenca_termos("cautela", "cautela")
    assert df.empty and "status" in df.columns


def test_ultimos_dois():
    t = pd.DataFrame({"nro_reuniao": [280, 282, 281], "tipo": ["comunicado"] * 3, "texto": ["a", "c", "b"]})
    atual, anterior = termos.ultimos_dois(t)
    assert (atual["nro_reuniao"], anterior["nro_reuniao"]) == (282, 281)
    assert termos.ultimos_dois(t.head(1)) is None
