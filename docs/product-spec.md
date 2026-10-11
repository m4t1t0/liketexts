# Product Specification — Substack-Style Platform

> The permanent product/business spec for Liketexts: reader/writer model,
> economics, paywall, endpoints, frontend requirements, testing strategy.
> Architecture decisions live in `docs/architecture.md` and `docs/adr/`.


## System Overview & Objectives
Build a production-ready Substack-like platform connecting Readers and Writers. 
- **Subscription Model:** Readers pay a global €9.95/month fee allowing them to subscribe to up to 5 writers simultaneously.
- **Paywall Model:** Posts consist of explicit `preview_content` (free to public) and `subscriber_content` (restricted to subscribers).
- **Architecture:** Flask backend (*Cosmic Python*) + Vue.js SPA frontend using REST APIs — see `docs/architecture.md`.

---

## Detailed Business Rules & Domain Logic

### 1. Subscription & Allocation Logic (`subscriptions` context)
- **Pricing:** Single global subscription model (€9.95/month).
- **Capacity:** Every active subscription grants **5 allocation slots** to follow writers.
- **Unallocated Slots:** Empty slots (`writer_id = NULL`) remain unused until assigned.
- **Allocation Changes & Anti-Fraud Budget:**
  - Readers have a budget of **2 slot change credits** per billing cycle month.
  - **Filling an empty slot:** Decrements empty slot count (e.g., 3/5 → 4/5). **Consumes 0 credits**.
  - **Swapping or removing an allocated slot:** Consumes **1 change credit**.
  - **Fraud Prevention:** If `change_credits == 0`, the system rejects any attempt to remove or swap an existing writer assignment until the next billing renewal event.
  - Track allocations via `AllocationLog` domain events to maintain audit trails.

### 2. Publishing & Paywalls (`publishing` context)
- **Newsletter Posts:**
  - `preview_content`: Text rendered for all readers (free public preview).
  - `subscriber_content`: Text rendered ONLY if the reader has an active, valid slot allocation for the post's author.
- **Archival Access:** Readers with active allocations to a writer can access past (archived) subscriber posts on the web app.
- **Publishing Schedule:** Writers can publish immediately or set a `scheduled_for` timestamp.

### 3. Async Email Dispatch Content Rules (`notifications` context)
- Sending is event-driven and asynchronous (worker + scheduler mechanics in
  `docs/architecture.md#asynchronous-processing`).
- Email content includes:
  - **Full Post:** Delivered to readers with an active allocation for the writer.
  - **Preview Only (+ Upsell):** Delivered to all non-subscribed followers/readers.

### 4. Payment Gateway
- Subscriptions start through a payment gateway abstraction: mock now, Stripe
  later — mechanics in `docs/architecture.md#payment-gateway-abstraction` and
  `docs/adr/0002-mock-payments-stripe-ready.md`.

---

## API Endpoints Specification

### Identity (`/api/v1/auth`)
* `POST /register` – User registration (email + password, optional first_name/last_name/avatar_url; no role — Reader/Writer capabilities are inferred from activity: writing a post grants writer, subscribing/following a writer grants reader)
* `POST /login` – Returns JWT access/refresh tokens
* `GET /me` – Profile state

### Subscriptions (`/api/v1/subscriptions`)
* `POST /subscribe` – Initiate €9.95/mo subscription (via Mock Gateway)
* `GET /allocations` – List active writer slots & remaining monthly change credits
* `POST /allocations/assign` – Allocate an empty slot to a writer (`writer_id`)
* `POST /allocations/swap` – Swap writer A for writer B (Deducts 1 credit)
* `DELETE /allocations/{writer_id}` – Release a writer slot (Deducts 1 credit)

### Writers Catalog (`/api/v1/writers`)
* `GET /` – Searchable list of public writers
* `GET /{writer_id}` – Writer profile & past public/subscriber newsletters

### Publishing (`/api/v1/posts`)
* `POST /` – Draft/Schedule newsletter (Fields: `title`, `preview_content`, `subscriber_content`, `scheduled_at`)
* `GET /feed` – Aggregated feed of newsletters for a reader based on allocations
* `GET /{post_id}` – Single post view (Applies content mask based on subscription status)

---

## Frontend Requirements (Vue 3)

1. **Reader Dashboard:**
   - Visual indicator showing 5 Slot Allocation Cards (Allocated vs. Empty).
   - "Change Budget" indicator showing remaining changes for the current cycle (e.g., "1/2 changes left").
   - Feed of recent newsletters from assigned writers.
2. **Writer Dashboard:**
   - Rich Markdown editor with explicit split fields: **Public Preview** vs. **Subscriber Only Content**.
   - Publishing/Scheduling controls and subscriber count metrics.
3. **Paywall UI:**
   - Clean inline visual banner at the end of `preview_content` prompting non-subscribers to allocate a slot to read the full post.

---

## Verification & Testing Requirements

1. **Unit Tests (`tests/unit/`):**
   - Test domain logic in pure Python without DB dependencies.
   - Verify allocation rules, unallocated slot handling, and fraud counter enforcement (`change_credits == 0`).
2. **Integration Tests (`tests/integration/`):**
   - Test SQLAlchemy repositories, Unit of Work transactions, and database operations.
   - Test `MockPaymentGateway` state transitions.
3. **API Tests (`tests/e2e/`):**
   - Flask client tests verifying access control rules for `subscriber_content` endpoint responses based on user session state.