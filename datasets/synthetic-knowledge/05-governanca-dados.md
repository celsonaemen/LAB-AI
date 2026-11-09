# Governança e classificação de dados - DAT-005

O corpus da organização fictícia Aurora Nebula contém apenas dados fictícios. Para este exercício existem duas classificações: sintético público e sintético restrito. A classificação restrita representa uma regra do cenário, sem incluir informações pessoais reais. Nenhum documento foi obtido de sistemas internos de instituições reais.

Cada item recebe identificador lógico, título, tema, formato, organização, origem e marca de dado sintético. O manifesto é o catálogo legível por ferramentas de teste. Na ingestão, o identificador persistido do documento e os identificadores reais dos fragmentos são gerados pelo serviço. O identificador lógico do manifesto não deve ser apresentado como UUID de banco.

A origem e o hash são preservados na reingestão de conteúdo equivalente. Metadados enviados em uma repetição não substituem silenciosamente a origem original. O controle de deduplicação em DOC-006 deve retornar o mesmo UUID e sinalizar a repetição. A decisão permite verificar proveniência sem contar novamente os mesmos fatos.

O relatório OPS-008 deve citar as fontes efetivamente recuperadas e distinguir ausência de evidência de uma falha de serviço. Uma referência precisa resolver para documento e fragmento existentes. Rótulos textuais inventados não constituem fonte. A política SEC-004 rege proteção de eventos e tratamento de trechos não confiáveis. A governança não autoriza leitura arbitrária de arquivos locais e não altera as permissões de ferramentas.
