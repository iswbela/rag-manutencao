"""Consulta pela linha de comando, sem subir a API.

Uso:
    python scripts/perguntar.py "Quando trocar o filtro hidraulico de retorno?"
    python scripts/perguntar.py "..." --so-busca
    python scripts/perguntar.py "..." --estrategia semantica
    python scripts/perguntar.py "..." --filtro-equipamento --reranker
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag.busca import buscar  # noqa: E402
from rag.config import obter_config  # noqa: E402
from rag.formatacao import formatar_referencia  # noqa: E402
from rag.geracao import GeracaoIndisponivel, gerar  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Pergunta ao assistente de manutencao.")
    parser.add_argument("pergunta")
    parser.add_argument("--estrategia", default="hibrida",
                        choices=["hibrida", "semantica", "textual"])
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--so-busca", action="store_true", help="mostra so os trechos recuperados")
    parser.add_argument("--equipamento", default=None,
                        help="restringe a busca a um equipamento (ex.: 'Britador Conico BC-900')")
    parser.add_argument("--filtro-equipamento", action="store_true", default=None,
                        help="infere o equipamento pelo texto da pergunta")
    parser.add_argument("--reranker", action="store_true", default=None,
                        help="reordena os candidatos com o cross-encoder")
    args = parser.parse_args()

    inicio = time.perf_counter()
    trechos = buscar(
        args.pergunta,
        limite=args.top_k,
        estrategia=args.estrategia,
        equipamento=args.equipamento,
        filtrar_equipamento=args.filtro_equipamento,
        reordenar=args.reranker,
    )
    ms_busca = (time.perf_counter() - inicio) * 1000

    print(f"\nTrechos recuperados ({args.estrategia}, {ms_busca:.0f} ms):\n")
    for indice, trecho in enumerate(trechos, start=1):
        print(f"[{indice}] {trecho['titulo']} - {formatar_referencia(trecho)}")
        pontuacao = f"pontuacao: {trecho['pontuacao']:.4f}"
        if trecho.get("pontuacao_recuperacao") is not None:
            pontuacao += f" (busca: {trecho['pontuacao_recuperacao']:.4f})"
        print(f"    secao: {trecho['secao'] or '-'}  | {pontuacao}")
        primeira_linha = trecho["texto"].strip().splitlines()[0]
        print(f"    {primeira_linha[:110]}...\n")

    if args.so_busca or not trechos:
        return

    if not obter_config().geracao_habilitada:
        print("Geracao desabilitada (LLM_BASE_URL/LLM_MODEL vazios no .env). "
              "Rodando em modo somente-busca.")
        return

    try:
        saida = gerar(args.pergunta, trechos)
    except GeracaoIndisponivel as erro:
        print(f"Geracao indisponivel: {erro}")
        return

    print("-" * 78)
    print(saida["texto"])
    print("-" * 78)
    print(f"modelo: {saida['modelo']} | geracao: {saida['latencia_ms']} ms | uso: {saida['uso']}")


if __name__ == "__main__":
    main()
