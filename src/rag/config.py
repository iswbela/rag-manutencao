"""Configuracao central, lida do arquivo .env (veja .env.example)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[2]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # "sqlite" roda sem infraestrutura; "postgres" e o caminho de producao.
    # Veja src/rag/backends/__init__.py para o porque de existirem os dois.
    backend: str = "sqlite"
    database_url: str = "postgresql://rag:rag@localhost:5433/rag"
    sqlite_path: Path = RAIZ / "data" / "indice.sqlite3"

    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384

    # Camadas opcionais de recuperacao. Os padroes abaixo sao resultado de
    # medicao, nao de preferencia - a tabela esta no README.
    #
    # O filtro vem ligado: custou 3 ms e nao excluiu o documento certo em
    # nenhuma das 40 perguntas. O reranker vem desligado apesar de ser o maior
    # ganho medido (+19 pontos de recall@1), porque cobra cerca de 1 s por
    # pergunta em CPU e baixa 470 MB no primeiro uso - decisao de quem opera.
    filtro_equipamento: bool = True
    reranker_habilitado: bool = False
    # Treinado em mMARCO, que inclui portugues. Medido contra o
    # BAAI/bge-reranker-base, que e maior: este e mais preciso E mais rapido.
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    # Reordenar 20 candidatos custou 4x mais que reordenar 5 pelo mesmo recall.
    # 10 deixa folga sobre o TOP_K padrao sem pagar o desperdicio inteiro.
    candidatos_reranker: int = 10

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_temperatura: float = 0.1
    llm_timeout_s: int = 60

    top_k: int = 5
    candidatos_por_via: int = 20
    chunk_alvo_chars: int = 1600
    chunk_overlap_chars: int = 250

    pasta_pdfs: Path = RAIZ / "data" / "pdfs"
    pasta_avaliacao: Path = RAIZ / "data" / "avaliacao"

    @field_validator("sqlite_path", "pasta_pdfs", "pasta_avaliacao")
    @classmethod
    def _ancorar_na_raiz(cls, valor: Path) -> Path:
        """Caminho relativo no .env vale a partir da raiz do projeto.

        Sem isto, rodar `python scripts/indexar.py` de dentro de scripts/ e da
        raiz criaria dois indices diferentes, e o sintoma seria "indexei mas a
        busca nao acha nada".
        """
        return valor if valor.is_absolute() else RAIZ / valor

    @property
    def geracao_habilitada(self) -> bool:
        """Sem endpoint configurado o projeto roda em modo somente-busca."""
        return bool(self.llm_base_url and self.llm_model)


@lru_cache
def obter_config() -> Config:
    return Config()
