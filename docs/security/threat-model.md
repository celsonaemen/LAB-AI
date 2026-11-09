# Threat model — internal AI workspace

Status: development/homologation with synthetic data. There is no production bank security approval. No claim of invulnerability, certification or zero leakage is made.

Assets include document bodies, vector embeddings (sensitive derived data), metadata, prompts, reports, execution events, JWTs and the runtime service credential. The browser, public .NET gateway, Python runtime, MCP subprocess, PostgreSQL and model server are separate trust boundaries.

Development permits anonymous business access and must remain loopback-only with synthetic data. Outside Development, .NET requires configured JWT authentication and Python requires a service token. JWT policies check issuer, audience, lifetime, workspace and permission. The synthetic customer endpoints also check customer claims. Generic knowledge and execution endpoints still grant workspace-level access: metadata filters do not establish tenant/customer isolation.

## Implemented outbound controls

- Both Ollama tool selection and report generation accept only a loopback origin. Remote/private-network hosts, credentials in URLs, custom paths, queries and fragments are rejected before transport. `localhost` is normalized to a numeric loopback address without DNS resolution.
- The Python model HTTP transport ignores proxy environment variables and rejects redirects. Requests have time and response-size bounds.
- The .NET runtime HTTP clients disable redirects, environment/system proxies and cookies. The runtime credential is registered only on the four dedicated runtime clients, not every future HTTP client.
- FastEmbed requires a pre-provisioned local cache (`local_files_only=True`). A missing model fails; serving does not download a replacement. Operators must verify and stage approved model artifacts separately.
- Browser dictation and synthesis are disabled through the voice adapter. No browser speech API is invoked. Local speech processing is not implemented yet.
- FastAPI validation failures return a generic error without echoing rejected values.

These application controls are not a host-wide egress firewall. They do not restrict the independently installed model server, database driver, operating system, IdP discovery, third-party libraries, extensions, backups, monitoring agents or another process.

## Existing input and tool controls

Knowledge operations accept bounded text or base64 PDF/TXT/Markdown and use parameterized SQL. Tool schemas, per-agent permissions, explicit approval for history, tool/output/round/time limits and server-side checks are enforced. Retrieved content is untrusted; it cannot grant permissions. Prompt-injection heuristics and citation-ID validation are defense layers, not proof of semantic correctness or complete injection resistance.

## Blocking gaps before real customer data

1. Derive customer/document/execution scope from verified identity on every route and every MCP tool. Scope list, detail, search, events, approval and cancellation consistently. Add cross-user/customer denial tests. Current generic endpoints and MCP document/history access are not isolated per customer.
2. Integrate corporate sign-in/MFA and authenticated browser event streaming; implement separation of requester and approver where required. Current approval records do not prove four-eyes separation.
3. Deploy gateway/runtime/database/model in segmented networks with default-deny egress. Permit only explicitly approved identity, model, database and monitoring destinations. Validate actual traffic with packet capture in that environment.
4. Configure verified TLS/mTLS, dedicated least-privilege database roles, encryption at rest for database/volumes/backups, managed keys, secret rotation and restore tests. None is established by a local code change.
5. Protect execution events and intermediate results as sensitive records. Define retention, deletion, export controls and tamper-evident audit storage. Redaction and a release SHA-256 are not encryption or signed immutable audit.
6. Scan dependencies, containers and model artifacts; pin approved artifacts; run SAST/DAST, resource-exhaustion tests and independent penetration testing. Establish incident response and monitored alerts.

Keep real bank data out of this environment until these controls are implemented and verified by the responsible organization.

For executed tests and their limits, see `../validation/local-privacy-hardening.md`.
