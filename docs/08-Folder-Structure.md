# 8. Development Folder Structure — BillNova Phase 1

Monorepo with `backend/`, `frontend/`, and root-level DevOps files.

```
BillNova/
├─ docs/                          # these Phase-1 deliverables
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # FastAPI app factory, router mount, middleware
│  │  ├─ core/
│  │  │  ├─ config.py             # pydantic-settings; env vars
│  │  │  ├─ security.py           # JWT issue/verify, password hashing
│  │  │  ├─ database.py           # engine, session, Base
│  │  │  ├─ deps.py               # get_current_user, get_tenant_ctx, require_role, subscription_guard
│  │  │  └─ errors.py             # error envelope + exception handlers
│  │  ├─ models/                  # SQLAlchemy 2.0 models (one file per aggregate)
│  │  │  ├─ tenant.py user.py product.py supplier.py
│  │  │  ├─ purchase.py sale.py payment.py
│  │  │  ├─ inventory.py subscription.py usage.py
│  │  ├─ schemas/                 # Pydantic v2 DTOs (mirror models/routes)
│  │  │  ├─ auth.py user.py product.py purchase.py
│  │  │  ├─ sale.py inventory.py subscription.py report.py dashboard.py settings.py
│  │  ├─ repositories/            # tenant-scoped DB access
│  │  │  ├─ base.py               # TenantRepository (always filters tenant_id)
│  │  │  ├─ product_repo.py sale_repo.py purchase_repo.py
│  │  │  ├─ inventory_repo.py subscription_repo.py usage_repo.py user_repo.py
│  │  ├─ services/                # business logic
│  │  │  ├─ auth_service.py
│  │  │  ├─ gst_service.py        # pure GST math (inclusive/exclusive, cgst/sgst/igst)
│  │  │  ├─ billing_service.py    # atomic bill save, preview
│  │  │  ├─ product_service.py purchase_service.py
│  │  │  ├─ inventory_service.py
│  │  │  ├─ subscription_service.py  # usage increment, guard, manual activate
│  │  │  ├─ report_service.py
│  │  │  └─ export_service.py     # pdf + excel
│  │  ├─ api/                     # routers (thin)
│  │  │  ├─ auth.py users.py products.py suppliers.py
│  │  │  ├─ purchases.py sales.py inventory.py
│  │  │  ├─ subscription.py reports.py dashboard.py settings.py health.py
│  │  └─ utils/                   # money/decimal, invoice numbering, dates(tz)
│  ├─ alembic/
│  │  ├─ versions/                # migrations
│  │  └─ env.py
│  ├─ tests/
│  │  ├─ conftest.py              # test app, db fixtures, auth helpers
│  │  ├─ unit/                    # gst_service, billing math, usage
│  │  ├─ api/                     # endpoint tests per router
│  │  └─ integration/             # full bill-save flow, tenant isolation
│  ├─ seeds/seed_plans.py         # subscription plans + optional demo data
│  ├─ pyproject.toml              # deps, ruff/black, pytest+coverage config
│  ├─ alembic.ini
│  ├─ Dockerfile
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  │  ├─ main.tsx App.tsx         # bootstrap + router
│  │  ├─ routes/                  # route definitions + protected route guards
│  │  ├─ pages/
│  │  │  ├─ Login.tsx Register.tsx
│  │  │  ├─ Dashboard.tsx
│  │  │  ├─ pos/POS.tsx           # billing screen (highest priority)
│  │  │  ├─ products/ purchases/ inventory/ reports/ settings/
│  │  ├─ components/
│  │  │  ├─ ui/                   # ShadCN components
│  │  │  ├─ layout/               # AppShell, Sidebar, Topbar
│  │  │  └─ common/               # Async, EmptyState, ErrorState, ConfirmDialog
│  │  ├─ features/                # per-domain hooks + api + types
│  │  │  ├─ auth/ products/ sales/ purchases/
│  │  │  ├─ inventory/ subscription/ reports/ dashboard/
│  │  ├─ lib/
│  │  │  ├─ api.ts                # Axios instance + interceptors
│  │  │  ├─ queryClient.ts        # TanStack Query setup
│  │  │  └─ utils.ts money.ts
│  │  ├─ stores/                  # Zustand (cart, ui)
│  │  ├─ schemas/                 # Zod schemas (mirror backend validation)
│  │  └─ styles/                  # tailwind globals, tokens
│  ├─ index.html
│  ├─ package.json tsconfig.json vite.config.ts
│  ├─ tailwind.config.ts components.json   # ShadCN config
│  ├─ Dockerfile nginx.conf
│  └─ .env.example
├─ docker-compose.yml
├─ docker-compose.dev.yml
├─ Makefile                       # up/down/migrate/seed/test/lint shortcuts
├─ README.md
└─ .gitignore
```

## Conventions

- **Backend:** routers thin → services hold logic → repositories own all DB access (tenant-scoped). GST math isolated in `gst_service` (pure, fully unit-tested).
- **Frontend:** feature-folder pattern; each feature exposes typed hooks built on TanStack Query + the shared Axios client. No direct `fetch`. Reusable `Async`/`EmptyState`/`ErrorState`/`ConfirmDialog` primitives for consistent states.
- **Tests** live beside the backend, split unit/api/integration; coverage gate ≥80%.
- **Migrations** via Alembic only; never auto-create tables in prod.
