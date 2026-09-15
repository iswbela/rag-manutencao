"""Contratos de entrada e saida da API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Consulta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500, examples=["Qual o intervalo de troca do filtro hidraulico de retorno da MTX-220?"])
    top_k: int | None = Field(default=None, ge=1, le=20)
    estrategia: Literal["hibrida", "semantica", "textual"] = "hibrida"

    # As tres abaixo aceitam None para herdar o padrao do .env. Ficam expostas na
    # API porque sao exatamente os botoes que se quer girar ao investigar uma
    # resposta ruim, sem reiniciar o servico.
    equipamento: str | None = Field(
        default=None,
        description="restringe a busca a este equipamento; documentos validos para a "
        "frota inteira continuam visiveis",
    )
    filtrar_equipamento: bool | None = Field(
        default=None, description="infere o equipamento a partir do texto da pergunta"
    )
    reordenar: bool | None = Field(
        default=None, description="reordena os candidatos com o cross-encoder"
    )


class Fonte(BaseModel):
    indice: int
    documento: str
    arquivo: str
    codigo: str | None = None
    equipamento: str | None = None
    secao: str = ""
    pagina_inicial: int
    pagina_final: int
    pontuacao: float
    # Preenchida so quando o reranker roda: e a pontuacao que a busca dera antes
    # da reordenacao. Sem ela nao da para auditar se o reranker ajudou.
    pontuacao_recuperacao: float | None = None
    trecho: str


class RespostaBusca(BaseModel):
    pergunta: str
    estrategia: str
    latencia_ms: int
    fontes: list[Fonte]


class RespostaPergunta(BaseModel):
    pergunta: str
    resposta: str
    fontes: list[Fonte]
    latencia_ms: int
    latencia_busca_ms: int
    latencia_geracao_ms: int
    modelo: str
    uso: dict = {}
