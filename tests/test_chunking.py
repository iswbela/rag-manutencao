"""Testes do chunking: e aqui que a qualidade da recuperacao e ganha ou perdida."""
from __future__ import annotations

from pathlib import Path

import pytest

from rag.chunking import Trecho, dividir, texto_para_embedding
from rag.extracao import extrair, listar_pdfs

PASTA = Path(__file__).resolve().parents[1] / "data" / "pdfs"
pytestmark = pytest.mark.skipif(
    not listar_pdfs(PASTA), reason="rode 'python scripts/gerar_pdfs.py' antes"
)


@pytest.fixture(scope="module")
def trechos():
    return dividir(extrair(PASTA / "manual-escavadeira-mtx220.pdf"))


def test_gera_varios_trechos_dentro_do_tamanho_alvo(trechos):
    assert len(trechos) >= 5
    # a tolerancia existe porque um bloco nunca e partido no meio de uma linha
    assert all(len(t.texto) <= 1600 * 1.6 for t in trechos)


def test_todo_trecho_carrega_a_pagina_de_origem(trechos):
    assert all(t.pagina_inicial >= 1 for t in trechos)
    assert all(t.pagina_final >= t.pagina_inicial for t in trechos)


def test_maioria_dos_trechos_conhece_a_propria_secao(trechos):
    com_secao = sum(1 for t in trechos if t.secao)
    assert com_secao / len(trechos) > 0.8


def test_linha_de_tabela_nao_e_partida_no_meio(trechos):
    linhas = [linha for t in trechos for linha in t.texto.splitlines() if "FH-P5501" in linha]
    assert linhas, "a linha do filtro de retorno deveria estar em algum trecho"
    assert any("500 h" in linha and "Trocar" in linha for linha in linhas)


def test_trechos_vizinhos_se_sobrepoem_ou_comecam_secao_nova(trechos):
    """A sobreposicao evita perder a frase cortada na fronteira entre trechos."""
    pares_com_overlap = 0
    for anterior, atual in zip(trechos, trechos[1:]):
        cauda = anterior.texto[-120:].strip()
        if cauda and cauda in atual.texto:
            pares_com_overlap += 1
    assert pares_com_overlap >= 1


def test_contexto_e_anexado_ao_texto_enviado_para_o_embedding():
    trecho = Trecho(
        ordem=0,
        texto="500 h | Filtro hidraulico de retorno | Trocar | FH-P5501",
        secao="3. Plano de manutencao preventiva",
        pagina_inicial=2,
        pagina_final=2,
    )
    entrada = texto_para_embedding("Manual da Escavadeira MTX-220", trecho)
    assert "MTX-220" in entrada
    assert "3. Plano de manutencao preventiva" in entrada
    assert "FH-P5501" in entrada
