"""Reordenacao dos candidatos por cross-encoder.

A diferenca em relacao ao embedding: o bi-encoder calcula o vetor da pergunta e
o do trecho separadamente e so depois os compara, o que o obriga a resumir o
trecho inteiro em um vetor antes de saber o que foi perguntado. O cross-encoder
le os dois juntos e devolve uma pontuacao de relevancia - e mais preciso pela
mesma razao que e mais caro: nao da para pre-calcular nada, cada par pergunta x
trecho e uma passada pelo modelo.

Por isso ele nao substitui a busca, reordena o resultado dela: o hibrido traz
`CANDIDATOS_RERANKER` trechos baratos e o cross-encoder gasta tempo so nesses.

O custo e real e precisa entrar na conta: a avaliacao mede recall@1 com e sem, e
a latencia media dos dois. Se o ganho de recall nao pagar a latencia na sua
base, deixe RERANKER_HABILITADO=false - o resto do sistema nao muda.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from .chunking import Trecho, texto_para_embedding
from .config import obter_config


@lru_cache
def _modelo():
    from sentence_transformers import CrossEncoder

    config = obter_config()
    return CrossEncoder(config.reranker_model, max_length=512)


def _texto_do_par(trecho: dict[str, Any]) -> str:
    """Mesmo contexto usado na indexacao: documento > secao > texto.

    Sem o cabecalho, um trecho que e so uma linha de tabela ("500 h | Filtro de
    retorno | FH-P5501") nao diz de qual maquina fala, e o cross-encoder o
    rejeitaria numa pergunta que cita o equipamento pelo nome.
    """
    return texto_para_embedding(
        trecho.get("titulo") or "",
        Trecho(
            ordem=0,
            texto=trecho["texto"],
            secao=trecho.get("secao") or "",
            pagina_inicial=trecho["pagina_inicial"],
            pagina_final=trecho["pagina_final"],
        ),
    )


def reordenar_trechos(pergunta: str, trechos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Devolve os mesmos trechos, reordenados, com a pontuacao do cross-encoder.

    A pontuacao original da recuperacao e preservada em `pontuacao_recuperacao`:
    sem ela nao da para investigar depois se o reranker promoveu ou rebaixou um
    trecho, que e a unica forma de saber se ele esta ajudando.
    """
    if len(trechos) < 2:
        return trechos

    pares = [(pergunta, _texto_do_par(t)) for t in trechos]
    pontuacoes = _modelo().predict(pares, show_progress_bar=False)

    enriquecidos = [
        {
            **trecho,
            "pontuacao_recuperacao": trecho.get("pontuacao"),
            "pontuacao": float(pontuacao),
        }
        for trecho, pontuacao in zip(trechos, pontuacoes)
    ]
    enriquecidos.sort(key=lambda t: t["pontuacao"], reverse=True)
    return enriquecidos


def aquecer() -> None:
    """Carrega o modelo agora em vez de na primeira pergunta.

    A primeira chamada baixa os pesos e paga o carregamento; num servico isso
    apareceria como uma unica requisicao absurdamente lenta. A API chama isto no
    start-up quando o reranker esta habilitado.
    """
    if obter_config().reranker_habilitado:
        _modelo()
