# ADR 0006: Stay on Flask (FastAPI migration declined for now)

Status: accepted

## Context

The question "what would a Flask → FastAPI migration cost?" keeps resurfacing
— the answer was researched in
[docs/research/flask-to-fastapi-migration.md](../research/flask-to-fastapi-migration.md).
Summary: the Cosmic Python layering keeps ~60% of the backend
framework-agnostic, so the migration is bounded (~3–5 focused days) — but the
OpenAPI-generation pipeline that couples `docs/openapi.yaml`, the generated TS
client, and the `openapi-check` contract test is the real cost, the API
surface is thin and synchronous, and Postgres (not Flask) is the latency.

## Decision

**Stay on Flask for v1.** No migration work is scheduled. The research note
is the standing methodology: if the question re-erupts, re-run its inventory
(line counts + coupling list) rather than re-deriving the analysis.

## Considered Options

- **Migrate now** — rejected: negative ROI (thin request handlers, native
  OpenAPI already exists contract-tested, Celery keeps the stack
  multi-runtime regardless).
- **Strangler/parallel v2 in FastAPI** — deferred until the revisit triggers
  exist (see research).

## Consequences

- New endpoints keep following the Flask blueprint + OpenAPI-annotation
  conventions; do not start "just this one route" in FastAPI.
- Revisit only when a trigger applies: websockets/SSE requirements, heavy
  async I/O in-request (e.g. an inline email provider), or a greenfield v2
  surface.
