# LinkedIn draft — review before posting

Estou desenvolvendo o **Aegis Agent Lab**, uma plataforma independente de estudos sobre engenharia Full Stack e agentes de IA corporativos, utilizando exclusivamente dados financeiros fictícios.

A solução combina Angular 20, ASP.NET Core .NET 10, Python/FastAPI e PostgreSQL com pgvector. O pipeline RAG processa PDF, TXT e Markdown, gera embeddings multilíngues de 384 dimensões com FastEmbed, executa busca semântica por cosseno e preserva as referências utilizadas.

Sobre essa base implementei um orquestrador rastreável com quatro responsabilidades: Data, Risk, Analytics e Report. Cada execução possui estados explícitos, histórico persistido, eventos em tempo real via SSE, cancelamento, aprovação humana e resultados intermediários auditáveis.

Na etapa mais recente adicionei um servidor MCP real com o SDK oficial. Os agentes descobrem ferramentas tipadas para pesquisar conhecimento, consultar documentos e acessar histórico autorizado. Guardrails bloqueiam prompt injection, ferramentas não permitidas, argumentos inválidos, ampliação de escopo, citações inexistentes e exposição de dados sensíveis.

Validação automatizada atual:

- 64 testes Python aprovados;
- 47 testes .NET aprovados;
- 20 testes Angular aprovados;
- PostgreSQL 18.6 + pgvector 0.8.7 validados localmente;
- descoberta MCP confirmada pelo runtime Python e pelo gateway público .NET.

Também registro os limites com transparência: o primeiro teste MCP ponta a ponta atingiu o timeout durante o cold start do modelo de embeddings, e ainda não há um modelo Ollama local configurado para comprovar Tool Calling escolhido por LLM real. O modo determinístico existe para testes, mas não é apresentado como inferência de IA.

O projeto é educacional e independente, sem afiliação ou acesso à arquitetura interna de qualquer instituição financeira. O foco é demonstrar decisões que consigo explicar, testar e evoluir: contratos, segurança, rastreabilidade, RAG, agentes e integração Full Stack.

Repositório: https://github.com/celsonaemen/LAB-btg

#SoftwareEngineering #ArtificialIntelligence #DotNet #Angular #Python #FastAPI #PostgreSQL #pgvector #RAG #MCP #AIAgents #CyberSecurity

Antes de publicar: adicionar, se disponível, um vídeo curto da demonstração. Este texto não foi publicado automaticamente.
