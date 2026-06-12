# BillNova — Backend

FastAPI backend for **BillNova**, a subscription-based billing/POS SaaS for small retail businesses in India. Multi-tenant, GST-aware, JWT auth, no payment gateway in Phase 1 (subscriptions activated manually).

> Frontend repo: https://github.com/krish6622/BillNova_Frontend
> Phase 1 design docs live in [`docs/`](docs/) (FRD, user stories, acceptance criteria, use cases, architecture, ER diagram, API spec, dev plan).

## Tech Stack

FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · python-jose (JWT) · Passlib · PostgreSQL 16 · Pytest · Docker

## Layout

```
backend/
├─ app/
│  ├─ main.py            FastAPI app factory
│  ├─ core/              config, database, security, deps, error envelope
│  ├─ api/               routers (thin)         — /api/*
│  ├─ models/            SQLAlchemy models (per milestone)
│  ├─ schemas/           Pydantic DTOs
│  ├─ repositories/      tenant-scoped data access
│  └─ services/          business logic (GST, billing, subscription, …)
├─ alembic/              migrations
├─ tests/                unit / api / integration  (>=80% coverage gate)
├─ docs/                 Phase 1 design deliverables
├─ docker-compose.yml    db + backend
└─ Dockerfile
```

## Quick Start (Docker)

```bash
cp .env.example .env          # set a strong JWT_SECRET
docker compose up --build
```

- API: http://localhost:8000/api/health
- Swagger: http://localhost:8000/docs
- Postgres: localhost:5432 (billnova/billnova)

## Local Development (Python 3.11+)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env                                 # point DATABASE_URL at a local Postgres
alembic upgrade head
uvicorn app.main:app --reload                        # http://localhost:8000
pytest                                               # tests with >=80% coverage gate
```

## Configuration

Env vars only (never committed). See `.env.example`: `DATABASE_URL`, `JWT_SECRET`, token TTLs, trial defaults, `CORS_ORIGINS`.

## Milestones

M0 scaffolding ✓ · M1 tenancy/auth · M2 products · M3 GST + POS · M4 purchases/inventory · M5 subscriptions · M6 reports · M7 dashboard/settings · M8 hardening. See [`docs/09-Development-Plan.md`](docs/09-Development-Plan.md).
