# Initial threat model

This bootstrap exposes health endpoints and document ingestion/search/list/detail endpoints, with no authentication. Bind published ports to localhost. Do not deploy it to a public network. Knowledge operations accept bounded text or base64-encoded PDF/TXT/Markdown and use parameterized SQL. Metadata filtering is not tenant isolation.

Before execution endpoints ship, enforce JWT signature/issuer/audience/expiry, server-derived tenant identity, resource ownership, rate limits, input size bounds, and permission checks for every tool. Use explicit human approval records for sensitive actions. Treat retrieved text and model output as untrusted data; they cannot grant permissions.

Never accept connection strings, filesystem paths or arbitrary URLs from model output. Bound runtime timeouts and output sizes. Do not log prompts or tokens. Use fictional seed data, append-only audit records and a dedicated least-privilege database application role. The Compose initialization account is for local development only.

Dependencies require review before public deployment. Collector configuration is optional; application telemetry export and trace propagation remain future work.
