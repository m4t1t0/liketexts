# Liketexts — Build Status & Session Handoff

Source of truth for the product is still `PROMPT.md`; this file tracks **what is
built, what was deliberately deferred, and what is left**. Last updated after
`45b05c9` (backend suite: 88 passed; `mypy backend` and `ruff` clean;
`frontend` production build passes).

## How to run (details in `AGENTS.md`)

- Backend: `make start` (full Docker stack, api on `:5000`).
  Tests: `make test` (full suite) / `make test T=tests/unit`.
- Frontend: runs in Compose (`:5173`, see `make ps`). Types regen:
  `make openapi-client` (node container, no host Node needed).
- Spec freshness: `make openapi-check` (also enforced by
  `tests/test_openapi.py`).
- Local services: PostgreSQL DBs `liketexts` / `liketexts_test` (owner `rafa`,
  no password over local socket/TCP); Redis on `:6379` (broker db 1, backend
  db 2). `.env` / `.env.test` are git-ignored; `.env.example` is the template.

## Built — backend (`backend/`, Flask + Cosmic Python)

- **Identity**: `POST /register` (email + password, optional profile fields —
  **no role field**),
  `POST /login`, `POST /refresh` (rotating), `GET /me`
  (`id,email,created_at,is_writer,is_reader` — no `roles` array). Stateless JWT
  (15 min access + 30 day refresh), `sessions` table, writers catalog
  (`GET /api/v1/writers`, `GET /api/v1/writers/{id}`).
- **Roles are inferred from activity, never chosen**: first post grants WRITER
  (`PublishingService`), subscribe/assign/swap grants READER (subscription
  handlers). New users start with zero roles.
- **Subscriptions**: `POST /subscribe`, `GET /allocations`, assign / swap /
  release, 5 slots + 2 change credits per cycle (config-driven), allocation log
  + `writer_subscribers` / `writer_followers` read-model projections, payment
  webhooks (internal + Stripe shapes).
- **Publishing**: draft / scheduled / publish / cancel / update, reader feed
  (cursor pagination), writer's own posts, paywall masking
  (`preview_content` public, `subscriber_content` gated), archival access.
- **Notifications**: `PostPublished` → Celery tasks (email batching); currently
  a stub log (see ADR-0004).
- **Infra**: Alembic migrations `0001`–`0004`, `/health` + `/health/ready`
  (DB/Redis/migrations), per-user+IP rate limiting, JSON structured logs,
  `docs/openapi.yaml` generated from the live `url_map` (strict: undocumented
  routes fail generation).

## Built — frontend (`frontend/`, Vue 3 + Vite + TS)

Scaffold plus functional views against the real API: catalog home, login /
register (with first/last name), **reader dashboard** (slot cards,
change-budget indicator, subscribe/assign/swap/release, feed), **writer
dashboard** (split preview/subscriber form, scheduling, own posts + publish),
post view with paywall banner, writer detail. The logged-out homepage mirrors
Substack (sidebar nav, hero, public recent-posts feed with author
avatar/name, signup card, cookie-consent banner). Typed client in `src/api/`
generated from the spec; `VITE_API_URL` defaults to `http://localhost:5000`
(backend CORS already allows `:5173`). User profiles carry
first_name/last_name/avatar_url (`users` migration `0005`); post views expose
`writer_name`/`writer_avatar_url`; `GET /api/v1/posts/recent` serves the
public masked feed.

## Deliberately out of scope (see `docs/adr/`)

- Real email provider (stub log v1, ADR-0004); Stripe integration (mock
  gateway, ADR-0002); writer payouts (counts only, ADR-0003).

## Resolved (this pass)

- **Scheduled posts never auto-published** (was unreported): the Celery Beat
  container ran with an empty schedule. A `beat_schedule` entry (every 60s)
  now exists in `backend/src/notifications/tasks.py`.
- **Follow writers** (`PROMPT.md` line 74): `POST/DELETE
  /api/v1/writers/{id}/follow` with `is_following` on the writer detail;
  preview emails now reach "all non-subscribed followers".
- **Subscriber count metric** (`PROMPT.md` line 116): `GET /posts/writer`
  returns `subscriber_count`; `WriterSubscribersProjection` now also runs in
  the command-handler direct-persistence path (projections were bus-wired
  only, and subscription handlers don't publish via the bus).
- **Post editing UI**: inline editor in `WriterView.vue` via `PATCH /posts/{id}`.
- **Feed pagination UI**: "Load more" in `ReaderView.vue` (existing cursor API).
- **Catalog search box**: debounced search in `HomeView.vue` calling
  `GET /api/v1/writers?q=` (server-side; replaces client filtering).
- **Post endpoints 404/403**: `publish/schedule/cancel/update` now map domain
  errors (not found / not authorized) instead of returning 500.
- Code-review standards pass: deleted dead `identity/adapters/repository.py`
  duplicate; shared `get_bus`/`parse_uuid`/`as_status_str` helpers replace
  copy-paste across API modules; subscription repo exposes `session` publicly
  instead of a handler poking `_session`; dead `MAX_SLOTS`/`CREDITS_PER_CYCLE`,
  `LoggingEmailSender`, and `read_model.add_follower` removed; `assert`
  validation replaced with `ValueError`.

## Left to do (roughly ordered by value)

1. **SPA token refresh**: the client never calls `POST /auth/refresh`, so users
   are effectively logged out when the 15 min access token expires. Add silent
   refresh + retry on 401.
2. **Cancel-subscription endpoint**: gateway/service support it; no route.
3. **Rich Markdown editor**: `PROMPT.md` line 115 — split preview/subscriber
   fields exist, but they are plain textareas (labels mention Markdown). A
   real editor component (e.g. CodeMirror/Tiptap) is deferred.
4. **Frontend tests**: no vitest/Playwright setup yet.
5. **CI** (no `.github/`): run `pytest`, `ruff`, `mypy backend`,
   `make openapi --check`, and `npm run build` on PRs.
6. **Production deployment**: WSGI server (Flask dev server only today), static
   SPA hosting, managed Postgres/Redis, secret management.
7. **Cleanup / tech debt**:
   - `backend/tests/{unit,integration,e2e}/` are empty stale dirs — remove.
   - Writers catalog filters in memory (`list()` + `is_writer()`); fine now,
     revisit with real user volume.

## Doc map

- `PROMPT.md` — product spec (authoritative). `CONTEXT.md` — glossary
  (roles-as-derived-state is recorded here).
- `AGENTS.md` — agent runbook. `docs/adr/` — architecture decisions.
- `docs/openapi.yaml` — generated contract (never hand-edit).
