"""O filtro por equipamento so ajuda se errar pouco: um filtro que escolhe a
maquina errada nao piora o ranking, ele apaga a resposta da base. Estes testes
cobrem os casos em que ele deve se recusar a escolher."""
from __future__ import annotations

from rag import equipamentos

FROTA = [
    "Escavadeira Hidraulica MTX-220",
    "Caminhao Fora de Estrada CF-450",
    "Britador Conico BC-900",
    "Aplicavel a toda a frota",
]


def test_reconhece_o_modelo_escrito_de_varias_formas():
    for texto in ("da MTX-220", "na mtx220", "na MTX 220"):
        pergunta = f"Qual o intervalo do filtro hidraulico {texto}?"
        assert equipamentos.inferir(pergunta, FROTA) == "Escavadeira Hidraulica MTX-220"


def test_reconhece_pelo_tipo_de_maquina():
    assert (
        equipamentos.inferir("Qual a pressao dos pneus do caminhao?", FROTA)
        == "Caminhao Fora de Estrada CF-450"
    )
    assert (
        equipamentos.inferir("Como ajustar a APF do britador?", FROTA)
        == "Britador Conico BC-900"
    )


def test_nao_escolhe_quando_a_pergunta_cita_duas_maquinas():
    pergunta = "O filtro da escavadeira serve no britador?"
    assert equipamentos.inferir(pergunta, FROTA) is None


def test_nao_escolhe_quando_a_pergunta_nao_cita_maquina():
    assert equipamentos.inferir("Como coletar amostra de oleo?", FROTA) is None


def test_numero_solto_nao_identifica_maquina():
    """'220' viria de MTX-220, mas numero solto em pergunta tecnica e valor, nao
    modelo. Filtrar por ele mandaria a pergunta para a maquina errada."""
    assert equipamentos.inferir("A pressao caiu para 220 bar, e normal?", FROTA) is None
    assert equipamentos.inferir("Aperto de 900 N.m vale para qual roda?", FROTA) is None


def test_termo_deixa_de_valer_quando_para_de_ser_exclusivo():
    """'Hidraulica' identifica a escavadeira so enquanto for a unica hidraulica
    da base. Entrando uma prensa hidraulica, o termo se anula sozinho - e o que
    evita que a lista de apelidos precise ser mantida na mao."""
    assert equipamentos.inferir("Falha na hidraulica", FROTA) == "Escavadeira Hidraulica MTX-220"
    com_prensa = FROTA + ["Prensa Hidraulica PR-300"]
    assert equipamentos.inferir("Falha na hidraulica", com_prensa) is None


def test_documento_da_frota_entra_junto_com_o_equipamento_escolhido():
    """O POP de lubrificacao responde perguntas sobre qualquer maquina. Um filtro
    estrito o esconderia justamente quando ele e a fonte certa."""
    alvos = equipamentos.alvos("Trocar o filtro da escavadeira MTX-220", FROTA)
    assert alvos == ["Escavadeira Hidraulica MTX-220", "Aplicavel a toda a frota"]


def test_sem_equipamento_identificado_nao_ha_filtro():
    assert equipamentos.alvos("Como armazenar tambores de oleo?", FROTA) is None


def test_generico_e_quem_nao_tem_codigo_de_modelo():
    assert equipamentos.e_generico("Aplicavel a toda a frota")
    assert not equipamentos.e_generico("Britador Conico BC-900")
