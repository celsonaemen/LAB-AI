# Validação real: base sintética, MCP e fluxo multiagente

Data: 2026-11-08. Projeto: Aegis Agent Lab. Corpus: `aegis-synthetic-v1`.

**Resultado: o critério de ingestão real, pgvector, recuperação MCP e evidência multiagente foi atingido.** A execução de aceitação completa aprovou 27 verificações. Foram persistidos 12 documentos, 68 chunks e 68 embeddings reais de 384 dimensões. O provedor do orquestrador permaneceu `deterministic`; esta validação não comprova inferência de LLM nem seleção autônoma de ferramentas por um modelo.

O relatório completo da execução está em `.artifacts/synthetic-knowledge-final/acceptance.json`, diretório local ignorado pelo Git. O [resumo de evidências](synthetic-knowledge-mcp-evidence.json) preserva contagens, UUIDs, fontes, resultados e verificações sem credenciais ou caminhos privados. A execução definitiva, após endurecer as verificações de fatos conhecidos e códigos de erro, ocorreu entre `2026-11-08T14:42:29-03:00` e `2026-11-08T14:44:05-03:00`.

## Auditoria e arquitetura reutilizada

Antes das alterações foram consultados os contratos públicos, a arquitetura do orquestrador, o ADR 0004, os relatórios das etapas anteriores, as três migrações, o armazenamento RAG, o FastEmbed e os clientes/servidor MCP existentes.

O carregamento utilizou exclusivamente `POST /api/v1/knowledge/documents`, passando pela API .NET e pelo runtime FastAPI. O Python executou extração, normalização, chunking a 350 caracteres com sobreposição de 60, FastEmbed e persistência transacional. Não houve inserção de documentos ou vetores por SQL. A conexão SQL do script de validação foi configurada como somente leitura para conferir os resultados de forma independente.

Foram verificados `knowledge.documents`, `knowledge.document_chunks`, `knowledge.agent_executions` e `knowledge.agent_execution_events`, a extensão pgvector 0.8.7 e as migrações `V001__knowledge_schema.sql`, `V002__knowledge_hnsw.sql` e `V003__agent_executions.sql`. O índice HNSW usa `vector_cosine_ops`; a busca existente utiliza distância de cosseno e retorna similaridade como `1 - distância`.

O servidor oficial MCP continua no runtime existente, via stdio, SDK `mcp==1.30.0`. O cliente lança apenas o módulo fixo autorizado. Data Agent pode pesquisar/listar/consultar documentos; Risk e Analytics utilizam suas ferramentas internas de cálculo; Report pode consultar resumos de histórico somente com aprovação explícita fornecida pelo operador confiável. Essa capacidade do processo não equivale a autenticação/RBAC de usuários.

## Dataset sintético

A organização Aurora Nebula, a plataforma Lume, o incidente JASMIM-17, as pessoas, valores e eventos são fictícios. O incidente documentado durou 17 minutos e exigiu replay idempotente de 240 documentos. As referências entre os documentos conectam riscos, indicadores, processamento e continuidade. O manifesto também registra consultas em português/inglês, fatos esperados, relações e hashes dos arquivos.

O [manifesto](../../datasets/synthetic-knowledge/manifest.json) contém quatro PDFs, quatro arquivos TXT e quatro arquivos Markdown. Fontes e arquivos podem ser regenerados por `scripts/generate_synthetic_knowledge.py`, usando a dependência pypdf já existente.

| ID lógico | Documento | Formato | Chunks SQL |
|---|---|---|---:|
| ARC-001 | Arquitetura da plataforma Lume | PDF | 6 |
| RSK-002 | Registro de riscos operacionais | Markdown | 6 |
| KPI-003 | Indicadores e objetivos de serviço | TXT | 6 |
| SEC-004 | Segurança de aplicações | PDF | 6 |
| DAT-005 | Governança de dados | Markdown | 6 |
| DOC-006 | Processamento documental | TXT | 5 |
| INC-007 | Análise do incidente JASMIM-17 | PDF | 5 |
| OPS-008 | Relatório operacional | Markdown | 6 |
| BCP-009 | Continuidade e recuperação | TXT | 6 |
| IAM-010 | Controle de acesso | PDF | 6 |
| GLO-011 | English operational glossary | TXT | 6 |
| ADV-012 | Amostra adversarial identificada | Markdown | 4 |
| **Total** | **12 documentos** | **4 de cada formato** | **68** |

Os quatro chunks de ADV-012 contêm padrões de prompt injection para testar quarentena. Apenas esse documento é marcado com `attack=true`. Os demais recebem `attack=false`. Todos recebem `corpus`, `logicalId`, `theme`, `organization` e `synthetic=true` como metadados textuais.

## Ingestão, vetores e reingestão

A primeira carga aprovou 15 verificações em 23,88 segundos: manifesto, readiness, 12 ingestões com reingestão e conferência SQL. A execução completa repetiu o carregamento pela API, aprovando novamente a deduplicação.

- Documentos físicos indexados neste corpus: **12**.
- Chunks persistidos neste corpus: **68**.
- Embeddings persistidos e não nulos: **68**.
- Dimensões observadas por `vector_dims(embedding)`: **384 em todas as linhas**.
- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, pelo FastEmbed configurado.
- Reingestão: mesmo UUID, mesma quantidade de chunks, `deduplicated=true` e metadados originais preservados mesmo quando a segunda requisição propõe metadados diferentes.

Os detalhes retornados pela API mantiveram filename, source, título e metadados. Cada referência MCP foi conferida contra o UUID, conteúdo e source persistidos no PostgreSQL.

## Resultado individual das ferramentas MCP

| Ferramenta | Resultado real |
|---|---|
| `search_knowledge` | Aprovada: consultas PT/EN, `limit=1/3`, ordenação por similaridade, filtros, referências SQL e limite de contexto. |
| `get_document` | Aprovada: metadados por UUID existente; UUID inexistente e identificador inválido rejeitados. |
| `list_documents` | Aprovada: retorno de metadados com no máximo 20 registros; `limit=21` rejeitado. |
| `get_execution_history` | Aprovada: sem aprovação é bloqueada; com Report Agent aprovado retorna somente resumos autorizados. |

Consulta PT: `Qual foi a duração do incidente JASMIM-17 e quantos documentos precisaram de reprocessamento?`

Consulta EN: `How long did incident JASMIM-17 last and how many documents were replayed?`

As consultas conhecidas, filtradas por INC-007, recuperaram um trecho contendo `Incident JASMIM-17 lasted 17 minutes; 240 documents were replayed without creating duplicate records.` As similaridades do primeiro resultado foram aproximadamente **0,77495 em português** e **0,77694 em inglês**. Também foram executadas buscas amplas em português e inglês no corpus seguro, sem filtro de ID lógico, exigindo os fatos de 17 minutos e 240 documentos e referências ao incidente ou a documentos relacionados. Os UUIDs e conteúdos dos chunks corresponderam ao SQL. Esses exemplos não constituem um benchmark amplo de qualidade semântica.

Com `maxContextChars=400`, o contexto retornou **399 caracteres**. A consulta não relacionada com `minScore=1` retornou zero resultados, zero referências e `insufficient_evidence`. Um filtro de corpus inexistente também retornou zero evidências. `generatedAnswer` permaneceu nulo, distinguindo recuperação de geração de texto.

## Segurança nas camadas de aplicação e servidor

Foram aprovados **15 casos negativos na camada do cliente/aplicação** e **12 casos diretamente pelo SDK contra o servidor MCP**, sem depender de validações da interface. Os testes diretos contornam a validação do cliente de propósito para conferir a defesa do servidor.

Os casos incluem agente não autorizado, histórico sem aprovação, tentativa de passar `approved` como argumento, propriedades extras (`command`, `url`), ferramenta desconhecida, UUID inválido/inexistente, path traversal, limites de paginação/pesquisa/contexto excedidos e prompt injection na consulta.

O servidor rejeitou os casos diretos com `isError=true`. A validação do cliente exigiu o código específico esperado por caso: `invalid_tool_arguments`, `tool_not_allowed`, `approval_required`, `unknown_tool` ou `tool_failed` para documento inexistente/consulta adversarial. Uma falha de conexão ou timeout não é aceita como prova de autorização correta. Nenhuma ferramenta lê arquivos arbitrários, executa comandos ou aceita SQL fornecido pelo solicitante.

A consulta real ao documento ADV-012 usou `minScore=-1` e o filtro do ID lógico para que seus chunks fossem candidatos à recuperação. Os quatro trechos adversariais foram descartados, resultando em zero fontes e `insufficient_evidence`. Os documentos permaneceram armazenados para auditoria; o bloqueio ocorreu na recuperação MCP.

O histórico aprovado retornou somente `id`, `state`, `workflow`, `provider`, `createdAt`, `startedAt` e `finishedAt`, incluindo os três IDs criados nesta execução de aceitação. Tarefas e resultados completos não fazem parte dessa ferramenta. A listagem MCP também exigiu pelo menos um UUID do dataset recém-indexado, além de conferir os metadados e o máximo de vinte registros.

## Fluxo Data → Risk → Analytics → Report

Execução concluída: `b8a91b91-37f6-48ba-b494-3f04c899654b`.

- Quatro agentes em ordem, todos `Completed`.
- Recuperação real de `search_knowledge` via MCP pelo Data Agent, seguida dos cálculos autorizados de Risk/Analytics.
- Pausa persistida em `AwaitingApproval`, com três agentes concluídos e Report ainda não executado.
- Aprovação explícita pela API pública; retomada e conclusão do Report.
- **26 eventos persistidos**, conferidos em SQL e entregues pela conexão SSE ao vivo.
- O replay SSE respeitou `Last-Event-ID`, entregou as sequências restantes e fechou após o estado terminal.
- Resultado final com rótulo `deterministic` e aviso explícito de ausência de inferência de LLM.
- **Cinco referências reais**, conectando relatório operacional, incidente, glossário e indicadores.

Exemplo de fonte: chunk `3cf9a856-da3f-4cb6-93c3-6f09d7855b8c`, documento `6c25aac9-349f-4684-a56d-0c85fd781d76`, source `synthetic/aegis-synthetic-v1/07-incidente-jasmim.pdf`. O conteúdo e os identificadores foram comparados com o PostgreSQL.

Execução cancelada: `e0fcc218-8609-4e0f-8eb7-1d4b327fcedc`. A execução alcançou a aprovação, recebeu cancelamento e persistiu **20 eventos**; o Report ficou `Cancelled`. Uma tentativa posterior de aprovação retornou HTTP 409.

Execução de solicitação adversarial: `b94e1ec5-a508-4721-a8cb-a7460bff95f3`. Terminou em `Failed` conforme esperado, com **quatro eventos**, incluindo `GuardrailBlocked`, sem iniciar ferramenta MCP. Os quatro agentes ficaram `Skipped`. As três execuções foram encontradas no histórico público e no histórico MCP autorizado.

O transporte SSE real foi validado por HTTP, incluindo entrega durante a execução e replay. A interface também foi exercitada no navegador: execução `f8adca72-0e23-4114-b2c9-7ec429f42af0`, criada pelo formulário de revisão documental com corpus sintético e aprovação obrigatória. O DOM atualizou sem recarga manual para três agentes concluídos e Report aguardando aprovação; após o clique em Aprovar, apresentou os quatro agentes concluídos, resultado final e 26 eventos. Foram observadas duas conexões SSE pelo proxy Angular com HTTP 200, a aprovação com HTTP 200 e nenhum erro ou aviso no console.

A busca pela interface recuperou cinco trechos com os fatos de 17 minutos e 240 documentos e uma referência ao PDF do incidente. As observações de DOM/rede/console estão em [evidência do navegador](synthetic-knowledge-browser.json). Uma captura do viewport Angular foi observada na conversa. A exportação de screenshot para arquivo encontrou uma restrição de caminho; a renderização visual dos PDFs não foi concluída. Os PDFs foram conferidos por extração integral e limites geométricos, sem instalar renderizadores adicionais.

## Falhas encontradas e correções

1. **Inicialização do modelo no subprocesso MCP.** O carregamento de NumPy/FastEmbed dentro do ciclo assíncrono do SDK travava no ambiente local. A inicialização das dependências foi antecipada para antes do loop do servidor. Cache absoluto e aquecimento real foram usados na reprodução. Isso preserva o modelo e os limites; não substitui embeddings por valores artificiais.
2. **Retorno MCP sem `structuredContent` utilizável.** Funções declaradas genericamente como `dict` não forneciam o contrato esperado pelo cliente. Os retornos passaram a usar os modelos existentes `SearchResponse`, `DocumentDetails` e listas tipadas. O teste de conteúdo estruturado reproduziu a falha antes da correção.
3. **Limite de contexto perdido na filtragem.** A reconstrução de evidências utilizava o padrão de 6.000 caracteres e ignorava o valor solicitado. O caso com limite 400 inicialmente retornou 2.484 caracteres; após preservar o limite no servidor e no cliente, a aceitação retornou 399.

As falhas anteriores do CI não foram mascaradas nem tratadas como sucesso. O pipeline do GitHub não foi reexecutado com estas alterações locais, pois esta tarefa proíbe commit e push.

## Testes automatizados executados

| Verificação | Resultado |
|---|---|
| Aceitação completa sintética HTTP + SQL + MCP + agentes | **27 aprovadas, zero falhas** |
| Carga isolada HTTP + SQL | **15 aprovadas, zero falhas** |
| Python com modelo real e PostgreSQL de testes | **77 aprovados, zero ignorados** |
| .NET, execução `--no-build` | **47 aprovados** |
| Angular | **20 aprovados** |
| Build Angular | **Aprovado; 356,71 kB** |

A suíte Python ainda emite o aviso de depreciação Starlette/AnyIO já conhecido. Não foi instalada dependência nova para o dataset. Não foram alterados contratos públicos, configurações de produção ou guardrails para forçar aprovação.

## Reprodução em PowerShell

Execute a partir da raiz do repositório. Configure a conexão local de desenvolvimento privadamente no processo; não grave senhas no script ou no histórico de comandos. A conexão de testes deve apontar para um banco dedicado e descartável, separado do utilizado pela aplicação.

```powershell
# Requer PostgreSQL nativo com pgvector já configurado.
# Defina DATABASE_URL privadamente neste processo.
# Defina AEGIS_TEST_DATABASE_URL para o banco dedicado aos testes.
$env:EMBEDDING_CACHE_DIR = (Resolve-Path '.model-cache').Path
$env:PYTHONPATH = 'apps/ai-runtime'
$env:AEGIS_REAL_EMBEDDINGS = '1'
$env:AEGIS_LLM_PROVIDER = 'deterministic'
& apps/ai-runtime/.venv/Scripts/python.exe -m app.migrate
& apps/ai-runtime/.venv/Scripts/python.exe -c "from app.rag.embeddings import embed; assert len(embed(['aquecimento sintético'])[0]) == 384"
# Opcional somente após garantir que os pesos estão no cache:
$env:HF_HUB_OFFLINE = '1'
& apps/ai-runtime/.venv/Scripts/python.exe scripts/generate_synthetic_knowledge.py

# Terminal 1, com DATABASE_URL e EMBEDDING_CACHE_DIR configurados:
& apps/ai-runtime/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-config apps/ai-runtime/app/logging.json
# Terminal 2, SDK .NET 10:
dotnet run --project apps/api/src/Aegis.Api --urls http://127.0.0.1:5080
# Terminal 3:
./scripts/native.ps1 Web

# Terminal 4, com os mesmos DATABASE_URL/PYTHONPATH/cache do runtime:
& apps/ai-runtime/.venv/Scripts/python.exe scripts/synthetic_knowledge_acceptance.py --load-only --output .artifacts/synthetic-knowledge
& apps/ai-runtime/.venv/Scripts/python.exe scripts/synthetic_knowledge_acceptance.py --output .artifacts/synthetic-knowledge-final

# Regressão real; exige AEGIS_TEST_DATABASE_URL no banco dedicado:
& apps/ai-runtime/.venv/Scripts/python.exe -m pytest apps/ai-runtime/tests -q
dotnet test apps/api/Aegis.slnx --no-build
npm --prefix apps/web test -- --watch=false
npm --prefix apps/web run build
```

O SDK local validado nesta estação também pode ser chamado por `.tools/dotnet/dotnet.exe`. O script de aceitação usa os arquivos reais do manifesto, conserva as evidências mesmo ao falhar e retorna exit code diferente de zero se qualquer verificação solicitada falhar.

## Arquivos criados e modificados

Modificados:

- `README.md`
- `apps/ai-runtime/app/executions/guardrails.py`
- `apps/ai-runtime/app/mcp_tools/client.py`
- `apps/ai-runtime/app/mcp_tools/server.py`
- `apps/ai-runtime/tests/test_guardrails.py`
- `apps/ai-runtime/tests/test_mcp.py`

Criados:

- `datasets/synthetic-knowledge/01-arquitetura-lume.pdf`
- `datasets/synthetic-knowledge/02-riscos-operacionais.md`
- `datasets/synthetic-knowledge/03-indicadores-slo.txt`
- `datasets/synthetic-knowledge/04-seguranca-aplicacoes.pdf`
- `datasets/synthetic-knowledge/05-governanca-dados.md`
- `datasets/synthetic-knowledge/06-processamento-documental.txt`
- `datasets/synthetic-knowledge/07-incidente-jasmim.pdf`
- `datasets/synthetic-knowledge/08-relatorio-operacional.md`
- `datasets/synthetic-knowledge/09-continuidade-recuperacao.txt`
- `datasets/synthetic-knowledge/10-controle-acesso.pdf`
- `datasets/synthetic-knowledge/11-operational-glossary.txt`
- `datasets/synthetic-knowledge/12-amostra-adversarial.md`
- `datasets/synthetic-knowledge/manifest.json`
- `datasets/synthetic-knowledge/sources.json`
- `datasets/synthetic-knowledge/README.md`
- `scripts/generate_synthetic_knowledge.py`
- `scripts/synthetic_knowledge_acceptance.py`
- `docs/validation/synthetic-knowledge-mcp.md`
- `docs/validation/synthetic-knowledge-mcp-evidence.json`
- `docs/validation/synthetic-knowledge-browser.json`

## Limitações e próximos passos

- A execução continua determinística; não há comprovação de Tool Calling por LLM real.
- O produto ainda é uma demonstração localhost de operador único, sem autenticação de usuários, isolamento multitenant ou segurança de produção.
- As regras de prompt injection e redação são heurísticas e não eliminam todos os ataques possíveis.
- A conexão MCP é recriada por chamada; pesquisas repetidas pagam o custo de inicialização. Otimização de sessão persistente exige trabalho separado e medidas de desempenho.
- O dataset demonstra casos conhecidos e não mede recall, precisão ou robustez em corpus amplo.
- Nenhum commit, push, publicação ou alteração de produção foi realizado nesta tarefa.
