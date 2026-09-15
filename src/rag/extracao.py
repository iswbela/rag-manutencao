"""Etapa 1 do pipeline: PDF -> texto por pagina, ja normalizado.

Decisoes que importam aqui:

* A extracao usa o modo "layout" do pypdf, que preserva a posicao horizontal do
  texto. Sem ele, as celulas de uma tabela saem embaralhadas e a informacao mais
  procurada nos manuais (intervalo de troca, limite de desgaste) fica ilegivel
  para a busca.
* Cada linha de tabela e convertida em "celula | celula | celula". Essa unica
  linha vale mais do que parece: melhora tanto o embedding quanto a busca por
  palavra-chave, porque mantem o intervalo colado ao componente e ao codigo da
  peca.
* O rodape repetido em toda pagina e removido. Se ficasse, apareceria em todo
  chunk e adicionaria ruido identico a todos os vetores.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

# 3 ou mais espacos seguidos = separacao de coluna gerada pelo modo layout
_COLUNAS = re.compile(r"\s{3,}")
_RODAPE = re.compile(r"^\s*(Pagina\s+\d+|[A-Z]{3}-[A-Z0-9]+-PT\s*-\s*rev\.)", re.IGNORECASE)
_ESPACOS = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class Pagina:
    numero: int  # 1-based, igual ao que o usuario ve no PDF
    texto: str


@dataclass(frozen=True)
class Documento:
    arquivo: str
    caminho: Path
    titulo: str
    paginas: list[Pagina]

    @property
    def total_paginas(self) -> int:
        return len(self.paginas)


def _limpar_linha(linha: str) -> str:
    if _RODAPE.match(linha):
        return ""
    linha = _COLUNAS.sub(" | ", linha.strip())
    linha = _ESPACOS.sub(" ", linha)
    # celulas vazias viram "|" solto e nao acrescentam nada
    linha = re.sub(r"(\s\|\s)+", " | ", linha).strip(" |").strip()
    return linha


def normalizar(texto_bruto: str) -> str:
    linhas = [_limpar_linha(linha) for linha in texto_bruto.splitlines()]
    resultado: list[str] = []
    vazias = 0
    for linha in linhas:
        if linha:
            vazias = 0
            resultado.append(linha)
        else:
            vazias += 1
            if vazias == 1:
                resultado.append("")
    return "\n".join(resultado).strip()


def extrair(caminho: Path) -> Documento:
    leitor = PdfReader(str(caminho))
    paginas: list[Pagina] = []
    for indice, pagina in enumerate(leitor.pages, start=1):
        try:
            bruto = pagina.extract_text(extraction_mode="layout") or ""
        except Exception:  # pragma: no cover - depende do PDF de entrada
            bruto = pagina.extract_text() or ""
        texto = normalizar(bruto)
        if texto:
            paginas.append(Pagina(numero=indice, texto=texto))

    titulo = ""
    meta = leitor.metadata
    if meta and meta.title:
        titulo = str(meta.title)
    if not titulo and paginas:
        titulo = paginas[0].texto.splitlines()[0][:200]

    if not paginas:
        raise ValueError(
            f"{caminho.name}: nenhum texto extraido. PDF escaneado precisa passar por OCR antes."
        )

    return Documento(arquivo=caminho.name, caminho=caminho, titulo=titulo, paginas=paginas)


def listar_pdfs(pasta: Path) -> list[Path]:
    return sorted(p for p in pasta.glob("*.pdf"))
