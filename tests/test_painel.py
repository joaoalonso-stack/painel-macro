"""Executa o painel com o AppTest do Streamlit, seção por seção, sem navegador.

Usa os caches locais (sem rede); se não existirem, os testes são pulados.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from data import CACHE_DIR

RAIZ = Path(__file__).resolve().parents[1]
CACHES = ["sgs", "focus_anual", "focus_selic", "di1", "copom_textos", "copom_calendario"]
sem_cache = not all((CACHE_DIR / f"{n}.parquet").is_file() for n in CACHES)


@pytest.mark.skipif(sem_cache, reason="caches locais ausentes; rode python -m data.atualizar e copom.resumo")
@pytest.mark.parametrize("secao", ["Indicadores", "Curva", "Expectativas", "Copom", "Nota matinal"])
def test_secao_renderiza_sem_excecao(secao):
    at = AppTest.from_file(str(RAIZ / "app" / "painel.py"), default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value(secao).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.subheader[0].value.lower().startswith(secao.split()[0].lower())
