# ADR 0001: .NET application core with Python AI runtime

Status: Accepted for bootstrap, 2026-11-07.

## Context

The portfolio has a 48-hour delivery window and must demonstrate Angular, .NET and applied AI engineering with an offline deterministic demo.

## Decision

Use a modular ASP.NET Core application with Domain, Application and Infrastructure boundaries. Python runs as one internal FastAPI service. Use typed HTTP contracts, PostgreSQL/pgvector, same-origin browser routing, and Docker Compose. Target .NET 10, Angular 20, Node 24 and Python 3.12 in containers.

## Alternatives

A single Python backend simplifies setup but misses the target .NET experience. A fleet of agents as independent services adds deployment and delivery failure modes before any useful workflow exists.

## Consequences

Two backend languages require contract tests and bounded network calls. The API owns identity and execution state; the runtime owns inference mechanics. A deterministic provider must be clearly identified in responses. SSE and database-backed dispatch precede any broker. Bootstrap folders for future capabilities are documentation boundaries, not completed features.

Stage 2 amendment: [ADR 0003](0003-agent-orchestration.md) supersedes the planned execution-state ownership above. The runtime owns durable coordination/state alongside its existing PostgreSQL adapter; .NET owns public workflow admission and contracts. This avoids two persistence adapters and a distributed coordinator for the local demonstration. No existing implemented execution API was replaced.
