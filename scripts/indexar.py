"""Indexa os PDFs da base de conhecimento no banco vetorial.

Uso:
    python scripts/indexar.py                 # indexa o que mudou
    python scripts/indexar.py --recriar       # apaga tudo e indexa do zero
    python scripts/indexar.py --pasta outra/  # outra pasta de PDFs

Rode com --recriar sempre que mudar o modelo de embeddings ou a estrategia de
chunking: trechos antigos e novos nao sao comparaveis entre si.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag import banco  # noqa: E402
from rag.indexacao import indexar_pasta  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa PDFs no banco vetorial.")
    parser.add_argument("--pasta", default=None, help="pasta com os PDFs")
    parser.add_argument("--recriar", action="store_true", help="apaga o indice antes de indexar")
    args = parser.parse_args()

    inicio = time.perf_counter()
    pasta = Path(args.pasta) if args.pasta else None
    resultados = indexar_pasta(pasta=pasta, recriar=args.recriar)

    estatisticas = banco.estatisticas()
    duracao = time.perf_counter() - inicio
    print(f"\n{len(resultados)} documento(s) processado(s) em {duracao:.1f}s")
    print(f"indice atual: {estatisticas['total_trechos']} trechos")
    for documento in estatisticas["documentos"]:
        print(
            f"  - {documento['arquivo']}: {documento['trechos']} trechos, "
            f"{documento['paginas']} paginas"
        )


if __name__ == "__main__":
    main()
