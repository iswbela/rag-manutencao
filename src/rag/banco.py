"""Fachada da persistencia: delega para o backend escolhido no .env.

O resto do projeto importa `banco` e nao sabe se por baixo esta o Postgres ou o
SQLite. Isso e o que permite desenvolver chunking e embeddings sem infraestrutura
e ainda assim rodar a mesma indexacao contra o Postgres em producao, sem tocar
em `indexacao.py`, `busca.py` ou `api.py`.
"""
from __future__ import annotations

from typing import Any

from .backends import obter_backend
from .config import obter_config


def nome_backend() -> str:
    return obter_config().backend.strip().lower()


def conectar():
    return obter_backend().conectar()


def criar_esquema() -> None:
    obter_backend().criar_esquema()


def limpar_tudo() -> None:
    obter_backend().limpar_tudo()


def remover_documento(arquivo: str) -> None:
    obter_backend().remover_documento(arquivo)


def hash_indexado(arquivo: str) -> str | None:
    return obter_backend().hash_indexado(arquivo)


def gravar_documento(meta: dict[str, Any], trechos: list[dict[str, Any]]) -> int:
    return obter_backend().gravar_documento(meta, trechos)


def estatisticas() -> dict[str, Any]:
    return obter_backend().estatisticas()


def buscar_semantica(
    vetor: list[float], limite: int, equipamentos: list[str] | None = None
) -> list[dict[str, Any]]:
    return obter_backend().buscar_semantica(vetor, limite, equipamentos)


def buscar_textual(
    pergunta: str, limite: int, equipamentos: list[str] | None = None
) -> list[dict[str, Any]]:
    return obter_backend().buscar_textual(pergunta, limite, equipamentos)


def buscar_hibrida(
    vetor: list[float],
    pergunta: str,
    limite: int,
    candidatos: int,
    equipamentos: list[str] | None = None,
) -> list[dict[str, Any]]:
    return obter_backend().buscar_hibrida(vetor, pergunta, limite, candidatos, equipamentos)
