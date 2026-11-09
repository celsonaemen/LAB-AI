# Synthetic knowledge corpus

All organizations, figures, systems and events in this dataset are fictional. This corpus is intended exclusively for local Aegis Agent Lab ingestion, retrieval, MCP and agent acceptance tests. It contains no institutional or client data.

`sources.json` is the editable source of truth. `manifest.json` describes 12 generated documents: four PDF files, four UTF-8 TXT files and four UTF-8 Markdown files. Each item has a logical identifier, title, format, theme, description, metadata, related documents, known facts and Portuguese/English search queries.

Regenerate the fixtures from the repository root using the existing runtime environment:

```powershell
apps/ai-runtime/.venv/Scripts/python.exe scripts/generate_synthetic_knowledge.py
```

The generator uses the already installed `pypdf` package, wraps PDF text to 80 monospaced columns, paginates at 44 lines and verifies every source word through PDF extraction. It performs no HTTP calls, indexing or database writes. The actual ingestion and validation scripts must use the existing public .NET API and MCP server.

The stable corpus metadata value is `aegis-synthetic-v1`. The `logicalId` field belongs to this manifest; actual document/chunk UUIDs must come from API responses and database validation. The default 350-character chunks and 60-character overlap produce an expected 68 chunks before ingestion. The actual persisted count must be reported from PostgreSQL, not inferred from this expectation.

Document `ADV-012` is an intentionally adversarial fixture, identified by `attack: true`. Its content contains clear prompt-injection attempts for quarantine tests. The other 11 documents contain factual statements about the fictional scenario. The attack document is not an operational instruction and must not grant tool permissions or approval.

Key cross-document facts: incident JASMIM-17 lasted 17 minutes, replayed 240 documents without duplicates, and illustrates idempotent recovery. The fictional availability target is 99.5%; search p95 target is below 800 ms; recovery objectives are RTO 30 minutes and RPO 5 minutes. These are declared scenario facts and targets, not measurements of the running application.
