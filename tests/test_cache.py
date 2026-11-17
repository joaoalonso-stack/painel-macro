"""Testes do cache parquet (sem rede)."""

import pandas as pd

from data import cache


def _df():
    return pd.DataFrame({"data": pd.to_datetime(["2026-01-01", "2026-02-01"]),
                         "serie": ["x", "x"], "valor": [1.5, 2.5]})


def test_gravar_e_ler_round_trip(tmp_path):
    cache.gravar("teste", _df(), pasta=tmp_path)
    lido = cache.ler("teste", pasta=tmp_path)
    pd.testing.assert_frame_equal(lido, _df())
    assert cache.existe("teste", pasta=tmp_path)
    assert cache.idade_horas("teste", pasta=tmp_path) < 1


def test_obter_usa_cache_quando_recente(tmp_path):
    chamadas = []

    def buscar():
        chamadas.append(1)
        return _df()

    cache.obter("t", buscar, ttl_horas=12, pasta=tmp_path)
    cache.obter("t", buscar, ttl_horas=12, pasta=tmp_path)
    assert len(chamadas) == 1  # segunda chamada veio do cache


def test_obter_forcar_rebaixa(tmp_path):
    chamadas = []

    def buscar():
        chamadas.append(1)
        return _df()

    cache.obter("t", buscar, pasta=tmp_path)
    cache.obter("t", buscar, forcar=True, pasta=tmp_path)
    assert len(chamadas) == 2


def test_idade_none_sem_arquivo(tmp_path):
    assert cache.idade_horas("nada", pasta=tmp_path) is None
    assert not cache.existe("nada", pasta=tmp_path)
