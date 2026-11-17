"""Comunicados e atas do Copom pela API pública do site do BCB.

Endpoints (JSON):
  copom/comunicados?quantidade=N            lista: nro_reuniao, dataReferencia, titulo
  copom/comunicados_detalhes?nro_reuniao=N  textoComunicado (HTML)
  copom/atas?quantidade=N                   lista: nroReuniao, dataReferencia, dataPublicacao, titulo
  copom/atas_detalhes?nro_reuniao=N         textoAta (HTML), urlPdfAta

Cache ``copom_textos.parquet``: nro_reuniao, tipo ("comunicado" | "ata"),
data_decisao, data_publicacao, titulo, texto (texto limpo, sem HTML).
"""

from __future__ import annotations

import html
import io
import logging
import re
import time
from html.parser import HTMLParser

import pandas as pd
import requests
from pypdf import PdfReader

from data import cache  # importa o pacote data: ativa o truststore

log = logging.getLogger(__name__)

BASE = "https://www.bcb.gov.br/api/servico/sitebcb/copom"
NOME_CACHE = "copom_textos"
TENTATIVAS = 3
TIMEOUT = 30
COLUNAS = ["nro_reuniao", "tipo", "data_decisao", "data_publicacao", "titulo", "texto"]


class _Extrator(HTMLParser):
    """Acumula só o texto dos nós, com quebra de linha em blocos."""

    BLOCOS = {"p", "div", "h1", "h2", "h3", "h4", "li", "br", "tr"}

    def __init__(self) -> None:
        super().__init__()
        self.partes: list[str] = []

    def handle_starttag(self, tag, attrs):  # noqa: D102
        if tag in self.BLOCOS:
            self.partes.append("\n")

    def handle_data(self, data):  # noqa: D102
        self.partes.append(data)


def limpar_html(texto_html: str) -> str:
    """Remove tags e entidades, normaliza espaços e quebras de linha.

    Caso conferido à mão: ``"<p>Olá&nbsp;<em>mundo</em></p><p>x</p>"`` vira ``"Olá mundo\\nx"``.
    """
    p = _Extrator()
    p.feed(html.unescape(texto_html or ""))
    texto = "".join(p.partes).replace("​", "").replace("\xa0", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r" *\n+ *", "\n", texto)
    return texto.strip()


def _get_json(rota: str, **params) -> list[dict]:
    """GET em ``BASE/rota`` com tentativas; devolve a lista ``conteudo``."""
    for i in range(1, TENTATIVAS + 1):
        try:
            r = requests.get(f"{BASE}/{rota}", params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()["conteudo"]
        except (requests.RequestException, ValueError, KeyError) as exc:
            log.warning("%s %s tentativa %d/%d: %s", rota, params, i, TENTATIVAS, exc)
            if i == TENTATIVAS:
                raise
            time.sleep(2 * i)
    raise RuntimeError("inalcançável")  # pragma: no cover


def listar_comunicados(quantidade: int = 500) -> pd.DataFrame:
    """Lista de comunicados: nro_reuniao, data_decisao, titulo."""
    df = pd.DataFrame(_get_json("comunicados", quantidade=quantidade))
    return (df.rename(columns={"dataReferencia": "data_decisao"})
              .assign(data_decisao=lambda d: pd.to_datetime(d["data_decisao"]))
              [["nro_reuniao", "data_decisao", "titulo"]])


def listar_atas(quantidade: int = 500) -> pd.DataFrame:
    """Lista de atas: nro_reuniao, data_decisao, data_publicacao, titulo."""
    df = pd.DataFrame(_get_json("atas", quantidade=quantidade))
    df = df.rename(columns={"nroReuniao": "nro_reuniao", "dataReferencia": "data_decisao",
                            "dataPublicacao": "data_publicacao"})
    df["data_decisao"] = pd.to_datetime(df["data_decisao"])
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"])
    return df[["nro_reuniao", "data_decisao", "data_publicacao", "titulo"]]


def baixar_comunicado(nro: int) -> dict:
    """Texto limpo do comunicado da reunião ``nro``."""
    item = _get_json("comunicados_detalhes", nro_reuniao=nro)[0]
    return {"nro_reuniao": int(nro), "tipo": "comunicado",
            "data_decisao": pd.Timestamp(item["dataReferencia"]),
            "data_publicacao": pd.Timestamp(item["dataReferencia"]),
            "titulo": item.get("titulo", ""), "texto": limpar_html(item.get("textoComunicado", ""))}


def texto_de_pdf(conteudo: bytes) -> str:
    """Extrai o texto de um PDF (bytes) e normaliza espaços e quebras de linha."""
    leitor = PdfReader(io.BytesIO(conteudo))
    bruto = "\n".join(p.extract_text() or "" for p in leitor.pages)
    bruto = re.sub(r"[ \t]+", " ", bruto)
    return re.sub(r" *\n+ *", "\n", bruto).strip()


def _baixar_pdf(url: str) -> bytes:
    """Baixa um PDF com tentativas e devolve os bytes."""
    for i in range(1, TENTATIVAS + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT * 2)
            r.raise_for_status()
            return r.content
        except requests.RequestException as exc:
            log.warning("pdf %s tentativa %d/%d: %s", url, i, TENTATIVAS, exc)
            if i == TENTATIVAS:
                raise
            time.sleep(2 * i)
    raise RuntimeError("inalcançável")  # pragma: no cover


def baixar_ata(nro: int) -> dict:
    """Texto limpo da ata da reunião ``nro``: HTML da API ou, se nulo, o PDF."""
    item = _get_json("atas_detalhes", nro_reuniao=nro)[0]
    if item.get("textoAta"):
        texto = limpar_html(item["textoAta"])
    elif item.get("urlPdfAta"):
        texto = texto_de_pdf(_baixar_pdf(item["urlPdfAta"]))
    else:
        texto = ""
    return {"nro_reuniao": int(nro), "tipo": "ata",
            "data_decisao": pd.Timestamp(item["dataReferencia"]),
            "data_publicacao": pd.Timestamp(item["dataPublicacao"]),
            "titulo": item.get("titulo", ""), "texto": texto}


def vazio() -> pd.DataFrame:
    """DataFrame sem linhas com as colunas padrão."""
    return pd.DataFrame(columns=COLUNAS)


def faltantes(antigo: pd.DataFrame, lista: pd.DataFrame, tipo: str, nro_minimo: int) -> list[int]:
    """Números de reunião em ``lista`` (>= ``nro_minimo``) ainda sem texto de ``tipo`` no cache."""
    ja_tem = set(antigo.loc[antigo["tipo"] == tipo, "nro_reuniao"].astype(int))
    nros = sorted(int(n) for n in lista["nro_reuniao"] if n >= nro_minimo)
    return [n for n in nros if n not in ja_tem]


def atualizar(nro_minimo: int = 200) -> pd.DataFrame:
    """Baixa comunicados e atas que faltam no cache (reuniões >= ``nro_minimo``)."""
    antigo = cache.ler(NOME_CACHE) if cache.existe(NOME_CACHE) else vazio()
    novos = []
    for tipo, listar, baixar in (("comunicado", listar_comunicados, baixar_comunicado),
                                 ("ata", listar_atas, baixar_ata)):
        pendentes = faltantes(antigo, listar(), tipo, nro_minimo)
        log.info("copom %s: %d textos a baixar", tipo, len(pendentes))
        for nro in pendentes:
            novos.append(baixar(nro))
    df = pd.concat([antigo, pd.DataFrame(novos, columns=COLUNAS)], ignore_index=True)
    df = (df.drop_duplicates(["nro_reuniao", "tipo"], keep="last")
            .sort_values(["nro_reuniao", "tipo"]).reset_index(drop=True))
    cache.gravar(NOME_CACHE, df)
    return df


def carregar() -> pd.DataFrame:
    """Lê o cache de textos; baixa se ainda não existir."""
    return cache.ler(NOME_CACHE) if cache.existe(NOME_CACHE) else atualizar()
