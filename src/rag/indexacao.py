"""Orquestra a fase offline: PDF -> trechos -> vetores -> banco."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from . import banco, embeddings
from .chunking import dividir, texto_para_embedding
from .config import obter_config
from .extracao import extrair, listar_pdfs


def _hash(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:32]


def _manifesto(pasta: Path) -> dict[str, dict[str, Any]]:
    """Metadados opcionais gerados junto com os PDFs de exemplo.

    Em uma base real esses campos viriam do sistema de gestao documental. Quando
    o manifesto nao existe, o titulo e lido do proprio PDF.
    """
    caminho = pasta / "manifesto.json"
    if not caminho.exists():
        return {}
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return {item["arquivo"]: item for item in dados}


def indexar_arquivo(caminho: Path, meta_extra: dict[str, Any] | None = None) -> dict[str, Any]:
    config = obter_config()
    documento = extrair(caminho)
    trechos = dividir(
        documento,
        alvo_chars=config.chunk_alvo_chars,
        overlap_chars=config.chunk_overlap_chars,
    )
    extra = meta_extra or {}
    titulo = extra.get("titulo") or documento.titulo

    vetores = embeddings.vetorizar_documentos(
        [texto_para_embedding(titulo, t) for t in trechos]
    )

    banco.gravar_documento(
        meta={
            "arquivo": documento.arquivo,
            "titulo": titulo,
            "codigo": extra.get("codigo"),
            "equipamento": extra.get("equipamento"),
            "revisao": extra.get("revisao"),
            "paginas": documento.total_paginas,
            "hash_arquivo": _hash(caminho),
        },
        trechos=[
            {
                "ordem": t.ordem,
                "texto": t.texto,
                "secao": t.secao,
                "pagina_inicial": t.pagina_inicial,
                "pagina_final": t.pagina_final,
                "embedding": vetor,
            }
            for t, vetor in zip(trechos, vetores)
        ],
    )
    return {
        "arquivo": documento.arquivo,
        "titulo": titulo,
        "paginas": documento.total_paginas,
        "trechos": len(trechos),
    }


def indexar_pasta(
    pasta: Path | None = None,
    recriar: bool = False,
    progresso: Callable[[str], None] = print,
) -> list[dict[str, Any]]:
    config = obter_config()
    pasta = pasta or config.pasta_pdfs
    arquivos = listar_pdfs(pasta)
    if not arquivos:
        raise FileNotFoundError(
            f"nenhum PDF em {pasta}. Rode 'python scripts/gerar_pdfs.py' para criar a base de exemplo."
        )

    banco.criar_esquema()
    if recriar:
        banco.limpar_tudo()

    manifesto = _manifesto(pasta)
    resultados: list[dict[str, Any]] = []
    for caminho in arquivos:
        if not recriar and banco.hash_indexado(caminho.name) == _hash(caminho):
            progresso(f"  inalterado, mantido: {caminho.name}")
            continue
        progresso(f"  indexando: {caminho.name}")
        resultados.append(indexar_arquivo(caminho, manifesto.get(caminho.name)))
    return resultados
