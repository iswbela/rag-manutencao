"""Etapa 3: texto -> vetor.

O modelo roda localmente na CPU. A escolha e deliberada: mantem o custo por
requisicao em zero, nao envia documento interno para fora e torna a reindexacao
completa barata o suficiente para ser feita a cada mudanca de estrategia de
chunking - que e exatamente o que mais se ajusta durante o desenvolvimento.

O modelo padrao e multilingue e trabalha bem com perguntas em portugues. Modelos
da familia e5 esperam prefixos diferentes para pergunta e documento; isso e
tratado aqui para nao vazar detalhe de modelo para o resto do codigo.
"""
from __future__ import annotations

from functools import lru_cache

from .config import obter_config


@lru_cache
def _modelo():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(obter_config().embedding_model)


def _usa_prefixo() -> bool:
    return "e5" in obter_config().embedding_model.lower()


def vetorizar_documentos(textos: list[str]) -> list[list[float]]:
    entradas = [f"passage: {t}" for t in textos] if _usa_prefixo() else textos
    vetores = _modelo().encode(
        entradas, normalize_embeddings=True, batch_size=16, show_progress_bar=False
    )
    return [v.tolist() for v in vetores]


def vetorizar_pergunta(texto: str) -> list[float]:
    entrada = f"query: {texto}" if _usa_prefixo() else texto
    vetor = _modelo().encode([entrada], normalize_embeddings=True, show_progress_bar=False)[0]
    return vetor.tolist()


def dimensao() -> int:
    return int(_modelo().get_sentence_embedding_dimension())
