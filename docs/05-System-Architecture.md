# 5. System Architecture — BillNova Phase 1

## 5.1 Overview

BillNova is a classic three-tier SaaS: a React SPA, a FastAPI backend, and PostgreSQL — all containerized and orchestrated with Docker Compose. Multi-tenancy is **shared-schema, row-level**: a single database where every business row carries `tenant_id`, enforced server-side.

```
┌──────────────────────────────────────────────────────────────────┐
│                          Browser (SPA)                             │
│  React + TS + Vite + Tailwind + ShadCN UI                          │
│  Routing: React Router   Server state: TanStack Query              │
│  Forms: React Hook Form + Zod   Client state: Zustand              │
│  Auth: JWT in memory (+ refresh); Axios interceptors               │
└───────────────▲───────────────────────────────────┬───────────────┘
                │  HTTPS  (Authorization: Bearer)     │  JSON
                │                                      ▼
┌───────────────┴──────────────────────────────────────────────────┐
│                        FastAPI Backend                             │
│  Routers → Services → Repositories                                 │
│  - Auth (JWT issue/verify, RBAC deps)                              │
│  - Tenant context middleware/dependency (tenant_id from token)     │
│  - Domain services: billing, gst, products, purchases,             │
│    inventory, subscription/usage, reports                          │
│  - Pydantic schemas (request/response)                             │
│  - SQLAlchemy 2.0 ORM + Alembic migrations                         │
│  - PDF (reportlab/weasyprint) + Excel (openpyxl) exporters         │
└───────────────┬───────────────────────────────────┬───────────────┘
                │  SQLAlchemy                          │
                ▼                                      ▼
┌──────────────────────────────┐      ┌────────────────────────────┐
│        PostgreSQL            │      │  (Phase 1: no external svc)  │
│  shared schema, tenant_id    │      │  No payment gateway, no MQ.  │
│  rows; indexes per §6        │      └────────────────────────────┘
└──────────────────────────────┘
```

## 5.2 Backend Layering

- **Routers (`api/`)** — thin HTTP layer: validate via Pydantic, call services, map errors.
- **Services (`services/`)** — business logic: GST math, atomic bill save, usage enforcement, stock movement, report aggregation.
- **Repositories (`repositories/`)** — DB access; every query is tenant-scoped by construction.
- **Models (`models/`)** — SQLAlchemy 2.0 declarative mapped classes.
- **Schemas (`schemas/`)** — Pydantic v2 request/response DTOs.
- **Core (`core/`)** — config, security (JWT, hashing), DB session, dependencies, error handlers.

Dependency rule: routers → services → repositories → models. No layer reaches upward.

## 5.3 Multi-Tenancy & Isolation

- JWT carries `tenant_id`. A FastAPI dependency extracts it and provides a **tenant-scoped session/context**.
- Repositories accept the tenant context and **always** add `WHERE tenant_id = :tid`. There is no code path that queries business tables without it.
- Direct access to another tenant's resource id returns `404` (existence not leaked).
- Defense in depth: composite indexes lead with `tenant_id`; unique constraints (e.g., product code, invoice number) are scoped `(tenant_id, …)`.

## 5.4 Authentication & Authorization

- **Tokens:** Short-lived access JWT (e.g., 30–60 min) + longer refresh token. Claims: `sub`, `tenant_id`, `role`, `iat`, `exp`, `type`.
- **Algorithm:** HS256 with a secret from env (`JWT_SECRET`). Rotatable per environment.
- **Passwords:** Passlib bcrypt.
- **Logout / revocation:** refresh tokens tracked (token version or revocation table) so logout invalidates them.
- **RBAC:** Two roles. `require_role("OWNER")` dependency guards owner-only endpoints; billing + product-read allowed for Cashier. Enforced on every route, never UI-only.

## 5.5 Subscription Enforcement

- A `subscription_guard` dependency runs before bill creation: checks status ∈ {Trial, Active} and `current_month_usage < plan_limit`.
- Usage counter incremented inside the same DB transaction as the sale (no double counting, no drift).
- 80% warning is computed and surfaced via the dashboard/usage endpoint; the SPA renders a banner.

## 5.6 Money & GST Computation

- All monetary values use `Numeric(12,2)` in DB and `Decimal` in Python — no floats.
- Rounding: half-up to 2 decimals at line level; bill totals are sums of rounded line values (documented, consistent).
- GST engine (pure functions, fully unit-tested) handles inclusive/exclusive and CGST/SGST vs IGST per place of supply.

## 5.7 Reporting & Export

- Report services aggregate via SQL (grouped queries) for performance.
- Exporters: **Excel** via `openpyxl`, **PDF** via `weasyprint` or `reportlab` (decided at build; both pure-Python/Docker-friendly).
- Exports reuse the exact figures from the on-screen report (single source of truth).

## 5.8 Frontend Architecture

- **Routing:** protected routes by auth + role; layout shell with sidebar nav.
- **Server state:** TanStack Query for all API reads/writes; query keys namespaced by resource + tenant.
- **Client state:** Zustand for POS cart + ephemeral UI state.
- **Forms:** React Hook Form + Zod schemas mirroring backend validation.
- **API client:** single Axios instance with interceptors (attach token, refresh on 401, normalize errors).
- **UI:** ShadCN components + Tailwind; consistent loading/empty/error/confirm primitives.
- **POS:** keyboard-first; cart in Zustand; debounced product search via TanStack Query.

## 5.9 Error Model

Uniform JSON error envelope:
```json
{ "error": { "code": "SUBSCRIPTION_LIMIT_REACHED", "message": "Monthly bill limit reached.", "details": {} } }
```
HTTP codes: `400/422` validation, `401` unauth, `403` forbidden/limit, `404` not found (incl. cross-tenant), `409` conflict, `500` server. Frontend maps `code` → user-friendly toast/banner.

## 5.10 Deployment (Docker Compose)

Services:
- `db` — postgres:16 with a named volume.
- `backend` — FastAPI (uvicorn/gunicorn); runs Alembic migrations on start; env-driven config.
- `frontend` — Vite build served by nginx (prod) / Vite dev server (dev).
- (optional) `adminer` for local DB inspection.

Networking: frontend → backend via `/api`; backend → db over the compose network. Secrets via env files (gitignored).

## 5.11 Configuration (env)

| Var | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres connection |
| `JWT_SECRET` | Token signing secret |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | Token TTLs |
| `TRIAL_DAYS` / `TRIAL_BILL_QUOTA` | Trial defaults |
| `DEFAULT_TIMEZONE` | `Asia/Kolkata` for usage windows |
| `CORS_ORIGINS` | Allowed SPA origins |
| `VITE_API_BASE_URL` | Frontend → backend base URL |

## 5.12 Observability & Quality (lightweight, Phase 1)

- Structured request logging + correlation id.
- Health endpoint `/api/health`.
- Pytest + coverage gate (≥80%) in CI; Ruff/Black for backend, ESLint/Prettier for frontend.
