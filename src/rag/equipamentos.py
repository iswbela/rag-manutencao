"""Descobre de qual equipamento a pergunta fala, para filtrar a busca.

Por que isso importa: com quatro manuais a busca ja confunde componentes de
nome parecido entre maquinas diferentes - "qual o torque do parafuso" existe na
escavadeira e no caminhao. Quando o tecnico diz de qual maquina esta falando,
usar essa informacao e mais barato e mais confiavel do que esperar que o
embedding resolva sozinho.

O modulo nao guarda nenhuma lista de equipamentos no codigo: ele deriva os
apelidos dos proprios valores gravados no banco. Cadastrar um equipamento novo
no manifesto passa a funcionar sem tocar aqui.

Regras, nesta ordem:

1. Um termo so vale como apelido se for exclusivo de um equipamento. "Hidraulica"
   aparece so na escavadeira, entao vale; se amanha entrar uma "Prensa
   Hidraulica", o termo deixa de ser exclusivo e e ignorado automaticamente.
2. Se a pergunta aponta para mais de um equipamento, nao filtra. Filtrar pelo
   "primeiro que apareceu" seria um chute, e um chute errado custa a resposta.
3. Documentos sem codigo de modelo no nome do equipamento ("Aplicavel a toda a
   frota") entram sempre. Um POP de lubrificacao responde perguntas sobre
   qualquer maquina, e um filtro estrito o esconderia exatamente quando ele e a
   fonte certa.

Sem dependencia de banco ou de rede: recebe a lista de equipamentos conhecidos
como argumento, para poder ser testado isoladamente.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Codigo de modelo: MTX-220, CF450, BC-900. E o que separa "a maquina tal" de
# um documento generico da frota.
_CODIGO = re.compile(r"\b[A-Za-z]{2,4}[- ]?\d{2,4}\b")
_TOKEN = re.compile(r"[0-9a-z]+")

# Termos genericos demais para identificar maquina, mesmo quando por acaso so
# aparecem em um equipamento da base atual.
_GENERICOS = {"manual", "de", "da", "do", "e", "a", "o", "para", "toda", "frota", "aplicavel"}


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def _tokens(texto: str) -> set[str]:
    """Tokens normalizados, com o codigo de modelo tambem na forma sem hifen.

    "MTX-220" vira {mtx, 220, mtx220}: o tecnico escreve das tres formas.
    """
    limpo = _sem_acento(texto).lower()
    tokens = {t for t in _TOKEN.findall(limpo) if len(t) >= 3 or t.isdigit()}
    for achado in _CODIGO.findall(limpo):
        tokens.add(_TOKEN.sub("", achado) or achado)
        tokens.add("".join(_TOKEN.findall(achado)))
    return {t for t in tokens if t not in _GENERICOS}


def e_generico(equipamento: str) -> bool:
    """Documento que vale para a frota toda, e nao para uma maquina especifica."""
    return not _CODIGO.search(equipamento or "")


def apelidos(conhecidos: list[str]) -> dict[str, str]:
    """Termo -> equipamento, so para termos exclusivos de um equipamento.

    Numeros soltos ficam de fora. "MTX-220" produziria tambem o apelido "220", e
    dai uma pergunta como "por que a pressao caiu para 220 bar" seria filtrada
    para a escavadeira. A forma juntada ("mtx220") ja cobre quem escreve o
    modelo, sem esse risco.
    """
    por_equipamento = {e: _tokens(e) for e in conhecidos if e and not e_generico(e)}
    frequencia = Counter(t for tokens in por_equipamento.values() for t in tokens)
    return {
        token: equipamento
        for equipamento, tokens in por_equipamento.items()
        for token in tokens
        if frequencia[token] == 1 and not token.isdigit()
    }


def inferir(pergunta: str, conhecidos: list[str]) -> str | None:
    """Equipamento citado na pergunta, ou None se nenhum ou mais de um."""
    indice = apelidos(conhecidos)
    achados = {indice[t] for t in _tokens(pergunta) if t in indice}
    return achados.pop() if len(achados) == 1 else None


def alvos(pergunta: str, conhecidos: list[str]) -> list[str] | None:
    """Lista para o filtro do backend: o equipamento citado + os genericos.

    None significa "sem filtro" - e o que acontece quando a pergunta nao cita
    maquina nenhuma, ou cita mais de uma.
    """
    escolhido = inferir(pergunta, conhecidos)
    if escolhido is None:
        return None
    return [escolhido] + [e for e in conhecidos if e and e_generico(e)]
