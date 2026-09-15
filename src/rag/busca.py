"""Etapa de recuperacao: pergunta -> trechos candidatos.

Tres estrategias, porque a comparacao entre elas e o que justifica a escolha:

* semantica - busca por vetor. Entende sinonimo e parafrase ("trocar o filtro"
  x "substituicao do elemento filtrante"), mas trata codigos de peca como
  quase identicos entre si: FH-P5501 e FH-P5502 ficam a milimetros um do outro
  no espaco vetorial.
* textual - busca por palavra-chave do proprio banco. Acerta o codigo exato
  e erra quando a pergunta nao repete as palavras do documento.
* hibrida - funde as duas listas por posicao (RRF). E o padrao do projeto, e o
  script de avaliacao mede o ganho em relacao as outras duas.

Duas camadas opcionais, ambas medidas por `scripts/avaliar.py` antes de virarem
padrao:

* filtro por equipamento - restringe a busca ao equipamento citado na pergunta.
* reranker - reordena os candidatos com um cross-encoder, que le pergunta e
  trecho juntos em vez de compara-los por vetores calculados separadamente.
"""
from __future__ import annotations

from typing import Any, Literal

from . import banco, embeddings, equipamentos
from .config import obter_config
from .formatacao import formatar_referencia  # noqa: F401  (reexportado por conveniencia)

Estrategia = Literal["hibrida", "semantica", "textual"]


def equipamentos_conhecidos() -> list[str]:
    return [
        documento["equipamento"]
        for documento in banco.estatisticas()["documentos"]
        if documento.get("equipamento")
    ]


def buscar(
    pergunta: str,
    limite: int | None = None,
    estrategia: Estrategia = "hibrida",
    equipamento: str | None = None,
    filtrar_equipamento: bool | None = None,
    reordenar: bool | None = None,
) -> list[dict[str, Any]]:
    """Recupera os trechos mais relevantes para a pergunta.

    `equipamento` fixa o filtro; `filtrar_equipamento` deixa o sistema inferir a
    partir do texto da pergunta. `reordenar` liga o cross-encoder. Os tres
    argumentos aceitam None para herdar o padrao do .env, de modo que a API, a
    CLI e a avaliacao consigam sobrescrever caso a caso sem duplicar a decisao.
    """
    config = obter_config()
    limite = limite or config.top_k
    if filtrar_equipamento is None:
        filtrar_equipamento = config.filtro_equipamento
    if reordenar is None:
        reordenar = config.reranker_habilitado

    alvos: list[str] | None = None
    if equipamento:
        alvos = [equipamento] + [
            e for e in equipamentos_conhecidos() if equipamentos.e_generico(e)
        ]
    elif filtrar_equipamento:
        alvos = equipamentos.alvos(pergunta, equipamentos_conhecidos())

    # Com reranker, a recuperacao precisa devolver mais candidatos do que o
    # usuario pediu: o ganho do cross-encoder vem justamente de promover um
    # trecho que estava abaixo do corte.
    limite_bruto = max(limite, config.candidatos_reranker) if reordenar else limite

    if estrategia == "textual":
        resultados = banco.buscar_textual(pergunta, limite_bruto, alvos)
    else:
        vetor = embeddings.vetorizar_pergunta(pergunta)
        if estrategia == "semantica":
            resultados = banco.buscar_semantica(vetor, limite_bruto, alvos)
        else:
            resultados = banco.buscar_hibrida(
                vetor, pergunta, limite_bruto, config.candidatos_por_via, alvos
            )

    if reordenar and resultados:
        from .reranker import reordenar_trechos

        resultados = reordenar_trechos(pergunta, resultados)

    return resultados[:limite]
