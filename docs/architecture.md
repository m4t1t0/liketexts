# Architecture

Records the technical decisions for Liketexts; pair it with the ADRs in
`docs/adr/` and the business rules in `docs/product-spec.md`.

## Technical Stack

### Backend (Python / Flask)
* **Framework:** Flask 3.x with REST APIs
* **ORM / Database:** SQLAlchemy 2.0 + PostgreSQL
* **Task Queue / Scheduler:** Celery + Redis (email delivery & scheduled posts)
* **Authentication:** Stateless JWTs (Access + Refresh tokens)
* **Architecture:** Hexagonal / Clean Architecture (*Cosmic Python*)

### Frontend (Vue.js)
* **Framework:** Vue 3 (Composition API) + Vite
* **State Management:** Pinia
* **Router:** Vue Router
* **Styling:** Tailwind CSS

## Bounded Contexts

Organize the backend into explicit bounded contexts with low coupling:

```
backend/
├── src/
│   ├── identity/          # Authentication & User Management
│   ├── subscriptions/     # Reader Subscription, Allocations, Anti-Fraud
│   ├── publishing/        # Newsletters, Drafts, Scheduling, Posts
│   ├── notifications/     # Email Dispatching & Rendering
│   └── shared/            # Base Domain Events, Unit of Work, Bus
```

## Key Cosmic Python Building Blocks

1. **Domain Models (`domain/model.py`):** Pure Python entities and aggregates
   containing rich business logic. No SQLAlchemy dependencies inside domain
   models.
2. **Repository Pattern (`adapters/repository.py`):** Abstract base
   repositories with SQLAlchemy concrete implementations mapping domain
   entities to tables.
3. **Unit of Work (`service_layer/unit_of_work.py`):** Context manager
   managing transaction boundaries and event dispatching.
4. **Service Layer / Message Bus (`service_layer/services.py`,
   `service_layer/messagebus.py`):** Application services handling commands
   and events.
5. **CQRS Read Models:** Direct SQL queries via SQLAlchemy Core for heavy reads
   (e.g., Reader Newsfeed, Writer Catalog), bypassing domain models for
   performance.

See `docs/adr/0001-cosmic-python-flask-postgres.md`.
Native Python 3.14; stdlib dataclasses + enum only.

## Asynchronous Processing

* When a newsletter is published, a `PostPublished` domain event is fired.
* A background worker (Celery + Redis) consumes the event and dispatches email
  batches (full content to allocated readers, preview + upsell to followers —
  the business rules live in `docs/product-spec.md`).
* Scheduled posts are auto-published by a Celery Beat periodic task
  (`process_scheduled_posts`), which then enqueues the single email task.

Related: `docs/adr/0004-no-email-v1-provider-ready.md` (stub sender v1,
provider interface for Mailchimp later).

## Payment Gateway Abstraction

* Abstract interface `PaymentGatewayAdapter(ABC)` in `adapters/payments.py`.
* **Initial implementation:** `MockPaymentGateway` (simulates subscription
  lifecycle events, webhooks, active/failed states locally).
* **Future readiness:** `StripePaymentGateway` can implement
  `PaymentGatewayAdapter` and consume Stripe webhooks
  (`customer.subscription.created`, `invoice.payment_succeeded`).

See `docs/adr/0002-mock-payments-stripe-ready.md`.

## ADR Index

- `docs/adr/0001-cosmic-python-flask-postgres.md` — Cosmic Python on Flask + Postgres
- `docs/adr/0002-mock-payments-stripe-ready.md` — Mock payments, Stripe-ready
- `docs/adr/0003-no-payouts-v1.md` — No payouts v1, counts only
- `docs/adr/0004-no-email-v1-provider-ready.md` — No email v1, provider-ready
- `docs/adr/0005-api-scope-v1.md` — v1 API scope (lifecycle extras are intentional)
