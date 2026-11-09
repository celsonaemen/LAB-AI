# Relatório operacional da semana do exercício - OPS-008

Relatório inteiramente sintético da organização fictícia Aurora Nebula. A semana do exercício consolida documentação de arquitetura, riscos e continuidade. Os números são fatos do cenário e não medições do ambiente em que este corpus é executado. O relatório precisa separar fatos documentados, cálculos derivados e informações desconhecidas.

## Incidente e recuperação

O relatório consolida o incidente JASMIM-17, com duração documentada de 17 minutos. Segundo INC-007, 240 documentos foram reprocessados e a deduplicação impediu criação de cópias. R-14 foi mitigado por reprocessamento idempotente, conforme controles de RSK-002 e DOC-006. A evidência é a comparação de identificadores e contagens, não uma promessa de que nenhum incidente futuro ocorrerá.

## Indicadores e limites

A meta de disponibilidade definida em KPI-003 é 99,5%, com busca p95 inferior a 800 ms. Não há evidência para disponibilidade mensal nem amostra suficiente para calcular percentis reais. O relatório deve registrar essa limitação de forma explícita. Dados de uma única ocorrência não autorizam afirmar cumprimento de todos os objetivos de serviço.

## Aprovação e proveniência

O responsável humano revisa fontes e limitações antes de aprovar divulgação. Referências precisam conter UUID do documento, UUID do fragmento e origem. O manifesto de DAT-005 ajuda localizar itens, mas não substitui os identificadores retornados pelo serviço. Falhas e ausências de evidência permanecem visíveis. O relatório não contém recomendação bancária, dados de clientes ou material de instituições reais.
