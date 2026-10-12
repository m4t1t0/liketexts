# Liketexts - Agent Instructions

Product spec: `docs/product-spec.md`. Architecture: `docs/architecture.md`
(tech stack, bounded contexts, Cosmic Python building blocks, async processing,
payment gateway) and per-decision `docs/adr/`. `PROMPT.md` is a transient
grilling-session workspace, usually empty.

## Agent skills

### Issue tracker

Engineering-flow tickets are Trello cards on the Liketexts board
(Backlog / In Progress / Done), driven through the Trello MCP tools. See
`docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `GLOSSARY.md` at the root + `docs/adr/`. See
`docs/agents/domain.md`.

## Run the App
```bash
make start
```
API on http://localhost:5000, frontend on http://localhost:5173.
Host needs only Docker + Make — all Python runs inside containers.

## Make Commands
```bash
make start        # Full stack up (api + db + redis + worker + beat + frontend)
make develop      # Same stack in foreground (streams logs)
make stop         # Stack down
make restart      # Restart stack
make logs SERVICE=api  # Tail logs
make ps           # Service status
make test         # Pytest in api (T=tests/unit for a subset)
make lint         # Ruff check in api
make typecheck    # Mypy in api
make openapi      # Regenerate docs/openapi.yaml (openapi-check to verify)
make openapi-client # Regenerate frontend TS client (node container, no host Node)
make migrate MSG="..."  # New autogenerate migration
make upgrade      # Apply migrations
make help         # List all targets
```

## Install Dependencies

No host install needed. `requirements.txt` is baked into the Docker image
(`make build-api` rebuilds it). Host needs only Docker + Make.

## Project Structure
- `app.py` - Application factory with Flask app creation
- `backend/` - Flask API (Cosmic Python); `frontend/` - Vue 3 SPA (Vite, Pinia, Router, Tailwind; types generated from `docs/openapi.yaml` via `make openapi-client`)
- `Makefile` - Make targets (start/stop/test/lint, all Docker-based)
- `requirements.txt` - Baked into the Docker image (no host install needed)
- `PROMPT.md` - Transient grilling-session workspace (usually empty; do not
  put documentation here)
- `docs/product-spec.md` - Permanent product spec (business rules)
- `docs/architecture.md` - Technical stack, bounded contexts, Cosmic Python
  building blocks, async processing, payment gateway abstraction
- `docs/openapi.yaml` - Generated API spec (do not edit; run `make openapi`)
- `docs/STATUS.md` - Build status & handoff (what's built, what's left)
- `GLOSSARY.md` - Ubiquitous language glossary
- `docs/adr/` - Architecture Decision Records
- `backend/src/identity/` - Authentication & User Management (single User, Reader/Writer capabilities, JWT); `api_auth.py` shared Flask auth helpers; `writers_api.py` Writers Catalog (`GET /api/v1/writers`)
- `backend/src/subscriptions/` - Subscription, Allocation Slots (5), Change Credits (2), config-driven
- `backend/src/publishing/` - Posts with preview_content / subscriber_content, scheduled_for, archival access
- `backend/src/notifications/` - PostPublished handling, stub log v1 (Mailchimp later)
- `backend/src/shared/` - Base events, UoW, bus, config
- `backend/src/adapters/payments.py` - PaymentGatewayAdapter ABC + MockPaymentGateway (Stripe later)

## Notes
- Uses Python 3.14 (inside the Docker image; no host venv needed)
- Host needs only Docker + Make
- Architecture: Cosmic Python (DDD + Hexagonal + UoW + Repository + CQRS),
  bounded contexts, and Cosmic Python building blocks — see
  `docs/architecture.md` and
  `docs/adr/0001-cosmic-python-flask-postgres.md`
- Database: PostgreSQL with SQLAlchemy 2.0 Imperative Mapping + Alembic migrations
- Auth: Stateless JWT (Access + Refresh)
- Scope v1: API-only (Vue SPA deferred) — see `docs/adr/0005-api-scope-v1.md`
- Economics configurable (price/slots/credits in config, not hardcoded); writers publish free; readers pay to read
- Payments: Mock now, Stripe-ready — see `docs/architecture.md#payment-gateway-abstraction` and `docs/adr/0002-mock-payments-stripe-ready.md`
- No writer payouts v1, counts only — see `docs/adr/0003-no-payouts-v1.md`
- Email: stub log v1, provider interface for Mailchimp later — see
  `docs/architecture.md#asynchronous-processing` and `docs/adr/0004-no-email-v1-provider-ready.md`
- Testing: pytest with unit, integration, and e2e (Flask client paywall checks)
- Default port: 5000 (macOS: AirPlay Receiver can squat on :5000 and block the
  API bind — disabling it resolves this; confirmed fixed in this environment)
- `start`/`develop`/`stop`/`restart` manage the Docker Compose stack; `local` runs Flask directly on the host (`--port`, `PORT` env honored by `app.py`; `--debug` enables the reloader via `FLASK_DEBUG=true`)
