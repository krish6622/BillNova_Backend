# BillNova — Phase 1 Documentation

BillNova is a subscription-based billing (POS) SaaS for small retail businesses in India — textile shops, fancy stores, footwear shops, gift shops, and general retail.

This folder contains the **Phase 1 design deliverables**. No application code is generated until these are approved.

## Deliverables (read in order)

| # | Document | Purpose |
|---|----------|---------|
| 1 | [01-FRD.md](01-FRD.md) | Functional Requirement Document — scope, modules, in/out of scope |
| 2 | [02-User-Stories.md](02-User-Stories.md) | User stories grouped by epic |
| 3 | [03-Acceptance-Criteria.md](03-Acceptance-Criteria.md) | Gherkin-style acceptance criteria per story |
| 4 | [04-Use-Cases.md](04-Use-Cases.md) | Detailed use cases with main/alternate flows |
| 5 | [05-System-Architecture.md](05-System-Architecture.md) | Components, auth, multi-tenancy, deployment |
| 6 | [06-Database-ER-Diagram.md](06-Database-ER-Diagram.md) | ER diagram + table specs + indexes |
| 7 | [07-API-Specifications.md](07-API-Specifications.md) | REST endpoints, payloads, error model |
| 8 | [08-Folder-Structure.md](08-Folder-Structure.md) | Backend + frontend folder layout |
| 9 | [09-Development-Plan.md](09-Development-Plan.md) | Milestones, sequencing, definition of done |

## Phase 1 Goal

Launch quickly, onboard real customers, validate the business model. Optimize for **simplicity, performance, maintainability, and UX**. Do not overengineer.

## Tech Stack (summary)

- **Frontend:** React + TypeScript + Vite + Tailwind + ShadCN UI + React Router + TanStack Query + React Hook Form + Zod + Zustand
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic + JWT + Passlib + Pytest
- **Database:** PostgreSQL
- **DevOps:** Docker + Docker Compose

## Key Decisions Locked for Phase 1

1. **No payment gateway** — subscription activation is manual (admin/owner-side).
2. **Multi-tenant, single database** — every business-owned row carries `tenant_id`; isolation enforced in the data-access layer.
3. **Two roles** — Owner (full access) and Cashier (billing + product view).
4. **Billing/POS is the highest-priority module.**
5. **GST inclusive & exclusive** pricing both supported, with CGST/SGST/IGST broken out internally for auditor-ready reports.

> **STATUS:** Awaiting approval. Code generation begins only after sign-off on these 9 documents.
