"""Backends de armazenamento e busca.

O projeto foi desenhado sobre Postgres + pgvector, que continua sendo o caminho
de producao: um unico servico guarda vetor, texto e metadado, e faz as duas
buscas com indice (HNSW e GIN). Mas exigir Docker para rodar o pipeline trava a
parte do projeto que mais muda - chunking, embeddings, fusao de rankings - atras
de uma infraestrutura que nao tem nada a ver com ela.

Por isso a camada de persistencia e trocavel. O backend `sqlite` usa so a
biblioteca padrao (FTS5 para a busca textual, cosseno vetorizado em numpy para a
busca semantica) e roda sem instalar nada. O `postgres` usa o mesmo SQL de
antes. Os dois expoem exatamente as mesmas funcoes, entao `indexacao.py`,
`busca.py` e `api.py` nao sabem qual esta ativo.

Onde o SQLite nao serve: a busca semantica dele e forca bruta - carrega todos os
vetores e calcula o produto interno. Isso e instantaneo ate a casa das dezenas
de milhares de trechos e vira problema depois. Com base grande, troque
BACKEND=postgres e nada mais muda.
"""
from __future__ import annotations

from functools import lru_cache
from types import ModuleType

from ..config import obter_config


@lru_cache
def obter_backend() -> ModuleType:
    nome = obter_config().backend.strip().lower()
    if nome == "sqlite":
        from . import sqlite as modulo
    elif nome == "postgres":
        from . import postgres as modulo
    else:
        raise ValueError(f"backend desconhecido: {nome!r}. Use 'sqlite' ou 'postgres'.")
    return modulo
