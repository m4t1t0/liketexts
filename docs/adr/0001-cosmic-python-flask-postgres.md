# ADR 0001: Cosmic Python on Flask + PostgreSQL

Status: accepted

## Context

`docs/product-spec.md` requires a Flask backend with DDD, Hexagonal architecture, Unit of
Work, Repository pattern, and CQRS, plus stateless JWT auth and an API-only v1
(Vue SPA deferred). The team needs one documented way to structure bounded
contexts (`identity`, `subscriptions`, `publishing`, `notifications`, `shared`).

## Decision

- Flask 3.x with REST APIs under `/api/v1/`.
- SQLAlchemy 2.1 **imperative mapping** (domain models stay pure Python; mapping
  lives in `adapters/orm.py`), PostgreSQL in production.
- Repository ABCs in `adapters/repository.py` + SQLAlchemy implementations.
- Unit of Work context manager (abstract in `shared/service_layer/`, concrete
  `SqlAlchemyUnitOfWork` in `shared/adapters/unit_of_work.py`) + command/event
  message bus (`shared/service_layer/messagebus.py`).
- CQRS read models as event-driven projection tables (not materialized views).
- Stateless JWT: 15 min access (`sub`, `sid`), 30 day rotating hashed refresh
  in a `sessions` table.
- Alembic migrations are **hand-written**, following the existing numbered
  files (autogenerate is unreliable under imperative mapping — it produced an
  empty template plus constraint warnings for migration 0006; use `make
  migrate` as a scaffold only, then write the real migration).
- Seed script `python -m scripts.seed_dev` (idempotent).
- **Postgres everywhere** (dev, test, prod). SQLite support was removed
  (2026-10) as dead-path code: no supported environment used it — the test
  suite always ran against Postgres, and the SQLite branches in the UoW and
  health check were untested.

## Consequences

- Domain stays DB-free, but repositories must translate persistence concerns
  (e.g. User roles set <-> JSON column) without leaking ORM into the domain.
- Projections must be registered on the bus **and** written explicitly by
  handlers: subscription command handlers mutate aggregates without publishing
  via the bus, so `AllocationChanged` projections (allocation_log,
  writer_subscribers) are also persisted directly in `_persist_allocation_log`.
  Silent event loss is a real failure mode — `WriterSubscribersProjection` was
  bus-wired only and `writer_subscribers` stayed empty until the direct
  persistence path was added (2026-10). `SubscriptionStatusProjection` is the
  same class of open issue (see `docs/STATUS.md`).
- SQLite is test/dev bootstrap only; Postgres semantics (e.g. upserts) must be
  gated or avoided in shared code paths.
