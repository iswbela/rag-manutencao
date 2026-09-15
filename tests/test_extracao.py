"""Testes da extracao: rodam sobre os PDFs de exemplo, sem banco e sem rede."""
from __future__ import annotations

from pathlib import Path

import pytest

from rag.extracao import extrair, listar_pdfs, normalizar

PASTA = Path(__file__).resolve().parents[1] / "data" / "pdfs"
pytestmark = pytest.mark.skipif(
    not listar_pdfs(PASTA), reason="rode 'python scripts/gerar_pdfs.py' antes"
)


def test_linha_de_tabela_vira_celulas_separadas_por_barra():
    bruto = "500 h         Filtro hidraulico de retorno      Trocar        FH-P5501"
    assert normalizar(bruto) == "500 h | Filtro hidraulico de retorno | Trocar | FH-P5501"


def test_rodape_repetido_e_removido():
    bruto = "Conteudo util\nMAN-MTX220-PT - rev. 4\nPagina 3"
    assert normalizar(bruto) == "Conteudo util"


def test_extrai_todas_as_paginas_com_numeracao_correta():
    documento = extrair(PASTA / "manual-escavadeira-mtx220.pdf")
    assert documento.total_paginas >= 3
    assert [p.numero for p in documento.paginas] == list(
        range(1, documento.total_paginas + 1)
    )


def test_codigo_de_peca_sobrevive_a_extracao():
    documento = extrair(PASTA / "manual-escavadeira-mtx220.pdf")
    texto = "\n".join(p.texto for p in documento.paginas)
    for codigo in ("FH-P5501", "FC-2202", "AR-7745"):
        assert codigo in texto
