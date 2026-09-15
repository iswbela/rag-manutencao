# Assistente de Manutenção (RAG)

Pergunta em linguagem natural sobre manuais e procedimentos de manutenção, com
resposta ancorada nos documentos e **citação da página**.

> *"De quanto em quanto tempo eu troco o filtro hidráulico de retorno da MTX-220?"*
>
> *"A cada 500 horas em condição severa, com o filtro FH-P5501. Nas primeiras
> 1.000 horas de uma máquina nova o intervalo cai para 250 horas. [1]"*
> `[1] MAN-MTX220-PT, pág. 2 — seção 3. Plano de manutenção preventiva`

O problema real: a informação existe, está em PDF, e o técnico em campo perde
tempo (ou desiste) procurando. Busca por palavra-chave não resolve porque quem
pergunta usa o vocabulário do dia a dia — "trocar o filtro" — e o manual usa o
vocabulário da engenharia — "substituição do elemento filtrante".

> Retomando o projeto depois de um tempo? Comece pelo [HANDOFF.md](HANDOFF.md):
> estado atual, o que ainda não foi executado e a ordem sugerida de continuação.

---

## Índice

- [Como funciona](#como-funciona)
- [Rodando o projeto](#rodando-o-projeto)
- [API](#api)
- [Avaliação](#avaliação)
- [Decisões técnicas](#decisões-técnicas)
- [O que não funcionou](#o-que-não-funcionou)
- [Limitações conhecidas](#limitações-conhecidas)
- [Próximos passos](#próximos-passos)
- [Estrutura do repositório](#estrutura-do-repositório)

---

## Como funciona

```
FASE OFFLINE (roda quando chega documento novo)

  PDF ──► extração ──► chunking ──► embeddings ──► índice
          (layout)     (por seção,   (modelo        (vetor + texto +
                        com overlap)  local)         metadados + índice textual)

                                        índice = SQLite (padrão, sem infra)
                                              ou Postgres + pgvector (produção)

FASE ONLINE (roda a cada pergunta)

  pergunta ──┬─► embedding ──► busca vetorial ──┐
             │                                  ├─► fusão RRF ──► candidatos ──┐
             └─► busca textual (BM25) ──────────┘                              │
                                                                               ▼
                                                          [filtro por equipamento]
                                                                               │
                                                               [reranker opcional]
                                                                               ▼
                    resposta + fontes ◄── modelo de texto ◄── prompt ancorado ◄─┘
```

As duas etapas entre colchetes são opcionais. O filtro vem ligado e o reranker
desligado — os dois padrões saíram da [medição](#camadas-opcionais), não de
preferência.

A recuperação é a parte que decide a qualidade do sistema: se o trecho certo não
entra no contexto, nenhum modelo de texto acerta a resposta depois. Por isso
`/buscar` existe separado de `/perguntar` — dá para inspecionar e medir a
recuperação sozinha.

## Rodando o projeto

Pré-requisito: Python 3.10+. Mais nada — o backend padrão é SQLite e os
embeddings rodam localmente. Docker só é necessário para usar o Postgres.

```bash
# 1. ambiente
python -m venv .venv
.venv\Scripts\activate          # Windows;  no Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 2. configuração
copy .env.example .env          # Windows;  no Linux/macOS: cp .env.example .env

# 3. base de conhecimento de exemplo (gera os PDFs)
python scripts/gerar_pdfs.py

# 4. indexação (a primeira execução baixa o modelo de embeddings, ~120 MB)
python scripts/indexar.py --recriar

# 5. pergunta pela linha de comando
python scripts/perguntar.py "Quando trocar o filtro hidraulico de retorno?"

# 6. ou suba a API
uvicorn rag.api:app --app-dir src --reload
# documentação interativa em http://localhost:8000/docs
```

Os passos 1 a 5 funcionam **sem nenhuma chave de API**: os embeddings rodam
localmente e o projeto opera em modo somente-busca. Para habilitar a resposta em
linguagem natural, preencha `LLM_BASE_URL`, `LLM_API_KEY` e `LLM_MODEL` no
`.env` com qualquer endpoint compatível com o formato `/chat/completions` —
serviço em nuvem com camada gratuita ou um servidor rodando na sua máquina.
Nenhum provedor está gravado no código.

### Onde o índice vive

`BACKEND` no `.env` escolhe entre dois backends que expõem a mesma interface:

| | `sqlite` (padrão) | `postgres` |
|---|---|---|
| Infraestrutura | nenhuma | `docker compose up -d` |
| Busca textual | FTS5 com BM25 | `tsvector` com dicionário de português |
| Busca vetorial | cosseno em numpy, força bruta | pgvector com índice HNSW |
| Escala confortável | dezenas de milhares de trechos | milhões |

A força bruta não é um atalho preguiçoso nesta escala: com poucos milhares de
vetores ela é mais rápida que um índice aproximado e, ao contrário dele, nunca
erra o vizinho mais próximo. O que ela não faz é crescer — daí o Postgres existir
como caminho de produção, atrás da mesma interface, para que trocar seja mudar
uma linha do `.env` e reindexar.

Uma diferença que vale saber ao comparar os dois: no Postgres o `plainto_tsquery`
liga os termos da pergunta com **E**, então uma pergunta longa costuma devolver
pouco na via textual; no SQLite os termos são ligados com **OU** e o BM25 ordena.
Os números abaixo são do backend SQLite.

### Base de conhecimento

Os quatro documentos em `data/pdfs/` são **fictícios**, gerados por
`scripts/gerar_pdfs.py`, e escritos no formato de manuais reais de manutenção de
equipamentos móveis de mina — seções numeradas, tabelas de intervalo, códigos de
peça e tabelas de diagnóstico:

| Documento | Código | Conteúdo |
|---|---|---|
| Escavadeira Hidráulica MTX-220 | `MAN-MTX220-PT` | plano preventivo, sistema hidráulico, motor, material rodante, torques |
| Caminhão Fora de Estrada CF-450 | `MAN-CF450-PT` | transmissão, freios a disco molhado, suspensão, pneus |
| Britador Cônico BC-900 | `MAN-BC900-PT` | lubrificação, ajuste de APF, revestimentos, sobrecarga |
| POP de Lubrificação e Análise de Óleo | `POP-LUB-004` | coleta de amostra, limites de alerta, armazenagem |

Para usar documentos próprios, basta colocar os PDFs em `data/pdfs/` e rodar
`python scripts/indexar.py`.

## API

| Método | Rota | Para que serve |
|---|---|---|
| `GET` | `/saude` | backend, modelo de embeddings, camadas ligadas, se a geração está habilitada |
| `GET` | `/documentos` | o que está indexado e quantos trechos por documento |
| `POST` | `/buscar` | só recuperação — funciona sem modelo de texto configurado |
| `POST` | `/perguntar` | recuperação + resposta com citação |

```bash
curl -X POST http://localhost:8000/perguntar ^
  -H "Content-Type: application/json" ^
  -d "{\"pergunta\": \"Qual a pressao correta dos pneus do CF-450?\"}"
```

A resposta sempre traz `fontes`, com documento, seção, página e o trecho exato
usado. Sem isso o sistema não é auditável e não deveria ser usado para decisão
de manutenção.

`/buscar` e `/perguntar` aceitam `equipamento`, `filtrar_equipamento` e
`reordenar` no corpo da requisição, sobrescrevendo o padrão do `.env` por
consulta. São exatamente os botões que se quer girar ao investigar uma resposta
ruim, sem reiniciar o serviço:

```bash
curl -X POST http://localhost:8000/buscar ^
  -H "Content-Type: application/json" ^
  -d "{\"pergunta\": \"Qual o torque do parafuso?\", \"equipamento\": \"Britador Conico BC-900\"}"
```

## Avaliação

`data/avaliacao/perguntas.json` tem 40 perguntas com resposta conhecida na base e
4 perguntas de controle cuja resposta correta é **admitir que não sabe**. Cada
pergunta declara o arquivo esperado e um trecho de evidência que precisa aparecer
no chunk recuperado. `python scripts/avaliar.py --conferir` verifica que toda
evidência existe em algum trecho gerado — sem isso, um erro de digitação no
conjunto viraria uma falha permanente e a métrica passaria a medir o erro.

### Estratégias de recuperação

```bash
python scripts/avaliar.py
```

| estratégia | recall@1 | recall@3 | recall@5 | MRR | ms médio | ms p95 |
|---|---|---|---|---|---|---|
| híbrida | 0,78 | 0,97 | 1,00 | 0,87 | 43 | 61 |
| semântica | 0,80 | 0,97 | 1,00 | 0,89 | 42 | 54 |
| textual | 0,65 | 0,93 | 0,95 | 0,79 | 5 | 8 |

> 40 perguntas, backend SQLite, `intfloat/multilingual-e5-small`, CPU.

O resultado honesto é que **a híbrida não venceu a semântica pura** neste
conjunto: 0,78 contra 0,80 no recall@1 é uma pergunta de diferença em 40, dentro
do ruído. O que a tabela sustenta é mais modesto e mais útil: a busca textual
sozinha é claramente pior (0,65), e a híbrida nunca fica abaixo da semântica a
partir do recall@3. Numa base fictícia de 22 trechos, onde quase toda pergunta
tem um trecho obviamente certo, sobra pouco espaço para a fusão mostrar valor —
ela paga em bases maiores e mais ambíguas, e o número para afirmar isso aqui
ainda não existe.

### Camadas opcionais

```bash
python scripts/avaliar.py --comparar-camadas --salvar relatorios/avaliacao.json
```

| configuração | recall@1 | recall@3 | MRR | ms médio | ms p95 |
|---|---|---|---|---|---|
| híbrida | 0,78 | 0,97 | 0,87 | 49 | 58 |
| híbrida + filtro por equipamento | 0,80 | 1,00 | 0,88 | 61 | 75 |
| híbrida + filtro + reranker | **0,97** | 1,00 | **0,99** | 2.314 | 2.936 |

> As três linhas são da **mesma execução**, com os padrões atuais. A latência
> oscila entre execuções (a híbrida ficou entre 43 e 61 ms nas medições desta
> rodada); comparar linhas de execuções diferentes numa tabela sobre latência
> daria diferenças que são ruído da máquina.

**O filtro por equipamento sai praticamente de graça**: +3 ms, recall@3 fecha em
1,00 e — o que mais importava — em nenhuma das 40 perguntas ele excluiu o
documento certo da base. O script conta esse caso separado (`perdidos_pelo_filtro`)
porque é o modo de falhar caro: filtro errado não piora o ranking, apaga a
resposta. Por isso `FILTRO_EQUIPAMENTO` vem ligado.

**O reranker é o maior ganho do projeto**: +19 pontos de recall@1, e MRR de 0,99
— em 39 das 40 perguntas o trecho certo vira o primeiro resultado. Mas chegar a
esse número exigiu desmontar duas suposições, e as duas estavam erradas.

#### Escolher o cross-encoder: o maior perdeu

| cross-encoder | parâmetros | recall@1 | MRR | ms médio |
|---|---|---|---|---|
| `BAAI/bge-reranker-base` | 278 M | 0,88 | 0,93 | 15.687 |
| `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | 118 M | **0,97** | **0,99** | 4.269 |

O modelo menor é mais preciso **e** 3,7x mais rápido. A explicação é o dado de
treino, não o tamanho: o mMiniLM foi treinado no mMARCO, que inclui português,
enquanto o `bge-reranker-base` é treinado sobretudo em chinês e inglês. Em um
projeto em português isso pesa mais que contagem de parâmetros.

#### Quantos candidatos reordenar: 20 era desperdício

| candidatos reordenados | recall@1 | MRR | ms médio |
|---|---|---|---|
| 20 | 0,97 | 0,99 | 4.269 |
| 10 *(padrão)* | 0,97 | 0,99 | 2.303 |
| 5 | 0,97 | 0,99 | 1.053 |

Recall idêntico nos três, latência 4x menor. O motivo está na primeira tabela:
o **recall@5 da híbrida já é 1,00**, ou seja, o trecho certo sempre está entre os
cinco primeiros. O cross-encoder não precisa resgatar nada de longe — só precisa
acertar a ordem do que a busca barata já trouxe. Reordenar 20 era pagar quatro
vezes para reclassificar quinze candidatos que nunca iam ganhar.

Esse resultado **não generaliza para uma base grande**: recall@5 igual a 1,00 é
propriedade desta base de 22 trechos. Em base maior o trecho certo vai cair fora
do top-5 e mais candidatos passam a valer.

O padrão do projeto é 10, e não os 5 que a medição aponta como ótimo aqui. O
motivo não é folga por precaução: com `CANDIDATOS_RERANKER` igual ao `TOP_K`, o
cross-encoder só consegue reordenar o que já ia ser devolvido, e perde a única
coisa que ele faz melhor que a busca barata — promover um trecho que estava
abaixo do corte. Nesta base nada precisou ser promovido; em qualquer base maior,
vai precisar. A regra é subir junto com a base, medindo.

#### Por que o reranker ainda vem desligado

No ajuste padrão ele custa cerca de 2,3 s por pergunta em CPU, contra 61 ms sem
ele, e baixa 470 MB no primeiro uso. É um preço defensável para quem vai somar
uma chamada de modelo de texto em seguida — e caro demais para ser imposto a
quem clonou o repositório para olhar. `RERANKER_HABILITADO=true` no `.env` liga;
`CANDIDATOS_RERANKER=5` derruba para cerca de 1 s sem perder recall nesta base.

O script também lista as perguntas em que a recuperação falhou — é a lista de
trabalho para a próxima iteração de chunking.

### Perguntas de controle: a recusa não vem de um limiar

As 4 perguntas de controle não têm resposta na base. Duas são distantes do
domínio, duas são próximas de propósito — um equipamento que não existe na base
(`PF-700`) e um sistema que não existe no manual de um equipamento que existe
(ar condicionado da MTX-220).

| pergunta de controle | similaridade do melhor trecho |
|---|---|
| N01 — capacidade do helicóptero de resgate | 0,8182 |
| N02 — salário do operador | 0,8280 |
| N03 — filtro de ar da perfuratriz PF-700 | 0,8535 |
| N04 — ar condicionado da cabine da MTX-220 | **0,8733** |

Para comparar, as 40 perguntas **com** resposta na base ficam em 0,8758 de média
e **0,8442 no pior caso**. Ou seja: a pior pergunta respondível pontua *abaixo*
de duas perguntas sem resposta. As populações se sobrepõem, e nenhum limiar de
similaridade separa as duas.

Isso descarta uma ideia que parece boa — "se a pontuação for baixa, recuse" — e
deixa a recusa inteiramente por conta do prompt e da instrução de *grounding*.
É também o motivo de a API sempre devolver as fontes: quem lê a resposta precisa
conseguir conferir a página.

## Decisões técnicas

**Por que RAG e não fine-tuning.** Ajustar um modelo ensina estilo e formato, não
fatos confiáveis, e precisa ser refeito a cada revisão de manual. RAG separa o
conhecimento (que muda toda semana) do modelo (que não precisa mudar), e permite
citar a fonte — requisito não negociável em manutenção.

**Chunking por seção, não por tamanho fixo.** Cortar a cada N caracteres parte
tabelas no meio e separa o título da seção do seu conteúdo. Como boa parte das
perguntas é respondida por *uma linha de tabela*, perder a tabela é perder a
resposta. O chunker quebra em blocos (parágrafo, item, linha de tabela), detecta
títulos numerados como fronteira natural e agrupa até ~1.600 caracteres com
sobreposição de ~250.

**Contexto embutido no vetor.** Um trecho que diz apenas
`500 h | Filtro de retorno | Trocar | FH-P5501` não menciona o equipamento em
lugar nenhum. O embedding é calculado sobre `título do documento > seção > texto`,
senão esse trecho nunca seria recuperado por uma pergunta que cita o equipamento
pelo nome.

**Busca híbrida (vetorial + BM25, fundidas por RRF).** Busca vetorial entende
paráfrase mas confunde códigos de peça: `FH-P5501` e `FH-P5502` ficam a
milímetros um do outro no espaço vetorial. Busca textual acerta o código exato e
erra quando a pergunta não repete as palavras do documento. A fusão usa
*Reciprocal Rank Fusion* — combina **posições**, não pontuações, porque
similaridade de cosseno e `ts_rank` vivem em escalas diferentes e somá-las
diretamente não significaria nada.

**Postgres + pgvector em vez de banco vetorial dedicado.** O projeto precisa de
vetor, texto, metadados e busca por palavra-chave. O Postgres faz as quatro
coisas em uma infraestrutura que a maioria dos times já opera. Um serviço
separado só para vetores seria mais uma peça para manter, sem ganho nesta escala.

**Persistência trocável, com SQLite como padrão.** Exigir Docker para rodar o
pipeline trancava a parte do projeto que mais muda — chunking, embeddings, fusão
de rankings — atrás de uma infraestrutura que não tem nada a ver com ela. Os dois
backends expõem as mesmas funções, então `indexacao.py`, `busca.py` e `api.py`
não sabem qual está ativo. Escolher o SQLite como padrão é escolher que o projeto
rode em uma máquina limpa; escolher o Postgres continua sendo escolher escala.

**Filtro por equipamento derivado dos metadados, não de uma lista no código.** Os
apelidos de cada máquina saem do próprio valor gravado no banco, e um termo só
vale como apelido enquanto for exclusivo de um equipamento — cadastrar uma
segunda máquina "hidráulica" anula o termo sozinho. O filtro se recusa a escolher
quando a pergunta cita duas máquinas ou nenhuma, porque um filtro errado não
piora o ranking: ele apaga a resposta da base. Documentos válidos para a frota
inteira, como o POP de lubrificação, passam sempre.

**Embeddings locais.** Custo por requisição zero, nenhum documento interno sai da
máquina, e reindexar a base inteira fica barato o suficiente para ser feito a
cada mudança de estratégia de chunking — que é justamente o que mais se ajusta.

**Grounding explícito.** O prompt instrui o modelo a responder apenas com os
trechos fornecidos e a recusar quando a informação não estiver lá. Reduz — não
elimina — a invenção de resposta. Por isso as fontes sempre acompanham a
resposta.

## O que não funcionou

Anotado durante o desenvolvimento, porque é o que explica as decisões acima:

- **Extração simples de PDF embaralhou as tabelas.** O texto das células saía em
  ordem de desenho, não de leitura, e um intervalo de troca virava ruído. A
  correção foi extrair em modo *layout* e converter cada linha de tabela em
  `célula | célula | célula` — uma linha que vale mais que o resto do parágrafo
  para a busca.
- **Regra de detecção de título boa demais.** O primeiro regex tratava
  `250 h | Trocar o filtro | FL-6600` como título de seção, porque começa com
  número. Resultado: cada linha de tabela virava um trecho isolado de 40
  caracteres. Corrigido exigindo que a linha não contenha separador de coluna.
- **Descartar trechos pequenos custou uma resposta.** Havia um filtro que jogava
  fora trechos com menos de 40 caracteres. Ele descartou justamente a linha da
  tabela de APF que respondia uma das perguntas de avaliação. Agora sobras
  pequenas são absorvidas pelo trecho anterior em vez de descartadas.
- **Rodapé repetido poluía todos os vetores.** O cabeçalho `MAN-XXX-PT - rev. 4 |
  Página N` aparecia em todo chunk e adicionava o mesmo ruído a todos os vetores.
  Removido na normalização.

## Limitações conhecidas

- **PDF escaneado não é suportado**: sem camada de texto, a extração falha com
  mensagem explícita. O caminho seria OCR antes da ingestão.
- **Reranker custa ~2,3 s por pergunta em CPU**: entrega +19 pontos de
  recall@1, mas multiplica a latência da recuperação por cerca de 38. Vem
  desligado por padrão; ligar é decisão de orçamento de latência.
- **O ajuste do reranker foi feito numa base onde recall@5 é 1,00**: reordenar 5
  ou 20 candidatos deu o mesmo resultado *aqui*. Numa base maior isso deixa de
  valer e `CANDIDATOS_RERANKER` precisa subir — com medição nova, não por
  analogia.
- **Sem memória de conversa**: cada pergunta é independente; "e no caminhão?"
  depois de uma pergunta sobre a escavadeira não funciona.
- **Avaliação mede recuperação, não geração**: a qualidade da resposta final
  ainda é verificada manualmente. Falta um endpoint de geração configurado para
  medir se cada afirmação da resposta está sustentada por um trecho citado.
- **Base de exemplo pequena** (22 trechos): suficiente para pegar regressão de
  chunking e para comparar camadas, insuficiente para separar híbrida de
  semântica pura — a diferença medida entre elas é de uma pergunta em 40.
- **Busca vetorial do SQLite é força bruta**: instantânea nesta escala, mas
  cresce linearmente. Para base grande, `BACKEND=postgres`.

## Próximos passos

1. **Endpoint de geração configurado**, e conferir as quatro perguntas de
   controle: a resposta correta é recusar. A medição acima mostra que não há
   limiar de similaridade que ajude — se o modelo inventar, é o prompt que
   precisa endurecer.
2. **Avaliação da geração**: verificar se toda afirmação da resposta está
   sustentada por algum trecho citado. Bloqueado pelo item 1.
3. **Base maior**, real ou fictícia. Três conclusões deste README são reféns dos
   22 trechos atuais: a híbrida não se separa da semântica pura, o reranker não
   precisa de mais de 5 candidatos, e o recall@5 é 1,00. Todas mudam com escala,
   e nenhuma deve ser reaproveitada sem remedir.
4. **Rodar o backend Postgres pelo menos uma vez** — é o único módulo do projeto
   que nunca executou.
5. Ingestão incremental disparada por chegada de arquivo, em vez de execução
   manual do script.
6. Agente com ferramentas sobre a mesma base: além de responder, abrir a ordem de
   serviço e consultar o histórico do equipamento.

## Estrutura do repositório

```
rag-manutencao/
├── data/
│   ├── avaliacao/perguntas.json     conjunto de avaliação da recuperação
│   └── pdfs/                        base de conhecimento (gerada pelo script)
├── scripts/
│   ├── conteudo_pdfs.py             conteúdo dos documentos de exemplo
│   ├── gerar_pdfs.py                gera os PDFs da base
│   ├── indexar.py                   PDF -> índice
│   ├── perguntar.py                 consulta pela linha de comando
│   └── avaliar.py                   recall@k, MRR e latência por configuração
├── src/rag/
│   ├── config.py                    configuração via .env
│   ├── extracao.py                  PDF -> texto normalizado por página
│   ├── chunking.py                  texto -> trechos com seção e página
│   ├── embeddings.py                texto -> vetor (modelo local)
│   ├── banco.py                     fachada da persistência
│   ├── backends/
│   │   ├── sqlite.py                FTS5 + cosseno em numpy (padrão)
│   │   └── postgres.py              pgvector + tsvector (produção)
│   ├── indexacao.py                 orquestra a fase offline
│   ├── busca.py                     recuperação: híbrida, semântica, textual
│   ├── equipamentos.py              infere de qual máquina a pergunta fala
│   ├── reranker.py                  reordenação por cross-encoder (opcional)
│   ├── geracao.py                   prompt ancorado + chamada do modelo
│   ├── formatacao.py                formatação das citações
│   ├── modelos.py                   contratos de entrada e saída da API
│   └── api.py                       FastAPI
├── tests/                           sem banco externo, sem rede
├── docker-compose.yml               Postgres 16 + pgvector (só para BACKEND=postgres)
└── requirements.txt
```

## Testes

```bash
pytest
```

Os testes não precisam de banco externo, de rede nem de baixar modelo. Cobrem a
normalização da extração, as invariantes do chunking (linha de tabela inteira,
página preservada, seção atribuída, sobreposição entre vizinhos), a montagem do
prompt, a inferência de equipamento e o backend SQLite — este último com vetores
de três dimensões escritos à mão, porque o que está sob teste é a persistência e
a fusão de rankings, não a qualidade dos embeddings.
