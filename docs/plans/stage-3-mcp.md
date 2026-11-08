# Stage 3 implementation ledger

Scope: reuse Stage2 coordinator and Stage1 RAG; add actual official MCP transport, bounded LLM-selected tool calls, guardrails, discovery/security UI and evidence. No broker, dangerous tools, real bank data or publication.

Audit/design complete before implementation: ADR0004, Stage2 report/source, MCP official SDK docs, Ollama tool-calling docs. No Ollama executable/listener/environment model found. Strict real-inference completion remains conditional and must not be claimed without a successful opt-in probe.

Tasks:

1. MCP server/client/router and SDK dependency: delegated, owns mcp_tools and transport tests. mcp1.30.0 installed in project venv; pip check passed, FastAPI/Starlette/Pydantic unchanged.
2. Guardrails, bounded model loop, worker integration and trace redaction: delegated, owns executions code/tests. Fixed schemas/actor authority cannot come from model text.
3. .NET catalog and Angular discovery/security presentation: delegated, preserves existing execution/SSE behavior and tests.
4. Coordinator: wire runtime router, native HTTP/stdio acceptance, regression suites, actual browser verification, documentation.
5. Independent review and repairs before final report.

Rulings: SDK1.30 supported maintenance line selected deliberately for dependency compatibility; no silent major upgrade. stdio server uses a fixed interpreter/module, not configurable shell commands. History permission is Report Agent plus persisted approval in the existing single-user local scope, not multi-tenant authorization. Deterministic selection exercises real MCP but is never called real LLM Tool Calling.

Evidence pending; record actual results in docs/validation/stage-3-mcp.md.
