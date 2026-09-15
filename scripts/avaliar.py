"""Mede a qualidade da recuperacao.

Sem isto o projeto e uma demonstracao que funcionou uma vez. Com isto da para
responder "o hibrido melhora mesmo?" com numero em vez de opiniao.

Metricas:
  recall@k - em quantas perguntas o trecho certo apareceu entre os k primeiros.
             E a metrica que importa: se o trecho certo nao entra no contexto,
             nenhum modelo de texto consegue acertar a resposta depois.
  MRR      - media de 1/posicao do primeiro acerto. Penaliza o trecho certo que
             aparece so na quinta posicao, porque ele compete por espaco de
             contexto com quatro trechos irrelevantes.

Uso:
    python scripts/avaliar.py                       # as tres estrategias
    python scripts/avaliar.py --comparar-camadas    # filtro e reranker sobre a hibrida
    python scripts/avaliar.py --conferir            # so checa o conjunto de avaliacao
    python scripts/avaliar.py --salvar relatorios/avaliacao.json

    # trocar o cross-encoder e reordenar menos candidatos sao as duas alavancas
    # do custo do reranker; ficam na linha de comando para a comparacao ser
    # repetivel sem editar o .env
    python scripts/avaliar.py --comparar-camadas
        --reranker-model cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
        --candidatos-reranker 10
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from rag import banco, embeddings  # noqa: E402
from rag.busca import buscar  # noqa: E402
from rag.config import obter_config  # noqa: E402


def normalizar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.lower().split())


def acertou(trecho: dict, esperado: dict) -> bool:
    if trecho["arquivo"] != esperado["arquivo_esperado"]:
        return False
    corpo = normalizar(trecho["texto"])
    return any(normalizar(e) in corpo for e in esperado["evidencias"])


def aquecer(reranker: bool) -> None:
    """Carrega os modelos antes de comecar a cronometrar.

    Sem isto, a primeira estrategia medida paga o carregamento do modelo de
    embeddings (mais de um segundo) e a tabela de latencia diz que a estrategia
    da primeira linha e 40x mais lenta que as outras - o que e falso e ja
    apareceu na primeira medicao deste projeto.
    """
    embeddings.vetorizar_pergunta("aquecimento do modelo")
    if reranker:
        from rag.reranker import _modelo

        _modelo()


def avaliar_configuracao(
    perguntas: list[dict],
    rotulo: str,
    estrategia: str,
    top_k: int,
    filtro_equipamento: bool = False,
    reordenar: bool = False,
) -> dict:
    posicoes: list[int | None] = []
    latencias: list[float] = []
    detalhes: list[dict] = []
    perdidos_pelo_filtro = 0

    for item in perguntas:
        inicio = time.perf_counter()
        resultados = buscar(
            item["pergunta"],
            limite=top_k,
            estrategia=estrategia,
            filtrar_equipamento=filtro_equipamento,
            reordenar=reordenar,
        )
        latencias.append((time.perf_counter() - inicio) * 1000)

        posicao = next(
            (i for i, trecho in enumerate(resultados, start=1) if acertou(trecho, item)), None
        )
        # Falha do filtro e diferente de falha do ranking: se o documento certo
        # nem aparece entre os candidatos, o filtro o excluiu da base. E o modo
        # de falhar mais caro desta camada, entao vale contar separado.
        if (
            posicao is None
            and filtro_equipamento
            and all(t["arquivo"] != item["arquivo_esperado"] for t in resultados)
        ):
            perdidos_pelo_filtro += 1

        posicoes.append(posicao)
        detalhes.append(
            {
                "id": item["id"],
                "pergunta": item["pergunta"],
                "posicao": posicao,
                "recuperado_1": (
                    f"{resultados[0]['arquivo']} pag. {resultados[0]['pagina_inicial']}"
                    if resultados
                    else None
                ),
            }
        )

    total = len(perguntas)

    def recall(k: int) -> float:
        return sum(1 for p in posicoes if p is not None and p <= k) / total if total else 0.0

    mrr = sum(1 / p for p in posicoes if p) / total if total else 0.0
    ordenadas = sorted(latencias)
    return {
        "rotulo": rotulo,
        "estrategia": estrategia,
        "filtro_equipamento": filtro_equipamento,
        "reranker": reordenar,
        "perguntas": total,
        "recall@1": recall(1),
        "recall@3": recall(3),
        "recall@5": recall(5),
        "mrr": mrr,
        "latencia_media_ms": statistics.mean(latencias) if latencias else 0.0,
        "latencia_p95_ms": (
            ordenadas[min(int(len(ordenadas) * 0.95), len(ordenadas) - 1)] if ordenadas else 0.0
        ),
        "perdidos_pelo_filtro": perdidos_pelo_filtro,
        "falhas": [d for d in detalhes if d["posicao"] is None],
        "detalhes": detalhes,
    }


def avaliar_recusa(negativas: list[dict], positivas: list[dict]) -> dict:
    """Pergunta sem resposta na base: quao confiante a recuperacao fica?

    Sem modelo de texto configurado nao da para medir se a resposta final recusa.
    Da para medir o que sustentaria essa recusa: a pontuacao do melhor trecho
    recuperado. Se ela nao se separar da pontuacao das perguntas com resposta,
    nenhum limiar vai distinguir as duas e a recusa depende inteiramente do
    prompt.

    A medicao usa a estrategia semantica de proposito. A pontuacao da hibrida e
    RRF, que soma 1/(60+posicao): o primeiro colocado pontua praticamente o
    mesmo tenha a busca encontrado a resposta ou lixo. RRF ordena bem e nao
    serve como confianca - usa-la aqui daria a impressao de que as duas
    populacoes sao identicas quando o que e identico e a formula.
    """

    def melhor(pergunta: str) -> float:
        # Filtro e reranker fixados: esta medicao compara duas populacoes de
        # pontuacao e precisa dar o mesmo numero independente do que estiver
        # ligado no .env.
        resultados = buscar(
            pergunta,
            limite=1,
            estrategia="semantica",
            filtrar_equipamento=False,
            reordenar=False,
        )
        return float(resultados[0]["pontuacao"]) if resultados else 0.0

    controles = [
        {"id": i["id"], "pergunta": i["pergunta"], "melhor_pontuacao": melhor(i["pergunta"])}
        for i in negativas
    ]
    com_resposta = [melhor(i["pergunta"]) for i in positivas]
    return {
        "estrategia": "semantica",
        "controles": controles,
        "com_resposta_media": statistics.mean(com_resposta) if com_resposta else 0.0,
        "com_resposta_minima": min(com_resposta) if com_resposta else 0.0,
        "controles_maxima": max((c["melhor_pontuacao"] for c in controles), default=0.0),
    }


def conferir_cobertura(caminho_perguntas: Path) -> int:
    """Toda evidencia do conjunto existe em algum trecho gerado?

    Roda so sobre os PDFs, sem banco: uma evidencia que nao existe em trecho
    nenhum transforma a pergunta em falha permanente, e a metrica passaria a
    medir um erro de digitacao em vez da qualidade da busca.
    """
    from rag.chunking import dividir
    from rag.extracao import extrair, listar_pdfs

    config = obter_config()
    por_arquivo: dict[str, list[str]] = {}
    for caminho in listar_pdfs(config.pasta_pdfs):
        documento = extrair(caminho)
        trechos = dividir(
            documento,
            alvo_chars=config.chunk_alvo_chars,
            overlap_chars=config.chunk_overlap_chars,
        )
        por_arquivo[caminho.name] = [normalizar(t.texto) for t in trechos]

    dados = json.loads(caminho_perguntas.read_text(encoding="utf-8"))
    problemas = 0
    for item in dados["perguntas"]:
        if not item["arquivo_esperado"]:
            continue
        corpos = por_arquivo.get(item["arquivo_esperado"])
        if corpos is None:
            print(f"  {item['id']}: arquivo {item['arquivo_esperado']} nao esta em data/pdfs")
            problemas += 1
            continue
        for evidencia in item["evidencias"]:
            if not any(normalizar(evidencia) in corpo for corpo in corpos):
                print(f"  {item['id']}: evidencia {evidencia!r} nao existe em trecho nenhum")
                problemas += 1

    total = sum(1 for i in dados["perguntas"] if i["arquivo_esperado"])
    if problemas:
        print(f"\n{problemas} problema(s) em {total} perguntas com resposta na base")
    else:
        print(f"todas as evidencias das {total} perguntas existem em algum trecho gerado")
    return problemas


def imprimir_tabela(relatorios: list[dict]) -> None:
    largura = max(len(r["rotulo"]) for r in relatorios)
    cabecalho = (
        f"{'configuracao':<{largura}} {'recall@1':>9} {'recall@3':>9} {'recall@5':>9} "
        f"{'MRR':>7} {'ms medio':>9} {'ms p95':>8}"
    )
    print(cabecalho)
    print("-" * len(cabecalho))
    for r in relatorios:
        print(
            f"{r['rotulo']:<{largura}} {r['recall@1']:>9.2f} {r['recall@3']:>9.2f} "
            f"{r['recall@5']:>9.2f} {r['mrr']:>7.2f} {r['latencia_media_ms']:>9.0f} "
            f"{r['latencia_p95_ms']:>8.0f}"
        )


def main() -> None:
    config = obter_config()
    parser = argparse.ArgumentParser(description="Avalia a recuperacao do indice atual.")
    parser.add_argument("--estrategias", nargs="+", default=["hibrida", "semantica", "textual"])
    parser.add_argument("--top-k", type=int, default=max(config.top_k, 5))
    parser.add_argument("--arquivo", default=str(config.pasta_avaliacao / "perguntas.json"))
    parser.add_argument("--salvar", default=None, help="caminho para gravar o relatorio em JSON")
    parser.add_argument(
        "--comparar-camadas",
        action="store_true",
        help="mede a hibrida com e sem filtro por equipamento e com e sem reranker",
    )
    parser.add_argument(
        "--conferir",
        action="store_true",
        help="so confere se as evidencias do conjunto existem nos trechos gerados",
    )
    parser.add_argument(
        "--reranker-model",
        default=None,
        help="cross-encoder a usar nesta medicao, sobrescrevendo o do .env",
    )
    parser.add_argument(
        "--candidatos-reranker",
        type=int,
        default=None,
        help="quantos candidatos o cross-encoder reordena (padrao: o do .env)",
    )
    args = parser.parse_args()

    # A config e um singleton em cache; sobrescrever os campos aqui e o que faz
    # a flag valer para busca.py e reranker.py sem passar o modelo por cinco
    # assinaturas de funcao so para chegar ao unico lugar que o usa.
    if args.reranker_model:
        config.reranker_model = args.reranker_model
    if args.candidatos_reranker:
        config.candidatos_reranker = args.candidatos_reranker

    caminho_perguntas = Path(args.arquivo)
    if args.conferir:
        sys.exit(1 if conferir_cobertura(caminho_perguntas) else 0)

    dados = json.loads(caminho_perguntas.read_text(encoding="utf-8"))
    todas = dados["perguntas"]
    positivas = [p for p in todas if p["arquivo_esperado"]]
    negativas = [p for p in todas if not p["arquivo_esperado"]]

    if args.comparar_camadas:
        configuracoes = [
            ("hibrida", "hibrida", False, False),
            ("hibrida+filtro", "hibrida", True, False),
            ("hibrida+reranker", "hibrida", False, True),
            ("hibrida+filtro+rerank", "hibrida", True, True),
        ]
    else:
        configuracoes = [(e, e, False, False) for e in args.estrategias]

    print(
        f"backend: {banco.nome_backend()} | modelo: {config.embedding_model} | "
        f"top_k: {args.top_k}"
    )
    if any(c[3] for c in configuracoes):
        print(
            f"reranker: {config.reranker_model} sobre {config.candidatos_reranker} candidatos"
        )
    print(
        f"Avaliando {len(positivas)} perguntas com resposta na base "
        f"(+{len(negativas)} de controle)\n"
    )

    aquecer(reranker=any(c[3] for c in configuracoes))

    relatorios = [
        avaliar_configuracao(positivas, rotulo, estrategia, args.top_k, filtro, rerank)
        for rotulo, estrategia, filtro, rerank in configuracoes
    ]
    imprimir_tabela(relatorios)

    for r in relatorios:
        if r["perdidos_pelo_filtro"]:
            print(
                f"\naviso: em '{r['rotulo']}', {r['perdidos_pelo_filtro']} pergunta(s) "
                f"perderam o documento certo por causa do filtro de equipamento"
            )

    for r in relatorios:
        if r["falhas"]:
            print(f"\nfalhas em '{r['rotulo']}':")
            for falha in r["falhas"]:
                print(f"  {falha['id']}: {falha['pergunta']}")
                print(f"        1o resultado: {falha['recuperado_1']}")

    recusa = avaliar_recusa(negativas, positivas)
    if recusa["controles"]:
        print(
            "\nperguntas de controle - a recuperacao sempre devolve algo, entao a recusa\n"
            "depende do prompt. Similaridade de cosseno do melhor trecho (busca semantica):"
        )
        for controle in recusa["controles"]:
            print(f"  {controle['id']}: {controle['melhor_pontuacao']:.4f}  {controle['pergunta']}")
        print(
            f"  perguntas com resposta na base: media {recusa['com_resposta_media']:.4f}, "
            f"minima {recusa['com_resposta_minima']:.4f}"
        )
        margem = recusa["com_resposta_minima"] - recusa["controles_maxima"]
        print(
            f"  separacao entre a pior com resposta e a melhor de controle: {margem:+.4f} "
            + ("(um limiar separaria as duas)" if margem > 0 else "(nenhum limiar separa as duas)")
        )

    if args.salvar:
        destino = Path(args.salvar)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(
                {
                    "backend": banco.nome_backend(),
                    "modelo_embeddings": config.embedding_model,
                    "modelo_reranker": config.reranker_model,
                    "top_k": args.top_k,
                    "relatorios": relatorios,
                    "recusa": recusa,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nrelatorio salvo em {destino}")


if __name__ == "__main__":
    main()
