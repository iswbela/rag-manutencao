# Handoff — Assistente de Manutenção (RAG)

**Data:** 13/09/2026 · **Estado:** pipeline executado ponta a ponta e medido ·
**Próxima ação:** configurar o endpoint de geração

Este documento é o "onde parei". A explicação do projeto e das decisões técnicas
está no [README.md](README.md); aqui está o que já foi verificado, o que ainda
não foi, as armadilhas que custaram tempo e a ordem sugerida de continuação.

---

## 1. Em uma frase

Pipeline de RAG sobre manuais de manutenção em PDF: extração → chunking por
seção → embeddings locais → índice (SQLite por padrão, Postgres/pgvector em
produção) → busca híbrida (vetorial + BM25 fundidas por RRF) → resposta ancorada
com citação de página, exposta por API FastAPI e por CLI.

## 2. O que mudou desde o handoff anterior

O handoff anterior dizia "esqueleto completo e testado, pronto para a primeira
indexação real". A indexação real rodou. Três coisas mudaram de fato:

1. **A máquina não tinha Docker funcionando** (o Docker Desktop falha ao iniciar
   com erro no `dockerInference`), e não tinha Postgres nativo. A persistência
   foi separada em dois backends atrás da mesma interface, com o **SQLite como
   padrão**. Isso desbloqueou o pipeline sem tocar em `indexacao.py`, `busca.py`
   nem `api.py` — que continuam sem saber qual backend está ativo.
2. **O conjunto de avaliação subiu de 18 para 40 perguntas** (mais 4 de
   controle), como o handoff anterior recomendava antes de comparar reranker.
3. **Filtro por equipamento e reranker foram implementados e medidos.** O
   filtro vem ligado (+3 ms, zero exclusões indevidas); o reranker vem
   desligado apesar de ser o maior ganho do projeto (+19 pontos de recall@1),
   porque custa ~2,3 s por pergunta em CPU. As tabelas estão no README.

## 3. Estado atual, sem otimismo

### Verificado, rodando

| Item | Como foi verificado |
|---|---|
| Geração dos 4 PDFs de exemplo | `python scripts/gerar_pdfs.py` — 13 páginas |
| Extração em modo layout | tabelas saem como `célula \| célula \| célula` |
| Chunking por seção | 22 trechos, todos com seção ou herdando a anterior |
| Cobertura do conjunto de avaliação | `avaliar.py --conferir` — 40/40 evidências existem |
| Indexação ponta a ponta | `indexar.py --recriar` — 4 documentos, 22 trechos, 48 s |
| Busca nas três estratégias | `avaliar.py` — tabela no README |
| Filtro por equipamento | 40 perguntas, zero exclusões do documento certo |
| Reranker | +19 pontos de recall@1 (0,78 → 0,97), 2,3 s por pergunta |
| Escolha do cross-encoder | dois modelos medidos lado a lado |
| Custo por nº de candidatos | 5, 10 e 20 medidos: mesmo recall, 4x de latência |
| Testes | `pytest` — 34 testes, verdes, sem banco externo e sem rede |

### Escrito, ainda NÃO executado

- **`backends/postgres.py`** — nunca rodou contra um Postgres real. Ganhou o
  filtro por equipamento (`_FILTRO` com `= ANY(...)`) junto com o SQLite, e essa
  mudança não foi testada em banco. Trate a primeira execução como depuração.
- **`geracao.py`** — a chamada HTTP ao endpoint de texto. Sem endpoint
  configurado, o projeto roda em modo somente-busca e `/perguntar` devolve 503.
- **`api.py`** — os quatro endpoints. O código importa e o esquema do FastAPI é
  válido, mas nenhum deles foi chamado por HTTP.

**Onde eu esperaria problema ao ligar o Postgres**, em ordem de probabilidade:

1. O predicado `%(equipamentos)s::text[] IS NULL OR d.equipamento = ANY(...)`
   com `None` — o psycopg precisa saber que o parâmetro é `text[]`; se reclamar,
   passe `[]` e troque a condição por `cardinality(...) = 0 OR ...`.
2. `EMBEDDING_DIM` (384) precisa bater com o modelo. O `CREATE TABLE` só roda uma
   vez e `VECTOR(384)` não se ajusta sozinha — troca de modelo exige `--recriar`.
   No SQLite isso já dá erro explícito pedindo `--recriar`; no Postgres, não.
3. Índice HNSW em tabela pequena é criado sem erro, mas o plano pode ignorá-lo.
   Não é bug.
4. `to_tsvector('portuguese', ...)` depende do dicionário de português estar na
   imagem do Postgres. Está na imagem oficial usada aqui.

## 4. Para retomar em 10 minutos

```bash
cd Documents\GitHub\rag-manutencao
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/gerar_pdfs.py
python scripts/indexar.py --recriar
python scripts/avaliar.py
```

Não precisa de Docker: o backend padrão é SQLite. A primeira indexação baixa o
modelo de embeddings (~120 MB) e leva cerca de 50 s.

Para reproduzir a comparação das camadas (baixa o cross-encoder, ~470 MB, e leva
cerca de 4 min em CPU):

```bash
python scripts/avaliar.py --comparar-camadas --salvar relatorios/avaliacao.json
```

Para repetir a comparação entre cross-encoders ou entre números de candidatos,
que é o que produziu as tabelas do README:

```bash
python scripts/avaliar.py --comparar-camadas --reranker-model OUTRO --candidatos-reranker 5
```

## 5. Armadilhas já pagas — não reintroduzir

As duas do chunking continuam valendo e voltam sozinhas se alguém mexer em
`chunking.py` sem ler:

- **Detecção de título não pode aceitar linha com `|`.** Sem isso,
  `250 h | Trocar o filtro | FL-6600` vira "título de seção" e cada linha de
  tabela vira um trecho isolado.
- **Sobra pequena se funde ao trecho anterior, nunca é descartada.** O filtro
  antigo (`len > 40`) apagou justamente a linha da tabela de APF que respondia a
  pergunta P14 da avaliação.

Cinco novas, desta rodada:

- **Não meça latência sem aquecer os modelos.** A primeira medição deste projeto
  reportou a híbrida a 1.212 ms contra 33 ms da semântica — a diferença inteira
  era o carregamento do modelo de embeddings, pago pela primeira estratégia da
  lista. `avaliar.py` agora chama `aquecer()` antes de cronometrar.
- **A pontuação da híbrida não é confiança.** RRF soma `1/(60+posição)`: o
  primeiro colocado pontua praticamente o mesmo tenha a busca achado a resposta
  ou lixo. Usar essa pontuação para decidir recusa não mede nada. A medição de
  recusa usa a similaridade de cosseno da busca semântica, de propósito.
- **Apelido de equipamento não pode ser número solto.** "MTX-220" produziria
  também o apelido "220", e "a pressão caiu para 220 bar" seria filtrada para a
  escavadeira. Números puros ficam fora do índice de apelidos; há teste.
- **Cross-encoder maior não é cross-encoder melhor.** O primeiro escolhido foi o
  `BAAI/bge-reranker-base` por ser o mais conhecido: 278 M de parâmetros, 0,88
  de recall@1, 15,7 s por pergunta. O `mmarco-mMiniLMv2-L12-H384-v1`, com 118 M,
  deu 0,97 em 4,3 s. O que decide aqui é o dado de treino — mMARCO inclui
  português — e não o tamanho. Se for trocar o reranker, meça antes.
- **Reordenar mais candidatos não compra recall se o recall@5 já é 1,00.**
  Reordenar 20 custava 4x mais que reordenar 5 pelo mesmo resultado. Isso é
  propriedade desta base pequena e vai mudar com escala — mas o hábito de medir
  o número de candidatos, e não herdá-lo, é o que fica.

Se mexer em chunking ou trocar o modelo de embeddings: **reindexe com
`--recriar` e rode `scripts/avaliar.py` antes e depois.**

## 6. Próximos passos, em ordem

1. **Configurar o endpoint de geração** no `.env` e conferir as quatro perguntas
   de controle (`N01`–`N04`): a resposta correta é recusar. A medição já mostrou
   que **nenhum limiar de similaridade separa** pergunta respondível de pergunta
   de controle — a pior pergunta com resposta (0,8442) pontua abaixo de duas de
   controle. Ou seja: a recusa depende inteiramente do prompt. Se o modelo
   inventar, é o prompt que endurece.
2. **Avaliação da geração**: verificar se cada afirmação da resposta está
   sustentada por um trecho citado. Bloqueado pelo passo 1.
3. **Decidir se o reranker entra ligado.** Está medido dos dois lados: +19
   pontos de recall@1 por ~2,3 s em CPU (ou ~1 s com `CANDIDATOS_RERANKER=5`,
   sem perda nesta base). A decisão depende do orçamento de latência com a
   geração somada, que só existe depois do passo 1.
4. **Base maior.** Três conclusões do README são reféns dos 22 trechos atuais: a
   híbrida não se separa da semântica pura, o reranker não precisa de mais de 5
   candidatos, e o recall@5 é 1,00. Nenhuma deve ser reaproveitada sem remedir.
5. **Rodar o backend Postgres pelo menos uma vez**, para que ele deixe de ser
   código não executado.
6. **Camada de agente** sobre a mesma base (abrir OS, consultar histórico), se a
   ideia for cobrir também "automação" além de RAG.

## 7. Mapa mental do código

```
scripts/gerar_pdfs.py ──► data/pdfs/*.pdf ──┐
scripts/conteudo_pdfs.py (conteúdo)         │
                                            ▼
                        extracao.py ──► chunking.py ──► embeddings.py
                                                             │
                                              indexacao.py ──┴──► banco.py
                                                                    │
                                                      backends/sqlite.py
                                                      backends/postgres.py
                                                                    │
                        busca.py ◄─────────────────────────────────┘
                           │  ├── equipamentos.py (filtro)
                           │  └── reranker.py (reordenação)
             ┌─────────────┴─────────────┐
        geracao.py                   api.py / scripts/perguntar.py
        (prompt + HTTP)              (entrada do usuário)
```

Regra que vale manter: `formatacao.py`, `chunking.py`, `extracao.py` e
`equipamentos.py` não importam banco nem rede — é o que permite testar a parte
que mais muda sem subir infraestrutura.

## 8. Vocabulário do domínio (para quem pegar o projeto sem contexto de mina)

- **APF** — abertura de posição fechada do britador; define a granulometria do
  produto.
- **Manto e côncavo** — os revestimentos de desgaste do britador cônico; trocados
  sempre em conjunto.
- **POP** — Procedimento Operacional Padrão.
- **TKPH** — indicador de capacidade de carga e velocidade do pneu fora de estrada.
- **Condição severa** — regime de operação que encurta os intervalos do plano
  preventivo.
- **Trecho / chunk** — pedaço do documento que é indexado e recuperado.
- **Recall@k** — em que fração das perguntas o trecho certo aparece entre os `k`
  primeiros resultados. É a métrica principal do projeto.
- **RRF** — fusão recíproca de rankings; combina posições de duas buscas, não
  pontuações.
- **Cross-encoder** — modelo que lê pergunta e trecho juntos e devolve
  relevância. Mais preciso que o embedding pela mesma razão que é mais caro:
  nada pode ser pré-calculado.

## 9. Perguntas em aberto

- **Qual endpoint de geração usar?** Continua aberta e agora é o que bloqueia o
  projeto. A escolha muda só o `.env`, mas sem ela não há número de latência nem
  de custo da resposta, e os passos 1 e 4 ficam parados.
- **Manter a base fictícia ou usar manuais públicos reais?** A fictícia é mais
  segura para publicar; a real é mais convincente na conversa. A fictícia também
  é pequena demais para separar híbrida de semântica pura — 22 trechos onde
  quase toda pergunta tem um trecho obviamente certo.
- **Vale reindexar tudo a cada mudança de chunking?** Hoje sim: 48 s. Numa base
  real de centenas de manuais isso deixa de ser verdade, e aí a indexação
  incremental por hash (já implementada em `indexar_pasta`) passa a ser o caminho
  padrão em vez de `--recriar`.
