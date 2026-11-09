# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Analistas internos autorizados de uma instituição financeira. Em homologação, eles investigam históricos inteiramente sintéticos, recuperam políticas e evidências relacionadas e submetem análises sensíveis para aprovação humana.

## Product Purpose

O Aegis Intelligence Workspace é uma plataforma interna preparada para reunir dados autorizados, recuperar documentos semanticamente e coordenar análises rastreáveis. A homologação usa somente dados sintéticos. Sucesso significa localizar evidências verificáveis, bloquear acesso não autorizado e manter cada decisão associada à sua fonte e execução.

## Positioning

O produto combina recuperação documental com um fluxo multiagente observável: cada etapa, ferramenta, evidência e aprovação permanece consultável em vez de ser escondida em uma resposta de chat.

## Operating Context

O analista seleciona um caso sintético, consulta o dossiê permitido, inicia uma análise Data → Risk → Analytics → Report e revisa as evidências antes de aprovar o relatório. O ambiente é dedicado à demonstração e usa apenas identidades, empresas, valores e eventos fictícios.

## Capabilities and Constraints

- Angular acessa somente o gateway ASP.NET Core; o runtime Python permanece privado.
- PostgreSQL com pgvector armazena documentos e embeddings multilíngues de 384 dimensões.
- JWT, permissões por operação e token de serviço protegem a configuração de homologação.
- O provedor determinístico permite testes sem chave; ele não representa inferência real de LLM.
- O recorte atual demonstra um workspace dedicado. Autorização por carteira e integração com identidade corporativa dependem da configuração do banco adotante.
- Nenhum dado bancário real, decisão automática de crédito ou movimentação financeira é permitido.

## Brand Commitments

O nome público é Aegis Agent Lab. A voz deve ser sóbria, precisa e transparente sobre evidência, simulação e limites.

## Evidence on Hand

O repositório contém dataset sintético, validação ponta a ponta do RAG/MCP, testes automatizados e registros em `docs/validation/`. Não há cliente, banco ou resultado comercial real a declarar.

## Product Principles

- Evidência antes de conclusão.
- Acesso mínimo e explícito.
- Aprovação humana para ações sensíveis.
- Rastreabilidade de cada etapa.
- Limites da demonstração sempre visíveis.

## Accessibility & Inclusion

Fluxos operacionais devem funcionar por teclado, manter foco visível, contraste legível, estados anunciáveis e linguagem direta em português.
