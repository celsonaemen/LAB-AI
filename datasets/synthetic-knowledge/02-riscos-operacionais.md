# Registro de riscos operacionais - RSK-002

Dados integralmente sintéticos da organização fictícia Aurora Nebula. O registro existe para avaliar continuidade do processamento documental Lume. Não contém posições financeiras, clientes ou decisões de crédito. As notas de severidade são critérios deste laboratório.

## Risco R-14: duplicidade no replay

A severidade de R-14 é alta porque uma nova tentativa sem idempotência poderia aumentar a contagem de documentos e apresentar fontes repetidas. O dono fictício é o time Horizonte. Os controles exigidos são hash do conteúdo normalizado, unicidade da configuração de indexação e transação atômica entre documento e fragmentos. A evidência de mitigação é a repetição controlada dos 240 documentos descritos em INC-007, sem criar novas cópias.

## Risco R-22: indisponibilidade de busca

A severidade de R-22 é média. Uma busca indisponível deve produzir erro explícito e não uma resposta plausível sem fontes. O time Brisa acompanha disponibilidade e latência conforme KPI-003. O plano BCP-009 define restauração e validação de integridade antes de reabrir o serviço. Não há autorização automática para mudar dados em produção.

## Acompanhamento

A revisão de risco ocorre a cada sete dias. Cada responsável registra estado aberto, mitigado ou aceito, evidência, data e justificativa. Uma aceitação sem evidência permanece aberta para revisão humana. O relatório OPS-008 consolida somente indicadores observados. Falhas de permissão pertencem também à política SEC-004 e devem ser investigadas sem expor o conteúdo sensível nos eventos.
