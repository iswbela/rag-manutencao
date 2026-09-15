"""Gera a base de conhecimento inicial: manuais e procedimentos em PDF.

Os documentos sao ficticios, porem escritos no formato e no vocabulario de
manuais reais de manutencao de equipamentos moveis de mina: secoes numeradas,
tabelas de intervalo, codigos de peca e tabelas de diagnostico. Isso importa
porque o pipeline de RAG e avaliado justamente na capacidade de achar um
intervalo dentro de uma tabela e um codigo de peca dentro de um paragrafo.

Uso:
    python scripts/gerar_pdfs.py [--saida data/pdfs]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conteudo_pdfs import DOCUMENTOS  # noqa: E402

CINZA = colors.HexColor("#3F4A54")
CINZA_CLARO = colors.HexColor("#E8EBEE")


def _estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontSize=18, leading=22, textColor=CINZA
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], fontSize=11, leading=15, textColor=CINZA
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontSize=13,
            leading=16,
            spaceBefore=14,
            spaceAfter=6,
            textColor=CINZA,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=4,
            textColor=CINZA,
        ),
        "p": ParagraphStyle(
            "p",
            parent=base["BodyText"],
            fontSize=9.5,
            leading=13.5,
            alignment=TA_JUSTIFY,
            spaceAfter=5,
        ),
        "celula": ParagraphStyle("celula", parent=base["BodyText"], fontSize=8.5, leading=11),
        "celula_cab": ParagraphStyle(
            "celula_cab",
            parent=base["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        ),
        "legenda": ParagraphStyle(
            "legenda",
            parent=base["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6B7580"),
            spaceAfter=10,
        ),
    }


def _rodape(meta: dict):
    def desenhar(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#6B7580"))
        canvas.drawString(2 * cm, 1.3 * cm, f"{meta['codigo']} - rev. {meta['revisao']}")
        canvas.drawCentredString(A4[0] / 2, 1.3 * cm, meta["titulo"])
        canvas.drawRightString(A4[0] - 2 * cm, 1.3 * cm, f"Pagina {canvas.getPageNumber()}")
        canvas.setStrokeColor(CINZA_CLARO)
        canvas.line(2 * cm, 1.7 * cm, A4[0] - 2 * cm, 1.7 * cm)
        canvas.restoreState()

    return desenhar


def _tabela(bloco: dict, est: dict) -> list:
    cabecalho = [Paragraph(f"<b>{c}</b>", est["celula_cab"]) for c in bloco["cabecalho"]]
    linhas = [[Paragraph(str(c), est["celula"]) for c in linha] for linha in bloco["linhas"]]
    largura_util = A4[0] - 4 * cm
    n = len(bloco["cabecalho"])
    pesos = bloco.get("pesos") or [1] * n
    total = sum(pesos)
    larguras = [largura_util * p / total for p in pesos]

    tabela = Table([cabecalho] + linhas, colWidths=larguras, repeatRows=1)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), CINZA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B9C0C7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos = [Spacer(1, 4), tabela]
    if bloco.get("legenda"):
        elementos.append(Spacer(1, 3))
        elementos.append(Paragraph(bloco["legenda"], est["legenda"]))
    else:
        elementos.append(Spacer(1, 8))
    return elementos


def _capa(meta: dict, est: dict) -> list:
    linhas = [
        ["Codigo do documento", meta["codigo"]],
        ["Revisao", meta["revisao"]],
        ["Equipamento", meta["equipamento"]],
        ["Area responsavel", meta["area"]],
        ["Vigencia a partir de", meta["vigencia"]],
    ]
    tabela = Table(
        [[Paragraph(f"<b>{a}</b>", est["celula"]), Paragraph(b, est["celula"])] for a, b in linhas],
        colWidths=[(A4[0] - 4 * cm) * 0.35, (A4[0] - 4 * cm) * 0.65],
    )
    tabela.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B9C0C7")),
                ("BACKGROUND", (0, 0), (0, -1), CINZA_CLARO),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [
        Paragraph(meta["titulo"], est["titulo"]),
        Spacer(1, 6),
        Paragraph(meta["subtitulo"], est["subtitulo"]),
        Spacer(1, 18),
        tabela,
        Spacer(1, 16),
    ]


def gerar(documento: dict, saida: Path) -> dict:
    est = _estilos()
    meta = documento["meta"]
    caminho = saida / meta["arquivo"]

    doc = SimpleDocTemplate(
        str(caminho),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.2 * cm,
        title=meta["titulo"],
        author=meta["area"],
        subject=meta["equipamento"],
    )

    fluxo: list = _capa(meta, est)
    for bloco in documento["blocos"]:
        tipo = bloco["tipo"]
        if tipo == "h1":
            fluxo.append(Paragraph(bloco["texto"], est["h1"]))
        elif tipo == "h2":
            fluxo.append(Paragraph(bloco["texto"], est["h2"]))
        elif tipo == "p":
            fluxo.append(Paragraph(bloco["texto"], est["p"]))
        elif tipo == "lista":
            for item in bloco["itens"]:
                fluxo.append(Paragraph(f"&bull;&nbsp;&nbsp;{item}", est["p"]))
        elif tipo == "tabela":
            fluxo.append(KeepTogether(_tabela(bloco, est)))
        elif tipo == "quebra":
            fluxo.append(PageBreak())
        else:  # pragma: no cover - erro de conteudo, nao de runtime
            raise ValueError(f"bloco desconhecido: {tipo}")

    rodape = _rodape(meta)
    doc.build(fluxo, onFirstPage=rodape, onLaterPages=rodape)
    return {**meta, "paginas": doc.page}


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera os PDFs da base de conhecimento.")
    parser.add_argument("--saida", default="data/pdfs", help="pasta de destino dos PDFs")
    args = parser.parse_args()

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    manifesto = []
    for documento in DOCUMENTOS:
        info = gerar(documento, saida)
        manifesto.append(info)
        print(f"  gerado: {info['arquivo']}  ({info['paginas']} paginas)")

    destino_manifesto = saida / "manifesto.json"
    destino_manifesto.write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{len(manifesto)} documentos em {saida}/ e metadados em {destino_manifesto}")


if __name__ == "__main__":
    main()
