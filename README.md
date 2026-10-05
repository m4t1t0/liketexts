# Liketexts

A Substack-style platform connecting **Readers** and **Writers**. Readers pay a
global €9.95/month fee to follow up to 5 writers simultaneously; posts have
public `preview_content` plus `subscriber_content` gated behind the paywall.

Product spec: [`PROMPT.md`](PROMPT.md) (authoritative).
Build status & handoff: [`docs/STATUS.md`](docs/STATUS.md).

## Stack

- **Backend**: Flask 3 + SQLAlchemy 2.1 + PostgreSQL, Celery + Redis, stateless
  JWT auth — organized as bounded contexts (Cosmic Python: DDD, Unit of Work,
  Repository, CQRS). See [`docs/adr/`](docs/adr/).
- **Frontend**: Vue 3 SPA (Vite, Pinia, Router, Tailwind); API types generated
  from [`docs/openapi.yaml`](docs/openapi.yaml) via `npm run openapi`.
- **Infra (v1)**: Postgres + Redis only. Payments are mocked, email is a stub
  log, avatars are local files — no Stripe/SMTP/S3 needed.

## Quickstart (Docker / Orbstack)

```bash
cp .env.example .env   # optional: overrides for secrets & non-default config
docker compose up --build
```

| Service  | URL                   |
| -------- | --------------------- |
| API      | http://localhost:5000 |
| Frontend | http://localhost:5173 |
| Postgres | localhost:5432        |
| Redis    | localhost:6379        |

Health: `GET /health`, readiness (db + redis + migrations): `GET /health/ready`.

> macOS: turn off **AirPlay Receiver** (uses port 5000) or the API forward
> won't bind — recreate the container after (`docker compose up -d --force-recreate api`).

## Local dev (no Docker)

```bash
python -m invoke start      # API on :5000 (no reloader); `develop` for hot reload
python -m invoke ui         # Vite dev server on :5173
python -m invoke --list     # all tasks
```

Needs local Postgres (`liketexts` / `liketexts_test`) + Redis on `:6379`;
see `.env.example`. Agent instructions: [`AGENTS.md`](AGENTS.md).

## Testing

```bash
# In Docker (service hostnames):
docker compose run --rm -e TEST_DATABASE_URL=postgresql://liketexts:liketexts@db:5432/liketexts_test \
  api python -m pytest tests/ -q
# Locally: pytest tests/   (uses liketexts_test + localhost Redis)
```

98 tests (unit + integration + e2e paywall). Also: `invoke lint`,
`invoke typecheck`, `invoke openapi --check`.

## Structure

- `app.py` — Flask factory (`/health`, `/health/ready`, blueprints, handlers)
- `backend/src/identity/` — auth, JWT, profiles, avatar uploads, writers catalog
- `backend/src/subscriptions/` — subscribe, 5 allocation slots, 2 change credits
- `backend/src/publishing/` — drafts, scheduling, publishing, feed, paywall
- `backend/src/notifications/` — `PostPublished` → Celery email tasks (stub v1)
- `backend/src/shared/` — config, UoW, message bus, logging, OpenAPI builder
- `backend/alembic/` — migrations (`alembic upgrade head` runs on API boot)
- `frontend/src/` — Vue SPA (`api/client.ts`, router, stores, views)
- `docs/` — `openapi.yaml` (generated, don't edit), `STATUS.md`, `adr/`
