"""Etapa final: monta o prompt ancorado nos trechos e chama o modelo de texto.

O ponto central deste modulo e o grounding: o modelo e instruido a responder
somente com o que esta nos trechos recuperados e a recusar quando a informacao
nao estiver la. Isso reduz - nao elimina - a invencao de resposta. Por isso a
API sempre devolve as fontes junto: quem le a resposta precisa conseguir
conferir a pagina do manual.

A integracao usa o formato de requisicao /chat/completions, suportado pela
maioria dos serviços de inferencia e tambem por servidores locais. Nenhum
provedor fica gravado no codigo: base, chave e modelo vem do .env.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from .formatacao import formatar_referencia
from .config import obter_config

INSTRUCAO_SISTEMA = """Voce e um assistente tecnico de manutencao de equipamentos.

Regras:
1. Responda EXCLUSIVAMENTE com base nos trechos de documentacao fornecidos.
2. Se os trechos nao contiverem a resposta, responda exatamente com a frase:
   Nao encontrei essa informacao nos documentos indexados.
   Nesse caso nao complete com conhecimento proprio.
3. Cite a fonte de cada afirmacao usando o numero do trecho entre colchetes, por
   exemplo [1].
4. Preserve valores exatos: intervalos, pressoes, torques e codigos de peca devem
   ser copiados dos trechos sem arredondamento.
5. Seja direto. Responda em portugues do Brasil, em no maximo 8 linhas.
6. Se os trechos trouxerem informacao conflitante, aponte o conflito em vez de
   escolher um dos lados."""


class GeracaoIndisponivel(RuntimeError):
    """Nenhum endpoint de geracao configurado: o projeto roda em modo somente-busca."""


def montar_prompt(pergunta: str, trechos: list[dict[str, Any]]) -> str:
    blocos = []
    for indice, trecho in enumerate(trechos, start=1):
        cabecalho = f"[{indice}] {trecho['titulo']} - {formatar_referencia(trecho)}"
        if trecho.get("secao"):
            cabecalho += f" - secao: {trecho['secao']}"
        blocos.append(f"{cabecalho}\n{trecho['texto']}")
    contexto = "\n\n---\n\n".join(blocos)
    return (
        f"Trechos da documentacao:\n\n{contexto}\n\n"
        f"---\n\nPergunta do tecnico: {pergunta}\n\nResposta:"
    )


def gerar(pergunta: str, trechos: list[dict[str, Any]]) -> dict[str, Any]:
    config = obter_config()
    if not config.geracao_habilitada:
        raise GeracaoIndisponivel(
            "configure LLM_BASE_URL e LLM_MODEL no .env para habilitar a geracao de resposta"
        )

    corpo = {
        "model": config.llm_model,
        "temperature": config.llm_temperatura,
        "messages": [
            {"role": "system", "content": INSTRUCAO_SISTEMA},
            {"role": "user", "content": montar_prompt(pergunta, trechos)},
        ],
    }
    cabecalhos = {"Content-Type": "application/json"}
    if config.llm_api_key:
        cabecalhos["Authorization"] = f"Bearer {config.llm_api_key}"

    url = config.llm_base_url.rstrip("/") + "/chat/completions"
    inicio = time.perf_counter()
    with httpx.Client(timeout=config.llm_timeout_s) as cliente:
        resposta = cliente.post(url, json=corpo, headers=cabecalhos)
        resposta.raise_for_status()
        dados = resposta.json()
    latencia_ms = int((time.perf_counter() - inicio) * 1000)

    return {
        "texto": dados["choices"][0]["message"]["content"].strip(),
        "latencia_ms": latencia_ms,
        "uso": dados.get("usage", {}),
        "modelo": dados.get("model", config.llm_model),
    }
