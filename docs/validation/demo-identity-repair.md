# Correção da identidade dos documentos antigos de demonstração

Data: 2026-11-08. Esta manutenção trata dados sintéticos históricos de demonstração; não envolve documentos de uma instituição real.

A renomeação do código não modificou o conteúdo já persistido no PostgreSQL. Uma busca pela interface revelou seis PDFs antigos de demonstração cujo cabeçalho ainda continha o rótulo anterior. Foram corrigidos somente os seis documentos das fontes `demo/credit-policy.pdf` e `demo/cafeteria.pdf`, com metadado `area=demo`.

O script `scripts/repair_demo_identity.py` trabalha em modo de leitura por padrão. Para aplicar, exige uma lista exata dos UUIDs identificados. Antes de escrever, reconstrói o texto pelos chunks e suas sobreposições, confere o SHA-256 original e verifica que a nova divisão conserva a quantidade de chunks. Uma divergência cancela a operação. Os IDs de documentos e chunks são preservados.

O mesmo motor FastEmbed usado pela ingestão gerou nove embeddings reais de 384 dimensões para os nove chunks completos desses documentos. Texto, embeddings, hash e timestamp foram atualizados em uma única transação. Foi criado um backup privado dos registros originais e vetores em `.artifacts/identity-repair/`, já ignorado pelo Git. Não houve exclusão de documentos nem alteração do corpus `aegis-synthetic-v1`.

Verificação posterior: zero chunks pesquisáveis contendo o rótulo anterior; busca pública por `credito` aprovada por meio do proxy Angular, retornando cinco resultados sem o rótulo retirado. O corpus sintético manteve 12 documentos e 68 embeddings, todos com 384 dimensões. Três testes da manutenção passaram, cobrindo reconstrução, recusa de hash inconsistente e recusa de fontes fora do escopo.

Os snapshots e eventos de execuções antigas foram preservados como evidências históricas. Esta manutenção não afirma que alterou ou apagou esses registros. Backups privados e arquivos antigos locais também não fazem parte da base pesquisável corrigida.

Reprodução, com conexão local e cache absoluto configurados privadamente:

```powershell
apps/ai-runtime/.venv/Scripts/python.exe scripts/repair_demo_identity.py --old-label '<rótulo anterior>'
# Após conferir o plano, adicionar --apply e um --document-id para cada UUID exato.
apps/ai-runtime/.venv/Scripts/python.exe -m pytest apps/ai-runtime/tests/test_demo_identity_repair.py -q
```

Não houve commit, push, configuração de produção nem instalação de dependências.
