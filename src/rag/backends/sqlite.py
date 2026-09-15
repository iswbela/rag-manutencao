"""Backend SQLite: o mesmo pipeline sem nenhuma infraestrutura para subir.

Como cada metade da busca hibrida e resolvida aqui:

* textual - FTS5, que ja vem compilado no SQLite da biblioteca padrao, com
  ranking BM25. O tokenizador `unicode61 remove_diacritics 2` resolve o
  problema pratico do portugues escrito na oficina: "manutencao" sem til e
  "manutenção" com til caem no mesmo token. Nao ha stemmer, entao a lista de
  palavras vazias abaixo faz o trabalho que o dicionario `portuguese` do
  Postgres faria.
* semantica - produto interno em numpy sobre a matriz inteira de vetores. Como
  os embeddings sao normalizados na geracao, produto interno e cosseno. Sem
  indice aproximado: com poucos milhares de trechos a forca bruta e mais rapida
  que um HNSW, e nunca erra o vizinho mais proximo.

Diferenca deliberada em relacao ao Postgres: la o `plainto_tsquery` liga os
termos com AND, o que faz a via textual devolver pouco ou nada para pergunta
longa; aqui os termos sao ligados com OR e o BM25 cuida de ordenar. Na pratica o
SQLite recupera mais na via textual - vale lembrar disso ao comparar numeros
entre os dois backends.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from ..config import obter_config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS documentos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    arquivo       TEXT UNIQUE NOT NULL,
    titulo        TEXT NOT NULL,
    codigo        TEXT,
    equipamento   TEXT,
    revisao       TEXT,
    paginas       INTEGER NOT NULL,
    hash_arquivo  TEXT NOT NULL,
    indexado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trechos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id   INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    ordem          INTEGER NOT NULL,
    texto          TEXT NOT NULL,
    secao          TEXT NOT NULL DEFAULT '',
    pagina_inicial INTEGER NOT NULL,
    pagina_final   INTEGER NOT NULL,
    embedding      BLOB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trechos_documento ON trechos (documento_id);

CREATE VIRTUAL TABLE IF NOT EXISTS trechos_fts USING fts5(
    secao, texto, tokenize='unicode61 remove_diacritics 2'
);
"""
# Nota sobre a tabela FTS: ela guarda copia propria do texto, em vez de usar
# `content=trechos`. O custo em disco e irrelevante nesta escala e em troca
# INSERT e DELETE comuns funcionam, sem a sintaxe especial das tabelas de
# conteudo externo.

CONSTANTE_RRF = 60

# Sem stemmer no FTS5, palavra vazia em consulta ligada por OR casa com tudo.
# O BM25 ja as pontuaria baixo, mas tira-las antes deixa o ranking mais limpo.
_VAZIAS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "deve", "devo",
    "do", "dos", "e", "em", "essa", "esse", "esta", "estao", "este", "eu",
    "fazer", "foi", "isso", "ja", "mais", "mas", "me", "meu", "na", "nas",
    "no", "nos", "num", "numa", "o", "os", "ou", "para", "pela", "pelo", "por",
    "posso", "pra", "preciso", "qual", "quais", "quando", "quanto", "quantos",
    "que", "quem", "se", "sem", "ser", "seu", "sobre", "sua", "tem", "tenho",
    "ter", "um", "uma", "vou",
}

_TOKEN = re.compile(r"[0-9a-zA-Z]+")


def _caminho() -> Path:
    caminho = obter_config().sqlite_path
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho


@contextmanager
def conectar() -> Iterator[sqlite3.Connection]:
    conexao = sqlite3.connect(_caminho())
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conexao
    finally:
        conexao.close()


def criar_esquema() -> None:
    with conectar() as conexao:
        conexao.executescript(ESQUEMA)
        conexao.commit()


def limpar_tudo() -> None:
    with conectar() as conexao:
        conexao.executescript(
            "DELETE FROM trechos_fts; DELETE FROM trechos; DELETE FROM documentos;"
        )
        conexao.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('trechos','documentos');"
        )
        conexao.commit()


def _apagar_documento(conexao: sqlite3.Connection, arquivo: str) -> None:
    conexao.execute(
        """
        DELETE FROM trechos_fts WHERE rowid IN (
            SELECT t.id FROM trechos t JOIN documentos d ON d.id = t.documento_id
            WHERE d.arquivo = ?
        );
        """,
        (arquivo,),
    )
    conexao.execute(
        "DELETE FROM trechos WHERE documento_id IN "
        "(SELECT id FROM documentos WHERE arquivo = ?);",
        (arquivo,),
    )
    conexao.execute("DELETE FROM documentos WHERE arquivo = ?;", (arquivo,))


def remover_documento(arquivo: str) -> None:
    with conectar() as conexao:
        _apagar_documento(conexao, arquivo)
        conexao.commit()


def hash_indexado(arquivo: str) -> str | None:
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT hash_arquivo FROM documentos WHERE arquivo = ?;", (arquivo,)
        ).fetchone()
    return linha["hash_arquivo"] if linha else None


def gravar_documento(meta: dict[str, Any], trechos: list[dict[str, Any]]) -> int:
    with conectar() as conexao:
        _apagar_documento(conexao, meta["arquivo"])
        cursor = conexao.execute(
            """
            INSERT INTO documentos (arquivo, titulo, codigo, equipamento, revisao,
                                    paginas, hash_arquivo)
            VALUES (:arquivo, :titulo, :codigo, :equipamento, :revisao, :paginas,
                    :hash_arquivo);
            """,
            meta,
        )
        documento_id = int(cursor.lastrowid)
        for trecho in trechos:
            vetor = np.asarray(trecho["embedding"], dtype=np.float32)
            cursor = conexao.execute(
                """
                INSERT INTO trechos (documento_id, ordem, texto, secao, pagina_inicial,
                                     pagina_final, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    documento_id,
                    trecho["ordem"],
                    trecho["texto"],
                    trecho["secao"],
                    trecho["pagina_inicial"],
                    trecho["pagina_final"],
                    vetor.tobytes(),
                ),
            )
            conexao.execute(
                "INSERT INTO trechos_fts (rowid, secao, texto) VALUES (?, ?, ?);",
                (int(cursor.lastrowid), trecho["secao"], trecho["texto"]),
            )
        conexao.commit()
    return documento_id


def estatisticas() -> dict[str, Any]:
    with conectar() as conexao:
        documentos = [
            dict(linha)
            for linha in conexao.execute(
                """
                SELECT d.arquivo, d.titulo, d.equipamento, d.paginas, d.indexado_em,
                       count(t.id) AS trechos
                FROM documentos d LEFT JOIN trechos t ON t.documento_id = d.id
                GROUP BY d.id ORDER BY d.arquivo;
                """
            ).fetchall()
        ]
        total = conexao.execute(
            "SELECT count(*) AS total FROM trechos;"
        ).fetchone()["total"]
    return {"documentos": documentos, "total_trechos": total}


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------

_CAMPOS = """
    t.id, t.texto, t.secao, t.pagina_inicial, t.pagina_final,
    d.arquivo, d.titulo, d.equipamento, d.codigo
"""


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def montar_consulta_fts(pergunta: str) -> str:
    """Pergunta em linguagem natural -> expressao MATCH do FTS5.

    Cada termo vai entre aspas para que o FTS5 o trate como literal: sem isso um
    hifen em codigo de peca ("MTX-220") seria lido como operador.
    """
    termos: list[str] = []
    for bruto in _TOKEN.findall(_sem_acento(pergunta).lower()):
        if bruto in _VAZIAS:
            continue
        if len(bruto) < 3 and not any(c.isdigit() for c in bruto):
            continue
        if bruto not in termos:
            termos.append(bruto)
    return " OR ".join('"' + t + '"' for t in termos)


def _carregar_vetores(conexao: sqlite3.Connection) -> tuple[list[int], np.ndarray]:
    linhas = conexao.execute("SELECT id, embedding FROM trechos ORDER BY id;").fetchall()
    if not linhas:
        return [], np.zeros((0, 0), dtype=np.float32)
    ids = [int(linha["id"]) for linha in linhas]
    matriz = np.vstack(
        [np.frombuffer(linha["embedding"], dtype=np.float32) for linha in linhas]
    )
    return ids, matriz


def _ids_permitidos(
    conexao: sqlite3.Connection, equipamentos: list[str] | None
) -> set[int] | None:
    """Restricao por equipamento (None = sem filtro).

    O filtro vive no backend, e nao depois do ranking, para que o corte por
    `limite` ja conte so trechos elegiveis: filtrar depois devolveria menos
    resultados do que o pedido sempre que a base tiver varios equipamentos.
    """
    if not equipamentos:
        return None
    marcadores = ",".join("?" * len(equipamentos))
    linhas = conexao.execute(
        "SELECT t.id FROM trechos t JOIN documentos d ON d.id = t.documento_id "
        "WHERE d.equipamento IN (" + marcadores + ");",
        equipamentos,
    ).fetchall()
    return {int(linha["id"]) for linha in linhas}


def _detalhar(
    conexao: sqlite3.Connection, pontuados: list[tuple[int, float]]
) -> list[dict[str, Any]]:
    """Campos completos dos trechos escolhidos, preservando a ordem do ranking."""
    if not pontuados:
        return []
    ids = [i for i, _ in pontuados]
    marcadores = ",".join("?" * len(ids))
    linhas = conexao.execute(
        "SELECT " + _CAMPOS + " FROM trechos t JOIN documentos d ON d.id = t.documento_id "
        "WHERE t.id IN (" + marcadores + ");",
        ids,
    ).fetchall()
    por_id = {int(linha["id"]): dict(linha) for linha in linhas}
    resultado = []
    for identificador, pontuacao in pontuados:
        linha = por_id.get(identificador)
        if linha is not None:
            resultado.append({**linha, "pontuacao": float(pontuacao)})
    return resultado


def _ranking_semantico(
    conexao: sqlite3.Connection,
    vetor: list[float],
    limite: int,
    equipamentos: list[str] | None,
) -> list[tuple[int, float]]:
    ids, matriz = _carregar_vetores(conexao)
    if not ids:
        return []
    consulta = np.asarray(vetor, dtype=np.float32)
    if consulta.shape[0] != matriz.shape[1]:
        raise ValueError(
            "dimensao do vetor da pergunta (" + str(consulta.shape[0]) + ") nao bate com a "
            "do indice (" + str(matriz.shape[1]) + "). Trocou de modelo de embeddings? "
            "Reindexe com --recriar."
        )
    permitidos = _ids_permitidos(conexao, equipamentos)
    pontuacoes = matriz @ consulta  # vetores normalizados: produto interno = cosseno
    saida: list[tuple[int, float]] = []
    for posicao in np.argsort(-pontuacoes):
        identificador = ids[int(posicao)]
        if permitidos is not None and identificador not in permitidos:
            continue
        saida.append((identificador, float(pontuacoes[int(posicao)])))
        if len(saida) >= limite:
            break
    return saida


def _ranking_textual(
    conexao: sqlite3.Connection,
    pergunta: str,
    limite: int,
    equipamentos: list[str] | None,
) -> list[tuple[int, float]]:
    expressao = montar_consulta_fts(pergunta)
    if not expressao:
        return []
    permitidos = _ids_permitidos(conexao, equipamentos)
    # bm25() do FTS5 devolve valor negativo, mais negativo = mais relevante.
    # Invertemos o sinal para que "maior pontuacao = melhor" valha no projeto
    # inteiro. Os pesos (2.0, 1.0) dao a secao o dobro do peso do corpo.
    linhas = conexao.execute(
        "SELECT rowid AS id, -bm25(trechos_fts, 2.0, 1.0) AS pontuacao "
        "FROM trechos_fts WHERE trechos_fts MATCH ? ORDER BY pontuacao DESC LIMIT ?;",
        (expressao, limite * 5 if permitidos is not None else limite),
    ).fetchall()
    saida: list[tuple[int, float]] = []
    for linha in linhas:
        identificador = int(linha["id"])
        if permitidos is not None and identificador not in permitidos:
            continue
        saida.append((identificador, float(linha["pontuacao"])))
        if len(saida) >= limite:
            break
    return saida


def buscar_semantica(
    vetor: list[float], limite: int, equipamentos: list[str] | None = None
) -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _detalhar(conexao, _ranking_semantico(conexao, vetor, limite, equipamentos))


def buscar_textual(
    pergunta: str, limite: int, equipamentos: list[str] | None = None
) -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _detalhar(conexao, _ranking_textual(conexao, pergunta, limite, equipamentos))


def buscar_hibrida(
    vetor: list[float],
    pergunta: str,
    limite: int,
    candidatos: int,
    equipamentos: list[str] | None = None,
) -> list[dict[str, Any]]:
    with conectar() as conexao:
        semantica = _ranking_semantico(conexao, vetor, candidatos, equipamentos)
        textual = _ranking_textual(conexao, pergunta, candidatos, equipamentos)

        pontos: dict[int, float] = {}
        for ranking in (semantica, textual):
            for posicao, (identificador, _) in enumerate(ranking, start=1):
                pontos[identificador] = pontos.get(identificador, 0.0) + 1.0 / (
                    CONSTANTE_RRF + posicao
                )
        melhores = sorted(pontos.items(), key=lambda par: par[1], reverse=True)[:limite]
        return _detalhar(conexao, melhores)
