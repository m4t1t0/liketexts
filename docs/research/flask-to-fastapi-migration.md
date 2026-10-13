# Research: Migrating from Flask to FastAPI

*Date: 2026-10-13 · Question: "What is the cost of migrating the backend from
Flask to FastAPI?" · Conclusion: moderate cost, small payoff today — see the
decision in [ADR-0006](../adr/0006-stay-on-flask.md).*

## TL;DR

The migration is **bounded, not a rewrite** — the Cosmic Python layering keeps
~60% of the backend framework-agnostic — but the real price is the
OpenAPI-generation pipeline that couples `docs/openapi.yaml`, the generated TS
client, and the contract test. Realistic elapsed cost is **3–5 focused days**
of agent-assisted work plus frontend type churn. Payoff today is small
because the API surface is thin, synchronous, and already has a
contract-tested spec. Decision: **stay on Flask** (ADR-0006), with explicit
revisit triggers.

## What survives untouched (~60% of the backend)

The domain/adapters/service split pays off:

- **Domain models** (`User`, `Post`, `Subscription`) — pure Python, zero
  Flask imports.
- **Adapters** — SQLAlchemy repositories, ORM imperative mappings, CQRS read
  models, payment gateways, email stub.
- **Service layer** — message bus, unit of work, command handlers;
  framework-agnostic.
- **Celery tasks + beat schedule, Alembic migrations, config** — untouched.
- **Domain/integration tests** — only e2e tests touch the Flask test client.

## What must be rebuilt (~2,600 lines of Flask-coupled surface)

| Component | Lines | Effort | Notes |
| --- | --- | --- | --- |
| `app.py` | 583 | Medium | Factory → FastAPI lifespan; per-command bus/UoW wiring becomes FastAPI dependency injection |
| API modules (`identity`, `publishing`, `subscriptions`, `writers`) | ~770 | Medium | Blueprints → routers; handlers stay thin; RFC7807 error mapping → exception handlers |
| `identity/api_auth.py` | 78 | Small | JWT helpers → `Depends()`; genuinely nicer in FastAPI |
| `shared/api.py` | 28 | Trivial | `get_bus()` → dependency; `parse_uuid` unchanged |
| `tests/conftest.py` + ~50 e2e tests | ~118 + tests | Medium | Flask test client → `httpx`/`TestClient`; mechanical, many files |
| `shared/openapi.py` | 1,083 | **High** | The hidden cost — see below |
| Middleware (request-id logging, rate limiting) | ~99+ | Small | Rewrite as ASGI middleware |
| Avatar file serving | 101 | Small | `send_from_directory` → `FileResponse` |

## The OpenAPI pipeline is the real cost

`shared/openapi.py` (1,083 lines) generates `docs/openapi.yaml` from
`app.url_map` + hand-written annotations, verified by
`tests/test_openapi.py::test_openapi_yaml_is_current` (`make openapi-check`),
and feeds the generated TS client (`make openapi-client`,
`frontend/src/api/schema.ts`).

FastAPI would replace it with native generation — but:

1. The generated spec shape differs (operation ordering, schema names,
   response envelopes), so **`docs/openapi.yaml` churns wholesale**.
2. The TS client regenerates with different type names/shapes; every
   `S["..."]` reference in `frontend/src/api/client.ts` and views is touched.
3. The contract test (`openapi-check`) needs a rethink — FastAPI guarantees
   currency by construction, which is a genuine simplification, but the
   "spec drift breaks CI" safety property must be re-established.

## Risk register

- **Silent contract drift** — spec-shape changes breaking frontend calls not
  covered by e2e tests (mitigated by: paywall/auth flows are well covered).
- **Auth/session subtleties** — cookie/header handling differences between
  Werkzeug and Starlette (mitigated by: `test_auth_integration.py`).
- **Feature freeze during migration** — the repo holds still while parity is
  kept green.

## What would be gained

- Native async endpoints + DI — real, but current endpoints are thin
  CRUD-over-bus calls; Flask is not the bottleneck (Postgres is the latency).
- Native OpenAPI generation — but the existing pipeline already provides it
  with a drift guard.
- No framework-elimination win: Celery stays regardless, so the stack
  remains multi-runtime either way.

## Revisit triggers (from ADR-0006)

1. Websockets or server-sent events become product requirements.
2. Handlers do heavy async I/O in-request (e.g. a real email provider called
   inline instead of via Celery).
3. A greenfield v2 surface is designed — consider building it in FastAPI
   alongside Flask rather than migrating v1.

Re-running this research with updated line counts is cheap: the coupling
inventory above is the methodology.
