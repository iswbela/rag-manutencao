"""Testes do prompt. Nao chamam nenhum endpoint externo."""
from __future__ import annotations

from rag.geracao import INSTRUCAO_SISTEMA, montar_prompt

TRECHOS = [
    {
        "titulo": "Manual de Manutencao - Escavadeira Hidraulica MTX-220",
        "arquivo": "manual-escavadeira-mtx220.pdf",
        "codigo": "MAN-MTX220-PT",
        "secao": "3. Plano de manutencao preventiva",
        "texto": "500 h | Filtro hidraulico de retorno | Trocar | FH-P5501",
        "pagina_inicial": 2,
        "pagina_final": 2,
    },
    {
        "titulo": "Procedimento Operacional Padrao - Lubrificacao e Analise de Oleo",
        "arquivo": "pop-lubrificacao-analise-oleo.pdf",
        "codigo": "POP-LUB-004",
        "secao": "5. Limites de alerta e de acao",
        "texto": "Silicio (Si) | ate 15 ppm | 15 a 25 ppm | acima de 25 ppm",
        "pagina_inicial": 3,
        "pagina_final": 3,
    },
]


def test_prompt_numera_os_trechos_para_permitir_citacao():
    prompt = montar_prompt("Quando trocar o filtro de retorno?", TRECHOS)
    assert "[1]" in prompt and "[2]" in prompt


def test_prompt_carrega_documento_secao_e_pagina_de_cada_trecho():
    prompt = montar_prompt("Quando trocar o filtro de retorno?", TRECHOS)
    assert "MAN-MTX220-PT, pag. 2" in prompt
    assert "3. Plano de manutencao preventiva" in prompt


def test_prompt_termina_com_a_pergunta():
    prompt = montar_prompt("Quando trocar o filtro de retorno?", TRECHOS)
    assert prompt.rstrip().endswith("Resposta:")
    assert "Quando trocar o filtro de retorno?" in prompt


def test_instrucao_exige_recusa_e_citacao():
    assert "Nao encontrei essa informacao nos documentos indexados." in INSTRUCAO_SISTEMA
    assert "EXCLUSIVAMENTE" in INSTRUCAO_SISTEMA
