"""Backend Postgres + pgvector - o caminho de producao.

Por que Postgres e nao um banco vetorial dedicado: o projeto precisa guardar o
vetor, o texto, os metadados (arquivo, pagina, secao) e ainda fazer busca por
palavra-chave. O Postgres faz as tres coisas - vetor com pgvector, texto com
tsvector - em uma infraestrutura que a maioria dos times ja opera. Um servico
separado so para vetores seria mais uma peca para manter sem ganho nesta escala.

Este backend precisa de um servidor de pe (veja `docker-compose.yml`). Para
rodar o pipeline sem infraestrutura, use BACKEND=sqlite - a interface e a mesma.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from ..config import obter_config

ESQUEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documentos (
    id            SERIAL PRIMARY KEY,
    arquivo       TEXT UNIQUE NOT NULL,
    titulo        TEXT NOT NULL,
    codigo        TEXT,
    equipamento   TEXT,
    revisao       TEXT,
    paginas       INTEGER NOT NULL,
    hash_arquivo  TEXT NOT NULL,
    indexado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trechos (
    id             SERIAL PRIMARY KEY,
    documento_id   INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    ordem          INTEGER NOT NULL,
    texto          TEXT NOT NULL,
    secao          TEXT NOT NULL DEFAULT '',
    pagina_inicial INTEGER NOT NULL,
    pagina_final   INTEGER NOT NULL,
    embedding      VECTOR({dim}),
    busca_textual  TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('portuguese', coalesce(secao, '') || ' ' || texto)
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_trechos_embedding
    ON trechos USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_trechos_textual
    ON trechos USING gin (busca_textual);
CREATE INDEX IF NOT EXISTS idx_trechos_documento
    ON trechos (documento_id);
"""

# Fusao reciproca de rankings (RRF): cada via de busca contribui com
# 1/(k + posicao). E robusta porque compara POSICOES e nao pontuacoes - a
# similaridade de cosseno e o ts_rank vivem em escalas diferentes e somar os
# dois valores direto nao significaria nada.
CONSTANTE_RRF = 60

# O filtro por equipamento entra como predicado opcional: quando
# %(equipamentos)s vem NULL a condicao e sempre verdadeira e o plano fica igual
# ao de antes. Isso evita manter duas versoes de cada consulta. E uma lista, e
# nao um valor, porque documentos que valem para a frota inteira (um POP de
# lubrificacao) precisam continuar visiveis junto com o equipamento pedido.
_FILTRO = "(%(equipamentos)s::text[] IS NULL OR d.equipamento = ANY(%(equipamentos)s))"

SQL_BUSCA_HIBRIDA = f"""
WITH semantica AS (
    SELECT t.id, ROW_NUMBER() OVER (ORDER BY t.embedding <=> %(vetor)s) AS posicao
    FROM trechos t JOIN documentos d ON d.id = t.documento_id
    WHERE {_FILTRO}
    ORDER BY t.embedding <=> %(vetor)s
    LIMIT %(candidatos)s
),
textual AS (
    SELECT t.id,
           ROW_NUMBER() OVER (ORDER BY ts_rank(t.busca_textual, consulta) DESC) AS posicao
    FROM trechos t
    JOIN documentos d ON d.id = t.documento_id,
         plainto_tsquery('portuguese', %(pergunta)s) AS consulta
    WHERE t.busca_textual @@ consulta AND {_FILTRO}
    ORDER BY ts_rank(t.busca_textual, consulta) DESC
    LIMIT %(candidatos)s
),
fusao AS (
    SELECT COALESCE(s.id, x.id) AS id,
           COALESCE(1.0 / (%(k)s + s.posicao), 0)
         + COALESCE(1.0 / (%(k)s + x.posicao), 0) AS pontuacao
    FROM semantica s
    FULL OUTER JOIN textual x ON x.id = s.id
)
SELECT t.id, t.texto, t.secao, t.pagina_inicial, t.pagina_final,
       d.arquivo, d.titulo, d.equipamento, d.codigo, f.pontuacao
FROM fusao f
JOIN trechos t ON t.id = f.id
JOIN documentos d ON d.id = t.documento_id
ORDER BY f.pontuacao DESC
LIMIT %(limite)s;
"""

SQL_BUSCA_SEMANTICA = f"""
SELECT t.id, t.texto, t.secao, t.pagina_inicial, t.pagina_final,
       d.arquivo, d.titulo, d.equipamento, d.codigo,
       1 - (t.embedding <=> %(vetor)s) AS pontuacao
FROM trechos t
JOIN documentos d ON d.id = t.documento_id
WHERE {_FILTRO}
ORDER BY t.embedding <=> %(vetor)s
LIMIT %(limite)s;
"""

SQL_BUSCA_TEXTUAL = f"""
SELECT t.id, t.texto, t.secao, t.pagina_inicial, t.pagina_final,
       d.arquivo, d.titulo, d.equipamento, d.codigo,
       ts_rank(t.busca_textual, consulta) AS pontuacao
FROM trechos t
JOIN documentos d ON d.id = t.documento_id,
     plainto_tsquery('portuguese', %(pergunta)s) AS consulta
WHERE t.busca_textual @@ consulta AND {_FILTRO}
ORDER BY pontuacao DESC
LIMIT %(limite)s;
"""


@contextmanager
def conectar() -> Iterator[psycopg.Connection]:
    config = obter_config()
    with psycopg.connect(config.database_url, row_factory=dict_row) as conexao:
        register_vector(conexao)
        yield conexao


def criar_esquema() -> None:
    config = obter_config()
    with conectar() as conexao:
        conexao.execute(ESQUEMA.format(dim=config.embedding_dim))
        conexao.commit()


def limpar_tudo() -> None:
    with conectar() as conexao:
        conexao.execute("TRUNCATE documentos RESTART IDENTITY CASCADE;")
        conexao.commit()


def remover_documento(arquivo: str) -> None:
    with conectar() as conexao:
        conexao.execute("DELETE FROM documentos WHERE arquivo = %s;", (arquivo,))
        conexao.commit()


def hash_indexado(arquivo: str) -> str | None:
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT hash_arquivo FROM documentos WHERE arquivo = %s;", (arquivo,)
        ).fetchone()
    return linha["hash_arquivo"] if linha else None


def gravar_documento(meta: dict[str, Any], trechos: list[dict[str, Any]]) -> int:
    with conectar() as conexao:
        conexao.execute("DELETE FROM documentos WHERE arquivo = %s;", (meta["arquivo"],))
        linha = conexao.execute(
            """
            INSERT INTO documentos (arquivo, titulo, codigo, equipamento, revisao, paginas,
                                    hash_arquivo)
            VALUES (%(arquivo)s, %(titulo)s, %(codigo)s, %(equipamento)s, %(revisao)s,
                    %(paginas)s, %(hash_arquivo)s)
            RETURNING id;
            """,
            meta,
        ).fetchone()
        documento_id = linha["id"]
        with conexao.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO trechos (documento_id, ordem, texto, secao, pagina_inicial,
                                     pagina_final, embedding)
                VALUES (%(documento_id)s, %(ordem)s, %(texto)s, %(secao)s, %(pagina_inicial)s,
                        %(pagina_final)s, %(embedding)s);
                """,
                [{**t, "documento_id": documento_id} for t in trechos],
            )
        conexao.commit()
    return documento_id


def estatisticas() -> dict[str, Any]:
    with conectar() as conexao:
        documentos = conexao.execute(
            """
            SELECT d.arquivo, d.titulo, d.equipamento, d.paginas, d.indexado_em,
                   count(t.id) AS trechos
            FROM documentos d LEFT JOIN trechos t ON t.documento_id = d.id
            GROUP BY d.id ORDER BY d.arquivo;
            """
        ).fetchall()
        total = conexao.execute("SELECT count(*) AS total FROM trechos;").fetchone()["total"]
    return {"documentos": documentos, "total_trechos": total}


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------


def _vetor_pg(vetor: list[float]):
    """psycopg precisa de um ndarray para casar com o adaptador do pgvector."""
    import numpy as np

    return np.asarray(vetor, dtype=np.float32)


def buscar_semantica(
    vetor: list[float], limite: int, equipamentos: list[str] | None = None
) -> list[dict[str, Any]]:
    with conectar() as conexao:
        linhas = conexao.execute(
            SQL_BUSCA_SEMANTICA,
            {"vetor": _vetor_pg(vetor), "limite": limite, "equipamentos": equipamentos},
        ).fetchall()
    return [dict(linha) for linha in linhas]


def buscar_textual(
    pergunta: str, limite: int, equipamentos: list[str] | None = None
) -> list[dict[str, Any]]:
    with conectar() as conexao:
        linhas = conexao.execute(
            SQL_BUSCA_TEXTUAL,
            {"pergunta": pergunta, "limite": limite, "equipamentos": equipamentos},
        ).fetchall()
    return [dict(linha) for linha in linhas]


def buscar_hibrida(
    vetor: list[float],
    pergunta: str,
    limite: int,
    candidatos: int,
    equipamentos: list[str] | None = None,
) -> list[dict[str, Any]]:
    with conectar() as conexao:
        linhas = conexao.execute(
            SQL_BUSCA_HIBRIDA,
            {
                "vetor": _vetor_pg(vetor),
                "pergunta": pergunta,
                "candidatos": candidatos,
                "k": CONSTANTE_RRF,
                "limite": limite,
                "equipamentos": equipamentos,
            },
        ).fetchall()
    return [dict(linha) for linha in linhas]
