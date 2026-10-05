# Liketexts — Make targets (Docker-first, host stays clean).
# Host needs only Docker + Make. Everything Python runs inside the api image.
#
#   make start        # full stack up (api :5000 + db + redis + worker + beat + frontend)
#   make test         # pytest in api (T=tests/unit for a subset)
#   make logs SERVICE=api
#
# macOS: turn off AirPlay Receiver (it squats on port 5000).

COMPOSE := docker compose

SERVICE ?=
T ?= tests
MSG ?= Auto migration
REVISION ?= -1

.PHONY: help start develop stop restart logs ps build build-api test lint format typecheck openapi openapi-check openapi-client migrate upgrade downgrade seed shell ui-build clean

help: ## Show this help
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

start: ## Start full stack (api :5000 + frontend :5173)
	@test -f .env || cp .env.example .env
	$(COMPOSE) up --build -d
	@for i in $$(seq 1 60); do curl -sf http://localhost:5000/health >/dev/null && break || sleep 2; done
	@curl -sf http://localhost:5000/health >/dev/null && echo "API: http://localhost:5000  Frontend: http://localhost:5173" || (echo "API unhealthy — try: make logs SERVICE=api"; exit 1)
	$(COMPOSE) ps

develop: ## Start stack in foreground (streams logs, Ctrl-C stops)
	@test -f .env || cp .env.example .env
	$(COMPOSE) up --build

stop: ## Stop the stack
	$(COMPOSE) down

restart: stop start ## Restart the stack (down + up)

logs: ## Tail logs (SERVICE=api for one service)
	$(COMPOSE) logs -f --tail 200 $(SERVICE)

ps: ## Show service status
	$(COMPOSE) ps

build: ## Build all images
	$(COMPOSE) build

build-api: ## Build the api image only
	$(COMPOSE) build api

test: build-api ## Run pytest in api (T=tests/unit for a subset)
	$(COMPOSE) up -d db redis
	-$(COMPOSE) exec db psql -U liketexts -d liketexts -c "CREATE DATABASE liketexts_test"
	$(COMPOSE) run --rm -e TEST_DATABASE_URL=postgresql://liketexts:liketexts@db:5432/liketexts_test -e REDIS_URL=redis://redis:6379/0 -e CELERY_BROKER_URL=redis://redis:6379/1 -e CELERY_RESULT_BACKEND=redis://redis:6379/2 api python -m pytest $(T) -q

lint: build-api ## Ruff check in api
	$(COMPOSE) run --rm api ruff check backend app.py scripts

format: build-api ## Ruff format in api
	$(COMPOSE) run --rm api ruff format backend app.py scripts

typecheck: build-api ## Mypy in api
	$(COMPOSE) run --rm api mypy backend

openapi: build-api ## Regenerate docs/openapi.yaml
	$(COMPOSE) run --rm api python scripts/generate_openapi.py

openapi-check: build-api ## Verify docs/openapi.yaml is current
	$(COMPOSE) run --rm api python scripts/generate_openapi.py --check

openapi-client: ## Regenerate frontend TS client from docs/openapi.yaml (node container, no host Node)
	$(COMPOSE) run --rm frontend sh -c "npm install --prefer-offline --no-audit --no-fund >/dev/null && npx --yes openapi-typescript@7 /docs/openapi.yaml -o src/api/schema.ts"

migrate: build-api ## New autogenerate migration (MSG="...")
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$(MSG)"

upgrade: build-api ## Apply migrations
	$(COMPOSE) run --rm api alembic upgrade head

downgrade: build-api ## Downgrade migrations (REVISION=...)
	$(COMPOSE) run --rm api alembic downgrade $(REVISION)

seed: build-api ## Seed dev data
	$(COMPOSE) run --rm api python -m scripts.seed_dev

shell: ## Shell into the running api container
	$(COMPOSE) exec api bash

ui-build: ## Production build of the Vue SPA (frontend/dist)
	$(COMPOSE) run --rm frontend npm run build

clean: ## Remove Python/pytest caches on host
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type f -name '.coverage' -delete 2>/dev/null || true
