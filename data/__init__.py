"""Coleta e cache local (parquet) de dados públicos: SGS/BCB, Focus e DI1.

Ao importar o pacote, o ``truststore`` passa a usar a loja de certificados do
sistema. Sem isso, antivírus que inspecionam HTTPS (caso do Avast nesta
máquina) derrubam as chamadas do ``httpx``/``requests`` com
``CERTIFICATE_VERIFY_FAILED``.
"""

from pathlib import Path

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover - opcional
    pass

CACHE_DIR = Path(__file__).resolve().parent / "cache"
