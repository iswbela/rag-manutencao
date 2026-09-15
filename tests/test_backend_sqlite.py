"""Testes do backend SQLite com vetores inventados.

Rodam sem baixar modelo e sem subir banco: o que esta sob teste e a persistencia
e a fusao de rankings, nao a qualidade dos embeddings. Vetores de tres dimensoes
escolhidos na mao deixam o resultado esperado obvio.
"""
from __future__ import annotations

import pytest

from rag.backends import sqlite as backend
from rag.config import obter_config


@pytest.fixture
def indice(tmp_path, monkeypatch):
    """Um indice novo por teste, em arquivo temporario."""
    config = obter_config()
    monkeypatch.setattr(config, "sqlite_path", tmp_path / "indice.sqlite3")
    backend.criar_esquema()

    def gravar(arquivo, equipamento, trechos):
        backend.gravar_documento(
            {
                "arquivo": arquivo,
                "titulo": f"Manual {equipamento}",
                "codigo": None,
                "equipamento": equipamento,
                "revisao": "1",
                "paginas": 1,
                "hash_arquivo": "abc",
            },
            [
                {
                    "ordem": ordem,
                    "texto": texto,
                    "secao": secao,
                    "pagina_inicial": 1,
                    "pagina_final": 1,
                    "embedding": vetor,
                }
                for ordem, (texto, secao, vetor) in enumerate(trechos)
            ],
        )

    return gravar


def test_grava_e_conta(indice):
    indice("a.pdf", "Escavadeira MTX-220", [("filtro de retorno FH-P5501", "4.2", [1.0, 0.0, 0.0])])
    dados = backend.estatisticas()
    assert dados["total_trechos"] == 1
    assert dados["documentos"][0]["equipamento"] == "Escavadeira MTX-220"


def test_reindexar_o_mesmo_arquivo_nao_duplica(indice):
    for _ in range(2):
        indice("a.pdf", "Escavadeira MTX-220", [("filtro de retorno", "", [1.0, 0.0, 0.0])])
    assert backend.estatisticas()["total_trechos"] == 1


def test_remover_documento_limpa_o_indice_textual(indice):
    """Se o FTS ficasse com a linha orfa, a busca textual devolveria um id que
    nao existe mais - e o sintoma seria resultado sumindo do meio da lista."""
    indice("a.pdf", "Escavadeira MTX-220", [("filtro hidraulico de retorno", "", [1.0, 0.0, 0.0])])
    backend.remover_documento("a.pdf")
    assert backend.buscar_textual("filtro hidraulico", 5) == []
    assert backend.estatisticas()["total_trechos"] == 0


def test_busca_semantica_ordena_por_proximidade(indice):
    indice(
        "a.pdf",
        "Escavadeira MTX-220",
        [
            ("longe", "", [0.0, 1.0, 0.0]),
            ("perto", "", [0.9, 0.1, 0.0]),
            ("exato", "", [1.0, 0.0, 0.0]),
        ],
    )
    resultados = backend.buscar_semantica([1.0, 0.0, 0.0], 3)
    assert [r["texto"] for r in resultados] == ["exato", "perto", "longe"]


def test_vetor_de_dimensao_errada_da_erro_explicito(indice):
    """Trocar de modelo de embeddings sem reindexar e o erro mais facil de
    cometer neste projeto. A mensagem precisa dizer o que fazer."""
    indice("a.pdf", "Escavadeira MTX-220", [("texto", "", [1.0, 0.0, 0.0])])
    with pytest.raises(ValueError, match="--recriar"):
        backend.buscar_semantica([1.0, 0.0], 3)


def test_busca_textual_acha_codigo_de_peca(indice):
    """O codigo exato e onde a busca por palavra-chave ganha da vetorial:
    FH-P5501 e FH-P5502 sao quase o mesmo ponto no espaco de embeddings."""
    indice(
        "a.pdf",
        "Escavadeira MTX-220",
        [
            ("filtro de retorno FH-P5501 a cada 500 h", "", [1.0, 0.0, 0.0]),
            ("filtro piloto FH-P5502 a cada 1000 h", "", [1.0, 0.0, 0.0]),
        ],
    )
    resultados = backend.buscar_textual("qual o intervalo do FH-P5502", 2)
    assert "FH-P5502" in resultados[0]["texto"]


def test_busca_textual_ignora_acento(indice):
    indice("a.pdf", "Britador BC-900", [("plano de lubrificacao do britador", "", [1.0, 0.0, 0.0])])
    assert backend.buscar_textual("lubrificação", 5)


def test_filtro_por_equipamento_restringe_as_duas_vias(indice):
    indice("a.pdf", "Escavadeira MTX-220", [("torque do parafuso 930 N.m", "", [1.0, 0.0, 0.0])])
    indice("b.pdf", "Caminhao CF-450", [("torque do parafuso 900 N.m", "", [1.0, 0.0, 0.0])])

    for resultados in (
        backend.buscar_semantica([1.0, 0.0, 0.0], 5, ["Caminhao CF-450"]),
        backend.buscar_textual("torque do parafuso", 5, ["Caminhao CF-450"]),
        backend.buscar_hibrida([1.0, 0.0, 0.0], "torque do parafuso", 5, 10, ["Caminhao CF-450"]),
    ):
        assert [r["arquivo"] for r in resultados] == ["b.pdf"]


def test_hibrida_promove_o_trecho_que_as_duas_vias_acham(indice):
    """O valor do RRF: estar nas duas listas vence estar no topo de uma so.

    Com `candidatos=2`, cada via corta o terceiro colocado. O trecho que sobra
    nas duas soma 1/62 duas vezes e passa na frente de quem soma 1/61 uma vez.

    O que este teste NAO afirma: que "2o em ambas" vence "1o numa e 3o na
    outra". Com k=60 essas duas somas empatam ate a quinta casa - o RRF separa
    presenca de ausencia, nao posicoes vizinhas.
    """
    indice(
        "a.pdf",
        "Escavadeira MTX-220",
        [
            # so a via textual acha: melhor BM25 (curto, todos os termos)
            ("filtro hidraulico de retorno", "", [0.0, 1.0, 0.0]),
            # so a via semantica acha: nenhum termo em comum com a pergunta
            ("assunto sem nada a ver", "", [1.0, 0.0, 0.0]),
            # as duas acham, em segundo lugar nas duas
            ("filtro hidraulico de retorno do reservatorio hidraulico", "", [0.9, 0.1, 0.0]),
        ],
    )
    resultados = backend.buscar_hibrida(
        [1.0, 0.0, 0.0], "filtro hidraulico de retorno", limite=3, candidatos=2
    )
    assert resultados[0]["texto"] == "filtro hidraulico de retorno do reservatorio hidraulico"


def test_consulta_fts_descarta_palavra_vazia_e_preserva_codigo():
    expressao = backend.montar_consulta_fts("Qual o codigo do filtro da MTX-220?")
    assert '"qual"' not in expressao
    assert '"codigo"' in expressao
    assert '"mtx"' in expressao and '"220"' in expressao
    # tudo entre aspas: sem isso o hifen de "MTX-220" viraria operador do FTS5
    assert "-" not in expressao


def test_consulta_fts_vazia_nao_quebra_a_busca(indice):
    """Pergunta so com palavra vazia geraria MATCH '' e erro de sintaxe no FTS5."""
    indice("a.pdf", "Escavadeira MTX-220", [("texto", "", [1.0, 0.0, 0.0])])
    assert backend.montar_consulta_fts("o que e isso") == ""
    assert backend.buscar_textual("o que e isso", 5) == []
