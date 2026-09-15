"""Etapa 2 do pipeline: texto -> trechos indexaveis.

Por que nao cortar a cada N caracteres:

* O corte cego parte tabelas no meio. Como boa parte das perguntas de manutencao
  e respondida por uma linha de tabela ("de quanto em quanto tempo troco o
  filtro X"), perder a tabela e perder a resposta.
* O corte cego separa o titulo da secao do conteudo dela. O trecho fica sem
  contexto e o embedding perde o assunto.

O que este modulo faz:

1. Quebra o texto em blocos (paragrafo, item de lista, linha de tabela), nunca
   dentro de uma linha.
2. Detecta titulos numerados ("4.2 Troca do filtro hidraulico") e usa o titulo
   como fronteira natural e como metadado de cada trecho.
3. Agrupa blocos ate um tamanho alvo, com sobreposicao entre trechos vizinhos
   para que uma frase cortada na fronteira continue recuperavel.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .extracao import Documento

# Titulo numerado: "3. Plano de manutencao" ou "4.2 Troca do filtro".
# O "|" na linha desqualifica: e linha de tabela ("250 h | Trocar | FL-6600"),
# que tambem comeca com numero mas nao e titulo de secao.
_TITULO = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\.?\s+([A-Za-zÀ-ÿ][^|]{2,120})$")


@dataclass(frozen=True)
class Trecho:
    ordem: int
    texto: str
    secao: str
    pagina_inicial: int
    pagina_final: int


@dataclass(frozen=True)
class _Bloco:
    texto: str
    pagina: int
    titulo_nivel: int  # 0 = nao e titulo; 1 = "3."; 2 = "3.1"; ...


def _nivel_titulo(texto: str) -> int:
    if "\n" in texto or len(texto) > 140 or "|" in texto:
        return 0
    achado = _TITULO.match(texto.strip())
    if not achado:
        return 0
    return achado.group(1).count(".") + 1


def _blocos(documento: Documento) -> list[_Bloco]:
    blocos: list[_Bloco] = []
    for pagina in documento.paginas:
        for bruto in re.split(r"\n\s*\n", pagina.texto):
            texto = bruto.strip()
            if not texto:
                continue
            blocos.append(
                _Bloco(texto=texto, pagina=pagina.numero, titulo_nivel=_nivel_titulo(texto))
            )
    return blocos


def _quebrar_bloco_grande(bloco: _Bloco, alvo: int) -> list[_Bloco]:
    """Tabela maior que o alvo: quebra por linhas, nunca no meio de uma linha."""
    if len(bloco.texto) <= alvo:
        return [bloco]
    partes: list[_Bloco] = []
    atual: list[str] = []
    tamanho = 0
    for linha in bloco.texto.splitlines():
        if tamanho + len(linha) > alvo and atual:
            partes.append(_Bloco("\n".join(atual), bloco.pagina, 0))
            # repete a ultima linha como ponte entre as partes da tabela
            atual = [atual[-1]] if len(atual) > 1 else []
            tamanho = sum(len(x) for x in atual)
        atual.append(linha)
        tamanho += len(linha) + 1
    if atual:
        partes.append(_Bloco("\n".join(atual), bloco.pagina, 0))
    return partes


def _cauda(texto: str, limite: int) -> str:
    """Ultimos caracteres do trecho, cortados em fronteira de linha."""
    if limite <= 0 or len(texto) <= limite:
        return texto if limite > 0 else ""
    recorte = texto[-limite:]
    quebra = recorte.find("\n")
    return recorte[quebra + 1 :].strip() if quebra != -1 else recorte.strip()


def dividir(
    documento: Documento,
    alvo_chars: int = 1600,
    overlap_chars: int = 250,
) -> list[Trecho]:
    brutos = _blocos(documento)
    blocos: list[_Bloco] = []
    for bloco in brutos:
        blocos.extend(_quebrar_bloco_grande(bloco, alvo_chars))

    trechos: list[Trecho] = []
    buffer: list[_Bloco] = []
    tamanho = 0
    secao = ""
    secao_do_buffer = ""
    prefixo_overlap = ""

    def descarregar(com_overlap: bool) -> None:
        nonlocal buffer, tamanho, prefixo_overlap
        if not buffer:
            return
        corpo = "\n\n".join(b.texto for b in buffer)
        texto = f"{prefixo_overlap}\n\n{corpo}".strip() if prefixo_overlap else corpo
        paginas = [b.pagina for b in buffer]
        trechos.append(
            Trecho(
                ordem=len(trechos),
                texto=texto,
                secao=secao_do_buffer,
                pagina_inicial=min(paginas),
                pagina_final=max(paginas),
            )
        )
        prefixo_overlap = _cauda(corpo, overlap_chars) if com_overlap else ""
        buffer = []
        tamanho = 0

    minimo_para_fechar = alvo_chars * 0.4

    for bloco in blocos:
        if bloco.titulo_nivel == 1:
            # Titulo de primeiro nivel e fronteira semantica limpa: fecha sem
            # overlap. Secoes curtas seguidas ficam juntas de proposito - trecho
            # de duas linhas tem pouco sinal e polui o indice.
            if tamanho >= minimo_para_fechar:
                descarregar(com_overlap=False)
            secao = bloco.texto
        elif bloco.titulo_nivel >= 2:
            if tamanho > alvo_chars * 0.5:
                descarregar(com_overlap=True)
            secao = bloco.texto

        if not buffer:
            secao_do_buffer = secao

        if tamanho + len(bloco.texto) > alvo_chars and buffer:
            descarregar(com_overlap=True)
            secao_do_buffer = secao

        buffer.append(bloco)
        tamanho += len(bloco.texto) + 2

    descarregar(com_overlap=False)
    return _absorver_residuos(trechos)


def _absorver_residuos(trechos: list[Trecho], minimo: int = 120) -> list[Trecho]:
    """Junta sobras minusculas ao trecho anterior em vez de descartar.

    Descartar seria mais simples e ja custou caro uma vez: uma linha solta de
    tabela vira um trecho de 40 caracteres, e jogar fora essa linha significa
    jogar fora exatamente o dado que alguem vai perguntar.
    """
    resultado: list[Trecho] = []
    for trecho in trechos:
        if len(trecho.texto.strip()) < minimo and resultado:
            anterior = resultado[-1]
            resultado[-1] = Trecho(
                ordem=anterior.ordem,
                texto=f"{anterior.texto}\n\n{trecho.texto}",
                secao=anterior.secao or trecho.secao,
                pagina_inicial=anterior.pagina_inicial,
                pagina_final=max(anterior.pagina_final, trecho.pagina_final),
            )
        else:
            resultado.append(trecho)
    return [
        Trecho(
            ordem=indice,
            texto=t.texto,
            secao=t.secao,
            pagina_inicial=t.pagina_inicial,
            pagina_final=t.pagina_final,
        )
        for indice, t in enumerate(resultado)
    ]


def texto_para_embedding(titulo_documento: str, trecho: Trecho) -> str:
    """O vetor e calculado sobre o trecho mais o seu contexto.

    Um trecho que diz apenas "500 h | Filtro de retorno | Trocar | FH-P5501" nao
    menciona o equipamento em lugar nenhum. Sem o titulo do documento e da secao
    grudados no texto, ele nunca seria recuperado por uma pergunta que cita o
    equipamento pelo nome.
    """
    partes = [p for p in (titulo_documento, trecho.secao) if p]
    cabecalho = " > ".join(partes)
    return f"{cabecalho}\n{trecho.texto}" if cabecalho else trecho.texto
