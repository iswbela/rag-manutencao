"""API HTTP do assistente de manutencao.

Endpoints:
    GET  /saude       - estado do banco e se a geracao esta habilitada
    GET  /documentos  - o que esta indexado
    POST /buscar      - so recuperacao (funciona sem modelo de texto configurado)
    POST /perguntar   - recuperacao + resposta com citacao

/buscar existe separado de proposito: a qualidade de um sistema de RAG e
decidida na recuperacao, entao ela precisa ser inspecionavel sozinha, sem o
modelo de texto no meio do caminho.
"""
from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from . import banco, busca
from .config import obter_config
from .geracao import GeracaoIndisponivel, gerar
from .modelos import Consulta, Fonte, RespostaBusca, RespostaPergunta

app = FastAPI(
    title="Assistente de Manutencao (RAG)",
    description="Perguntas em linguagem natural sobre manuais e procedimentos de manutencao, "
    "com resposta ancorada nos documentos e citacao de pagina.",
    version="0.1.0",
)


@app.on_event("startup")
def carregar_modelos() -> None:
    """Paga o carregamento do cross-encoder na subida, e nao na primeira pergunta.

    Sem isto o primeiro usuario depois de cada deploy espera o download e o
    carregamento dos pesos, e o sintoma aparece como "a API as vezes trava".
    """
    from .reranker import aquecer

    aquecer()


def _recuperar(consulta: Consulta) -> list[dict]:
    return busca.buscar(
        consulta.pergunta,
        limite=consulta.top_k,
        estrategia=consulta.estrategia,
        equipamento=consulta.equipamento,
        filtrar_equipamento=consulta.filtrar_equipamento,
        reordenar=consulta.reordenar,
    )


def _para_fontes(trechos: list[dict]) -> list[Fonte]:
    return [
        Fonte(
            indice=indice,
            documento=trecho["titulo"],
            arquivo=trecho["arquivo"],
            codigo=trecho.get("codigo"),
            equipamento=trecho.get("equipamento"),
            secao=trecho.get("secao") or "",
            pagina_inicial=trecho["pagina_inicial"],
            pagina_final=trecho["pagina_final"],
            pontuacao=round(float(trecho["pontuacao"]), 6),
            pontuacao_recuperacao=(
                round(float(trecho["pontuacao_recuperacao"]), 6)
                if trecho.get("pontuacao_recuperacao") is not None
                else None
            ),
            trecho=trecho["texto"],
        )
        for indice, trecho in enumerate(trechos, start=1)
    ]


@app.get("/saude")
def saude() -> JSONResponse:
    config = obter_config()
    try:
        dados = banco.estatisticas()
        banco_ok, detalhe = True, None
    except Exception as erro:  # pragma: no cover - depende do ambiente
        dados, banco_ok, detalhe = {"total_trechos": 0}, False, str(erro)

    return JSONResponse(
        {
            "banco": "ok" if banco_ok else "indisponivel",
            "detalhe": detalhe,
            "backend": banco.nome_backend(),
            "trechos_indexados": dados.get("total_trechos", 0),
            "modelo_embeddings": config.embedding_model,
            "filtro_equipamento": config.filtro_equipamento,
            "reranker": config.reranker_model if config.reranker_habilitado else None,
            "geracao_habilitada": config.geracao_habilitada,
        }
    )


@app.get("/documentos")
def documentos() -> dict:
    try:
        return banco.estatisticas()
    except Exception as erro:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"banco indisponivel: {erro}") from erro


@app.post("/buscar", response_model=RespostaBusca)
def buscar(consulta: Consulta) -> RespostaBusca:
    inicio = time.perf_counter()
    try:
        trechos = _recuperar(consulta)
    except Exception as erro:  # pragma: no cover
        raise HTTPException(status_code=503, detail=str(erro)) from erro
    return RespostaBusca(
        pergunta=consulta.pergunta,
        estrategia=consulta.estrategia,
        latencia_ms=int((time.perf_counter() - inicio) * 1000),
        fontes=_para_fontes(trechos),
    )


@app.post("/perguntar", response_model=RespostaPergunta)
def perguntar(consulta: Consulta) -> RespostaPergunta:
    inicio = time.perf_counter()
    try:
        trechos = _recuperar(consulta)
    except Exception as erro:  # pragma: no cover
        raise HTTPException(status_code=503, detail=str(erro)) from erro
    latencia_busca = int((time.perf_counter() - inicio) * 1000)

    if not trechos:
        return RespostaPergunta(
            pergunta=consulta.pergunta,
            resposta="Nao encontrei essa informacao nos documentos indexados.",
            fontes=[],
            latencia_ms=latencia_busca,
            latencia_busca_ms=latencia_busca,
            latencia_geracao_ms=0,
            modelo="-",
        )

    try:
        saida = gerar(consulta.pergunta, trechos)
    except GeracaoIndisponivel as erro:
        raise HTTPException(status_code=503, detail=str(erro)) from erro
    except Exception as erro:  # pragma: no cover - falha do endpoint externo
        raise HTTPException(status_code=502, detail=f"falha na geracao: {erro}") from erro

    return RespostaPergunta(
        pergunta=consulta.pergunta,
        resposta=saida["texto"],
        fontes=_para_fontes(trechos),
        latencia_ms=int((time.perf_counter() - inicio) * 1000),
        latencia_busca_ms=latencia_busca,
        latencia_geracao_ms=saida["latencia_ms"],
        modelo=saida["modelo"],
        uso=saida["uso"],
    )
