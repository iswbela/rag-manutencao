# -*- coding: utf-8 -*-
"""Conteudo dos documentos ficticios que formam a base de conhecimento.

Separado do renderizador (gerar_pdfs.py) de proposito: para acrescentar um
documento novo basta adicionar um dicionario nesta lista, sem tocar no codigo
de geracao. Tipos de bloco aceitos: h1, h2, p, lista, tabela, quebra.
"""

ESCAVADEIRA = {
    "meta": {
        "arquivo": "manual-escavadeira-mtx220.pdf",
        "codigo": "MAN-MTX220-PT",
        "revisao": "4",
        "titulo": "Manual de Manutencao - Escavadeira Hidraulica MTX-220",
        "subtitulo": "Manutencao preventiva, sistema hidraulico, motor e material rodante",
        "equipamento": "Escavadeira Hidraulica MTX-220",
        "area": "Engenharia de Manutencao",
        "vigencia": "2025-03-01",
    },
    "blocos": [
        {"tipo": "h1", "texto": "1. Identificacao do equipamento"},
        {
            "tipo": "p",
            "texto": "A escavadeira hidraulica MTX-220 e uma maquina de esteiras com peso "
            "operacional de 22.400 kg, motor diesel de 6 cilindros turboalimentado com 124 kW "
            "a 2.000 rpm e sistema hidraulico de duplo circuito com bombas de pistoes axiais de "
            "deslocamento variavel. A caçamba padrao tem capacidade de 1,05 m3.",
        },
        {
            "tipo": "p",
            "texto": "O numero de serie fica gravado na placa fixada na lateral direita da "
            "estrutura superior, atras da cabine. Sempre informe o numero de serie ao solicitar "
            "pecas: componentes do sistema hidraulico mudaram a partir da serie 22H-4100.",
        },
        {"tipo": "h1", "texto": "2. Seguranca antes de qualquer intervencao"},
        {
            "tipo": "lista",
            "itens": [
                "Estacione em piso plano, apoie a caçamba no solo e acione o freio de "
                "estacionamento antes de desligar o motor.",
                "Alivie a pressao residual do sistema hidraulico movimentando as alavancas de "
                "comando por 10 segundos com a chave na posicao ligada e o motor desligado.",
                "Execute o bloqueio e a etiquetagem de energia conforme o POP-LUB-004 e a norma "
                "interna de bloqueio antes de abrir qualquer linha pressurizada.",
                "Aguarde o resfriamento do motor e do oleo hidraulico ate abaixo de 40 graus C "
                "antes de drenar reservatorios.",
                "Nunca procure vazamentos com a mao: use um pedaco de papelao. Oleo sob pressao "
                "penetra na pele e causa lesao grave.",
            ],
        },
        {"tipo": "h1", "texto": "3. Plano de manutencao preventiva"},
        {
            "tipo": "p",
            "texto": "Os intervalos abaixo valem para operacao em condicao severa (mina a ceu "
            "aberto, ambiente com poeira em suspensao). Em operacao leve, os intervalos de troca "
            "de oleo podem ser estendidos em ate 25 por cento mediante analise de oleo favoravel "
            "em tres coletas consecutivas.",
        },
        {
            "tipo": "tabela",
            "cabecalho": ["Intervalo", "Componente", "Servico", "Codigo da peca"],
            "pesos": [0.16, 0.30, 0.34, 0.20],
            "linhas": [
                ["10 h / diario", "Nivel de oleo hidraulico", "Verificar e completar", "-"],
                ["10 h / diario", "Nivel de oleo do motor", "Verificar e completar", "-"],
                ["10 h / diario", "Pinos e buchas do equipamento frontal", "Engraxar", "-"],
                ["50 h", "Separador de agua do combustivel", "Drenar", "-"],
                ["250 h", "Oleo do motor e filtro", "Trocar", "FM-3120"],
                ["250 h", "Filtro de combustivel primario", "Trocar", "FC-2201"],
                ["500 h", "Filtro de combustivel secundario", "Trocar", "FC-2202"],
                ["500 h", "Elemento primario do filtro de ar", "Trocar", "AR-7745"],
                ["500 h", "Filtro hidraulico de retorno", "Trocar", "FH-P5501"],
                ["1.000 h", "Filtro hidraulico piloto", "Trocar", "FH-P5502"],
                ["1.000 h", "Elemento secundario do filtro de ar", "Trocar", "AR-7746"],
                ["1.000 h", "Oleo das reducoes finais", "Trocar", "-"],
                ["2.000 h", "Oleo hidraulico do reservatorio", "Trocar", "-"],
                ["2.000 h", "Oleo do giro (swing)", "Trocar", "-"],
                ["5.000 h", "Fluido de arrefecimento", "Trocar", "-"],
            ],
            "legenda": "Tabela 1 - Plano de manutencao preventiva da MTX-220 em condicao severa.",
        },
        {"tipo": "quebra"},
        {"tipo": "h1", "texto": "4. Sistema hidraulico"},
        {"tipo": "h2", "texto": "4.1 Oleo recomendado"},
        {
            "tipo": "p",
            "texto": "Utilize oleo hidraulico mineral ISO VG 46 com aditivo antidesgaste, indice "
            "de viscosidade minimo de 140 e nivel de limpeza ISO 4406 igual ou melhor que "
            "18/16/13. A capacidade total do sistema e de 210 litros, sendo 118 litros no "
            "reservatorio. Em operacao continua abaixo de 5 graus C, utilize ISO VG 32.",
        },
        {"tipo": "h2", "texto": "4.2 Troca do filtro hidraulico de retorno"},
        {
            "tipo": "p",
            "texto": "O filtro hidraulico de retorno FH-P5501 fica na parte superior do "
            "reservatorio, sob a tampa de inspecao do lado esquerdo. O intervalo padrao e de 500 "
            "horas, reduzido para 250 horas nas primeiras 1.000 horas de uma maquina nova ou apos "
            "qualquer troca de bomba ou motor hidraulico, por causa do residuo de montagem.",
        },
        {
            "tipo": "lista",
            "itens": [
                "Alivie a pressao do reservatorio girando lentamente o respiro RE-0410.",
                "Remova os oito parafusos da tampa de inspecao (torque de reaperto: 25 N.m).",
                "Retire o elemento antigo e inspecione o fundo do copo: particulas metalicas "
                "brilhantes indicam desgaste de bomba e exigem analise de oleo antes de religar "
                "o equipamento.",
                "Lubrifique o anel de vedacao novo com o proprio oleo hidraulico antes de montar.",
                "Complete o nivel, de partida no motor e mantenha em marcha lenta por 5 minutos "
                "antes de operar sob carga.",
            ],
        },
        {
            "tipo": "p",
            "texto": "O indicador de restricao do filtro acende quando a diferenca de pressao "
            "passa de 0,17 MPa. Leitura com oleo frio pode gerar alarme falso: confirme a "
            "indicacao com o oleo em temperatura de trabalho, entre 50 e 80 graus C.",
        },
        {"tipo": "h2", "texto": "4.3 Pressoes de referencia"},
        {
            "tipo": "tabela",
            "cabecalho": ["Circuito", "Pressao nominal", "Tolerancia", "Rotacao de teste"],
            "pesos": [0.34, 0.22, 0.22, 0.22],
            "linhas": [
                ["Principal (bomba 1 e 2)", "34,3 MPa", "+/- 1,0 MPa", "1.800 rpm"],
                ["Circuito piloto", "3,9 MPa", "+/- 0,3 MPa", "1.800 rpm"],
                ["Giro (swing)", "27,9 MPa", "+/- 1,0 MPa", "1.800 rpm"],
                ["Translacao", "34,3 MPa", "+/- 1,0 MPa", "1.800 rpm"],
            ],
            "legenda": "Tabela 2 - Pressoes medidas com oleo a 50 graus C.",
        },
        {"tipo": "h1", "texto": "5. Motor diesel"},
        {
            "tipo": "p",
            "texto": "Use oleo de motor grau SAE 15W-40 API CK-4. A capacidade do carter com "
            "filtro e de 24 litros. Troque o oleo e o filtro FM-3120 a cada 250 horas ou a cada "
            "seis meses, o que ocorrer primeiro. Oleo escurecido nao e criterio de troca; a "
            "decisao deve vir da analise de oleo descrita no POP-LUB-004.",
        },
        {
            "tipo": "p",
            "texto": "A folga de valvulas deve ser verificada a cada 2.000 horas com o motor "
            "frio: 0,25 mm na admissao e 0,51 mm no escape. O tensionamento da correia do "
            "alternador esta correto quando a deflexao fica entre 10 e 15 mm sob forca de 98 N "
            "no vao maior.",
        },
        {"tipo": "quebra"},
        {"tipo": "h1", "texto": "6. Material rodante"},
        {
            "tipo": "p",
            "texto": "A tensao da esteira e medida pela folga entre o terceiro rolete superior e "
            "a face interna do elo, com a maquina apoiada na lanca. O valor correto fica entre 320 "
            "e 340 mm. Esteira frouxa acelera o desgaste dos dentes da roda motriz; esteira "
            "excessivamente tensionada aumenta o consumo de combustivel e sobrecarrega os mancais.",
        },
        {
            "tipo": "tabela",
            "cabecalho": ["Componente", "Desgaste admissivel", "Criterio de troca"],
            "pesos": [0.32, 0.30, 0.38],
            "linhas": [
                ["Sapata da esteira", "ate 60 por cento da garra", "garra abaixo de 10 mm"],
                ["Rolete inferior", "ate 6 mm no diametro externo", "vazamento de oleo no mancal"],
                ["Roda motriz", "ate 50 por cento do perfil do dente", "dente com perfil pontiagudo"],
                ["Elo da esteira", "ate 5 mm de altura", "contato do elo com o rolete"],
            ],
            "legenda": "Tabela 3 - Criterios de substituicao do material rodante.",
        },
        {"tipo": "h1", "texto": "7. Diagnostico de falhas"},
        {
            "tipo": "tabela",
            "cabecalho": ["Sintoma", "Causa provavel", "Acao corretiva"],
            "pesos": [0.28, 0.34, 0.38],
            "linhas": [
                [
                    "Perda de forca em todos os movimentos",
                    "Pressao principal abaixo do nominal ou filtro de retorno saturado",
                    "Medir a pressao principal conforme a Tabela 2 e trocar o filtro FH-P5501",
                ],
                [
                    "Movimento lento apenas no giro",
                    "Valvula de alivio do giro desregulada ou freio do giro travando",
                    "Ajustar a valvula para 27,9 MPa e inspecionar o disco do freio de giro",
                ],
                [
                    "Oleo hidraulico com aspecto leitoso",
                    "Contaminacao por agua acima de 0,1 por cento",
                    "Coletar amostra, analisar e trocar o oleo se a agua passar do limite",
                ],
                [
                    "Superaquecimento do oleo hidraulico",
                    "Radiador obstruido ou valvula de alivio com passagem interna",
                    "Limpar o radiador e testar a valvula de alivio",
                ],
                [
                    "Motor sem forca com fumaca preta",
                    "Filtro de ar saturado ou turbocompressor com folga",
                    "Trocar os elementos AR-7745 e AR-7746 e medir a folga axial do turbo",
                ],
                [
                    "Partida dificil a frio",
                    "Filtro de combustivel primario parcialmente obstruido",
                    "Trocar o filtro FC-2201 e sangrar o sistema de combustivel",
                ],
            ],
            "legenda": "Tabela 4 - Diagnostico rapido para a equipe de campo.",
        },
        {"tipo": "h1", "texto": "8. Torques de aperto"},
        {
            "tipo": "tabela",
            "cabecalho": ["Uniao", "Torque", "Observacao"],
            "pesos": [0.40, 0.20, 0.40],
            "linhas": [
                ["Parafuso da sapata da esteira", "930 N.m", "reapertar apos 50 h de operacao"],
                ["Parafuso da roda motriz", "540 N.m", "aplicar trava quimica media"],
                ["Tampa do filtro hidraulico", "25 N.m", "aperto cruzado em duas etapas"],
                ["Bujao de dreno do carter", "70 N.m", "trocar a arruela a cada drenagem"],
                ["Parafuso do contrapeso", "1.100 N.m", "medicao com torquimetro calibrado"],
            ],
            "legenda": "Tabela 5 - Torques com rosca limpa e levemente lubrificada.",
        },
    ],
}

CAMINHAO = {
    "meta": {
        "arquivo": "manual-caminhao-cf450.pdf",
        "codigo": "MAN-CF450-PT",
        "revisao": "2",
        "titulo": "Manual de Manutencao - Caminhao Fora de Estrada CF-450",
        "subtitulo": "Transmissao, freios, suspensao e pneus",
        "equipamento": "Caminhao Fora de Estrada CF-450",
        "area": "Engenharia de Manutencao",
        "vigencia": "2025-06-15",
    },
    "blocos": [
        {"tipo": "h1", "texto": "1. Identificacao do equipamento"},
        {
            "tipo": "p",
            "texto": "O caminhao fora de estrada CF-450 tem capacidade nominal de carga de 45 "
            "toneladas, peso bruto operacional de 78.500 kg, motor diesel de 12 cilindros com 522 "
            "kW e transmissao automatica planetaria de sete marchas a frente e uma a re. O sistema "
            "de freios e do tipo disco molhado nas quatro rodas, com resfriamento forcado por oleo.",
        },
        {
            "tipo": "p",
            "texto": "Este manual cobre apenas a manutencao de campo. Intervencoes no conjunto "
            "planetario da transmissao e na caixa de reducao final exigem oficina central e "
            "ferramental especifico.",
        },
        {"tipo": "h1", "texto": "2. Plano de manutencao preventiva"},
        {
            "tipo": "tabela",
            "cabecalho": ["Intervalo", "Componente", "Servico", "Codigo da peca"],
            "pesos": [0.16, 0.30, 0.34, 0.20],
            "linhas": [
                ["Turno", "Pressao dos pneus", "Verificar a frio", "-"],
                ["Turno", "Nivel de oleo da transmissao", "Verificar com motor em marcha lenta", "-"],
                ["250 h", "Oleo do motor e filtro", "Trocar", "FM-4400"],
                ["250 h", "Filtro de ar primario", "Inspecionar e trocar se saturado", "AR-9930"],
                ["500 h", "Filtro de oleo da transmissao", "Trocar", "FT-8810"],
                ["500 h", "Filtro do circuito de freio", "Trocar", "FR-4402"],
                ["1.000 h", "Oleo da transmissao", "Trocar", "-"],
                ["1.000 h", "Carga de nitrogenio da suspensao", "Verificar e corrigir", "-"],
                ["2.000 h", "Oleo das reducoes finais", "Trocar", "-"],
                ["2.000 h", "Discos de freio", "Medir espessura", "-"],
                ["4.000 h", "Mangueiras do circuito de freio", "Substituir por tempo de uso", "-"],
            ],
            "legenda": "Tabela 1 - Plano preventivo do CF-450 em ciclo de mina.",
        },
        {"tipo": "h1", "texto": "3. Sistema de freios"},
        {
            "tipo": "p",
            "texto": "O freio de servico e a disco molhado, acionado hidraulicamente a 17,2 MPa. "
            "O oleo do circuito de freio e o mesmo da transmissao (TO-4 SAE 30) e nao pode ser "
            "substituido por fluido de freio automotivo em nenhuma hipotese: fluido a base de "
            "glicol ataca as vedacoes e provoca perda total de frenagem.",
        },
        {
            "tipo": "p",
            "texto": "O filtro do circuito de freio FR-4402 tem intervalo de 500 horas. Apos "
            "qualquer reparo que abra o circuito, faca a sangria pelos bujoes de cada roda na "
            "sequencia traseira direita, traseira esquerda, dianteira direita e dianteira esquerda, "
            "com o motor em marcha lenta.",
        },
        {
            "tipo": "tabela",
            "cabecalho": ["Verificacao", "Valor de referencia", "Limite de servico"],
            "pesos": [0.38, 0.31, 0.31],
            "linhas": [
                ["Espessura do disco de freio", "12,0 mm", "9,5 mm"],
                ["Pressao de acionamento", "17,2 MPa", "abaixo de 15,5 MPa reprova"],
                ["Temperatura do oleo de freio em rampa", "ate 110 graus C", "acima de 125 graus C"],
                ["Curso do pedal", "38 mm", "acima de 55 mm exige regulagem"],
                ["Teste de retencao em rampa de 15 por cento", "sem deslocamento por 60 s", "qualquer deslocamento reprova"],
            ],
            "legenda": "Tabela 2 - Parametros de aceitacao do sistema de freios.",
        },
        {"tipo": "quebra"},
        {"tipo": "h1", "texto": "4. Suspensao hidropneumatica"},
        {
            "tipo": "p",
            "texto": "Os quatro cilindros de suspensao trabalham com oleo e carga de nitrogenio. "
            "Use exclusivamente nitrogenio seco: ar comprimido introduz umidade e oxigenio, o que "
            "degrada as vedacoes e cria risco de combustao interna sob compressao.",
        },
        {
            "tipo": "tabela",
            "cabecalho": ["Posicao", "Pressao de nitrogenio (vazio)", "Curso exposto (vazio)"],
            "pesos": [0.30, 0.36, 0.34],
            "linhas": [
                ["Dianteira esquerda", "6,2 MPa", "95 a 105 mm"],
                ["Dianteira direita", "6,2 MPa", "95 a 105 mm"],
                ["Traseira esquerda", "4,8 MPa", "75 a 85 mm"],
                ["Traseira direita", "4,8 MPa", "75 a 85 mm"],
            ],
            "legenda": "Tabela 3 - Carga da suspensao com o caminhao vazio, em piso plano.",
        },
        {
            "tipo": "p",
            "texto": "Diferenca de curso exposto maior que 15 mm entre os dois lados do mesmo eixo "
            "indica perda de carga em um dos cilindros e deve ser corrigida antes do proximo turno. "
            "A verificacao completa da carga de nitrogenio tem intervalo de 1.000 horas.",
        },
        {"tipo": "h1", "texto": "5. Pneus e rodas"},
        {
            "tipo": "p",
            "texto": "Os pneus sao 24.00 R35 com indice TKPH minimo de 490. A pressao correta a "
            "frio e de 650 kPa nos dianteiros e 620 kPa nos traseiros. Meça sempre com o pneu frio: "
            "a pressao sobe cerca de 10 por cento em operacao e a correcao feita com pneu quente "
            "resulta em subpressao no turno seguinte.",
        },
        {
            "tipo": "lista",
            "itens": [
                "Subpressao de 20 por cento reduz a vida do pneu em cerca de 30 por cento e "
                "aumenta o consumo de combustivel.",
                "Aperte as porcas de roda em 900 N.m, em estrela, e reaperte apos 50 horas.",
                "Nunca complete pneu montado em aro de tres pecas sem antes conferir o "
                "travamento do anel.",
                "Registre a pressao de cada posicao no sistema para acompanhar a evolucao do TKPH "
                "por rota.",
            ],
        },
        {"tipo": "h1", "texto": "6. Diagnostico de falhas"},
        {
            "tipo": "tabela",
            "cabecalho": ["Sintoma", "Causa provavel", "Acao corretiva"],
            "pesos": [0.28, 0.34, 0.38],
            "linhas": [
                [
                    "Transmissao patinando sob carga",
                    "Nivel baixo de oleo ou filtro FT-8810 saturado",
                    "Completar o nivel com o motor em marcha lenta e trocar o filtro",
                ],
                [
                    "Frenagem fraca em rampa",
                    "Pressao de acionamento abaixo de 15,5 MPa ou disco no limite",
                    "Medir a pressao e a espessura do disco conforme a Tabela 2",
                ],
                [
                    "Caminhao inclinado para um lado com carga",
                    "Perda de carga de nitrogenio em um cilindro de suspensao",
                    "Medir o curso exposto dos dois lados e recarregar conforme a Tabela 3",
                ],
                [
                    "Oleo de freio acima de 125 graus C",
                    "Bomba de resfriamento com vazao baixa ou uso excessivo do freio de servico",
                    "Verificar a bomba e orientar o uso do retardador na descida",
                ],
                [
                    "Consumo de combustivel acima da media da frota",
                    "Subpressao dos pneus ou filtro de ar AR-9930 saturado",
                    "Calibrar a frio conforme a secao 5 e trocar o elemento de ar",
                ],
            ],
            "legenda": "Tabela 4 - Diagnostico rapido do CF-450.",
        },
    ],
}

BRITADOR = {
    "meta": {
        "arquivo": "manual-britador-bc900.pdf",
        "codigo": "MAN-BC900-PT",
        "revisao": "1",
        "titulo": "Manual de Manutencao - Britador Conico BC-900",
        "subtitulo": "Lubrificacao, ajuste de APF, revestimentos e protecao contra sobrecarga",
        "equipamento": "Britador Conico BC-900",
        "area": "Manutencao de Usina",
        "vigencia": "2025-01-20",
    },
    "blocos": [
        {"tipo": "h1", "texto": "1. Identificacao do equipamento"},
        {
            "tipo": "p",
            "texto": "O britador conico BC-900 opera como britagem secundaria, com motor eletrico "
            "de 250 kW, capacidade nominal de 320 t/h e abertura de alimentacao de 215 mm. O ajuste "
            "da abertura de posicao fechada, tratada neste manual pela sigla APF, e hidraulico e "
            "pode ser feito com o britador em operacao, sem carga.",
        },
        {"tipo": "h1", "texto": "2. Sistema de lubrificacao"},
        {
            "tipo": "p",
            "texto": "A lubrificacao e forcada, com reservatorio de 380 litros de oleo mineral "
            "ISO VG 150. O britador nao pode ser partido com o oleo abaixo de 16 graus C: abaixo "
            "disso o intertravamento bloqueia a partida e o aquecedor do reservatorio deve ser "
            "acionado. A temperatura de trabalho fica entre 38 e 54 graus C na linha de retorno.",
        },
        {
            "tipo": "tabela",
            "cabecalho": ["Intervalo", "Servico", "Referencia"],
            "pesos": [0.18, 0.52, 0.30],
            "linhas": [
                ["Turno", "Verificar temperatura e vazao de retorno do oleo", "38 a 54 graus C"],
                ["Turno", "Verificar pressao de lubrificacao", "0,10 a 0,25 MPa"],
                ["Semanal", "Drenar agua condensada do reservatorio", "-"],
                ["250 h", "Trocar o filtro de lubrificacao", "FL-6600"],
                ["500 h", "Coletar amostra de oleo para analise", "POP-LUB-004"],
                ["2.000 h", "Trocar o oleo do reservatorio", "ISO VG 150"],
                ["2.000 h", "Limpar o trocador de calor", "-"],
            ],
            "legenda": "Tabela 1 - Plano de lubrificacao do BC-900.",
        },
        {
            "tipo": "p",
            "texto": "Pressao de lubrificacao abaixo de 0,10 MPa desarma o britador por "
            "intertravamento. As causas mais comuns, em ordem de frequencia, sao filtro FL-6600 "
            "saturado, oleo frio demais e valvula de alivio desregulada.",
        },
        {"tipo": "h1", "texto": "3. Ajuste da abertura de posicao fechada (APF)"},
        {
            "tipo": "p",
            "texto": "A APF determina a granulometria do produto e o consumo de energia. Reduzir a "
            "APF aumenta a fracao fina e a potencia consumida; aumentar a APF eleva a vazao e "
            "engrossa o produto. O ajuste deve ser feito sempre com o britador vazio e girando.",
        },
        {
            "tipo": "tabela",
            "cabecalho": ["APF", "Produto P80 aproximado", "Vazao esperada", "Potencia tipica"],
            "pesos": [0.18, 0.30, 0.26, 0.26],
            "linhas": [
                ["16 mm", "19 mm", "215 t/h", "205 a 225 kW"],
                ["22 mm", "26 mm", "265 t/h", "190 a 210 kW"],
                ["28 mm", "33 mm", "320 t/h", "175 a 195 kW"],
                ["35 mm", "41 mm", "360 t/h", "160 a 180 kW"],
            ],
            "legenda": "Tabela 2 - Relacao entre APF, produto e consumo com minerio de indice de "
            "britabilidade medio.",
        },
        {
            "tipo": "p",
            "texto": "Calibre a APF a cada 200 horas e sempre apos a troca de revestimentos. O "
            "metodo aceito e o do chumbo: com o britador vazio e girando, introduza um corpo de "
            "chumbo pela camara, recolha e meça a espessura no ponto mais fino.",
        },
        {"tipo": "quebra"},
        {"tipo": "h1", "texto": "4. Revestimentos: manto e concavo"},
        {
            "tipo": "p",
            "texto": "O manto MT-1200-M e o concavo CV-1200-M sao de aco manganes de 18 por cento "
            "e devem ser substituidos sempre em conjunto. A vida tipica com minerio abrasivo fica "
            "entre 900 e 1.200 horas efetivas de britagem.",
        },
        {
            "tipo": "lista",
            "itens": [
                "Troque os revestimentos quando o desgaste atingir 70 por cento da espessura "
                "original ou quando a APF minima nao puder mais ser alcancada pelo ajuste "
                "hidraulico.",
                "Desgaste concentrado em um unico setor da camara indica segregacao na "
                "alimentacao: corrija a distribuicao antes de instalar o revestimento novo.",
                "O aperto do anel de fixacao do manto e de 2.400 N.m, aplicado em duas etapas.",
                "Apos a troca, opere por duas horas com carga reduzida para assentamento e "
                "reaperte o anel de fixacao.",
            ],
        },
        {"tipo": "h1", "texto": "5. Protecao contra sobrecarga"},
        {
            "tipo": "p",
            "texto": "Os cilindros hidraulicos de alivio protegem o britador contra material "
            "nao britavel. A pressao de acumulacao e de 8,5 MPa com nitrogenio a 5,5 MPa nos "
            "acumuladores. Disparos frequentes do alivio indicam sucata metalica na alimentacao ou "
            "camara sobrecarregada, e nao defeito do sistema hidraulico.",
        },
        {"tipo": "h1", "texto": "6. Diagnostico de falhas"},
        {
            "tipo": "tabela",
            "cabecalho": ["Sintoma", "Causa provavel", "Acao corretiva"],
            "pesos": [0.28, 0.34, 0.38],
            "linhas": [
                [
                    "Britador nao parte",
                    "Oleo de lubrificacao abaixo de 16 graus C ou pressao abaixo de 0,10 MPa",
                    "Acionar o aquecedor do reservatorio e trocar o filtro FL-6600",
                ],
                [
                    "Produto mais grosso que o especificado",
                    "Desgaste dos revestimentos ou APF descalibrada",
                    "Medir a APF pelo metodo do chumbo e avaliar a troca do conjunto MT-1200-M "
                    "e CV-1200-M",
                ],
                [
                    "Potencia oscilando acima de 225 kW",
                    "Camara sobrecarregada ou alimentacao segregada",
                    "Reduzir a alimentacao e corrigir a distribuicao no anel de alimentacao",
                ],
                [
                    "Alivio hidraulico disparando com frequencia",
                    "Material nao britavel entrando na camara",
                    "Inspecionar o detector de metais e a limpeza da correia de alimentacao",
                ],
                [
                    "Temperatura de retorno acima de 54 graus C",
                    "Trocador de calor sujo ou vazao de oleo reduzida",
                    "Limpar o trocador e verificar a bomba de lubrificacao",
                ],
            ],
            "legenda": "Tabela 3 - Diagnostico rapido do BC-900.",
        },
    ],
}

POP_LUBRIFICACAO = {
    "meta": {
        "arquivo": "pop-lubrificacao-analise-oleo.pdf",
        "codigo": "POP-LUB-004",
        "revisao": "6",
        "titulo": "Procedimento Operacional Padrao - Lubrificacao e Analise de Oleo",
        "subtitulo": "Coleta de amostras, limites de alerta e armazenagem de lubrificantes",
        "equipamento": "Aplicavel a toda a frota",
        "area": "Engenharia de Manutencao",
        "vigencia": "2025-08-01",
    },
    "blocos": [
        {"tipo": "h1", "texto": "1. Objetivo"},
        {
            "tipo": "p",
            "texto": "Padronizar a coleta de amostras de oleo, a interpretacao dos resultados de "
            "analise e a armazenagem de lubrificantes, de modo que a decisao de troca de oleo seja "
            "tomada por condicao e nao apenas por intervalo fixo.",
        },
        {"tipo": "h1", "texto": "2. Abrangencia e responsabilidades"},
        {
            "tipo": "tabela",
            "cabecalho": ["Funcao", "Responsabilidade"],
            "pesos": [0.30, 0.70],
            "linhas": [
                ["Lubrificador", "Coletar a amostra, identificar o frasco e registrar o horimetro"],
                ["Planejador de manutencao", "Programar a coleta junto com a preventiva do equipamento"],
                ["Analista de confiabilidade", "Interpretar o laudo e abrir a ordem corretiva quando houver alerta"],
                ["Supervisor de manutencao", "Autorizar a extensao de intervalo mediante tres laudos favoraveis"],
            ],
            "legenda": "Tabela 1 - Responsabilidades no processo de analise de oleo.",
        },
        {"tipo": "h1", "texto": "3. Coleta da amostra"},
        {
            "tipo": "p",
            "texto": "A amostra deve representar o oleo em circulacao. Colete sempre com o "
            "equipamento na temperatura de trabalho e logo apos a parada, nunca com o oleo "
            "decantado por horas.",
        },
        {
            "tipo": "lista",
            "itens": [
                "Limpe o ponto de coleta com pano sem fiapos antes de abrir a valvula.",
                "Descarte o primeiro meio litro que sair da valvula, que carrega residuo da linha.",
                "Encha o frasco ate tres quartos da capacidade e feche imediatamente.",
                "Nunca colete pelo bujao de dreno durante a drenagem completa: o material de fundo "
                "distorce a contagem de particulas.",
                "Identifique o frasco com tag do equipamento, componente, horimetro total, horas "
                "do oleo, data e se houve reposicao de oleo no periodo.",
                "Envie ao laboratorio em ate 48 horas da coleta.",
            ],
        },
        {"tipo": "h1", "texto": "4. Periodicidade das coletas"},
        {
            "tipo": "tabela",
            "cabecalho": ["Componente", "Intervalo de coleta", "Ensaios"],
            "pesos": [0.32, 0.26, 0.42],
            "linhas": [
                ["Motor diesel", "250 h", "Viscosidade, TBN, fuligem, metais de desgaste"],
                ["Sistema hidraulico", "500 h", "Viscosidade, contagem de particulas ISO 4406, agua"],
                ["Transmissao", "500 h", "Viscosidade, metais de desgaste, agua"],
                ["Reducoes finais", "1.000 h", "Metais de desgaste, agua"],
                ["Lubrificacao de britador", "500 h", "Viscosidade, contagem de particulas, agua"],
            ],
            "legenda": "Tabela 2 - Periodicidade minima de coleta por tipo de componente.",
        },
        {"tipo": "quebra"},
        {"tipo": "h1", "texto": "5. Limites de alerta e de acao"},
        {
            "tipo": "p",
            "texto": "Os limites abaixo sao referencias gerais da frota. O criterio mais confiavel "
            "nao e o valor absoluto e sim a tendencia: uma subida consistente em tres coletas "
            "seguidas exige investigacao mesmo com os valores ainda dentro do limite.",
        },
        {
            "tipo": "tabela",
            "cabecalho": ["Parametro", "Normal", "Alerta", "Acao imediata"],
            "pesos": [0.31, 0.23, 0.23, 0.23],
            "linhas": [
                ["Ferro (Fe)", "ate 50 ppm", "50 a 100 ppm", "acima de 100 ppm"],
                ["Silicio (Si)", "ate 15 ppm", "15 a 25 ppm", "acima de 25 ppm"],
                ["Cobre (Cu)", "ate 20 ppm", "20 a 40 ppm", "acima de 40 ppm"],
                ["Agua", "ate 0,05 por cento", "0,05 a 0,10 por cento", "acima de 0,10 por cento"],
                ["Variacao de viscosidade", "ate 5 por cento", "5 a 10 por cento", "acima de 10 por cento"],
                ["Contagem ISO 4406 (hidraulico)", "ate 18/16/13", "19/17/14", "20/18/15 ou pior"],
                ["TBN restante (motor)", "acima de 50 por cento", "30 a 50 por cento", "abaixo de 30 por cento"],
            ],
            "legenda": "Tabela 3 - Limites de alerta e de acao para analise de oleo.",
        },
        {
            "tipo": "p",
            "texto": "Silicio elevado quase sempre significa entrada de poeira: verifique o filtro "
            "de ar, as conexoes do sistema de admissao e as vedacoes do respiro antes de trocar o "
            "oleo. Trocar o oleo sem corrigir a entrada de contaminante apenas reinicia o ciclo.",
        },
        {"tipo": "h1", "texto": "6. Armazenagem de lubrificantes"},
        {
            "tipo": "lista",
            "itens": [
                "Guarde os tambores deitados sobre bercos ou em pe sob cobertura, nunca expostos "
                "a chuva: a variacao de temperatura suga agua pela tampa.",
                "Respeite a ordem de consumo pela data de fabricacao, com validade maxima de 24 "
                "meses para oleos minerais.",
                "Identifique bombas, funis e recipientes por tipo de oleo. Mistura de lubrificantes "
                "e uma das causas mais comuns de contaminacao evitavel.",
                "Filtre o oleo novo na transferencia: oleo novo de tambor costuma chegar em nivel "
                "de limpeza pior do que o exigido por sistemas hidraulicos.",
            ],
        },
        {"tipo": "h1", "texto": "7. Registros"},
        {
            "tipo": "p",
            "texto": "Todo laudo deve ser anexado a ordem de servico do componente e mantido por "
            "cinco anos. A extensao de intervalo de troca so pode ser autorizada com tres laudos "
            "consecutivos na faixa normal e sem tendencia de subida de metais de desgaste.",
        },
    ],
}

DOCUMENTOS = [ESCAVADEIRA, CAMINHAO, BRITADOR, POP_LUBRIFICACAO]
