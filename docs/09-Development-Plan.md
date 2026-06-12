# 9. Development Plan — BillNova Phase 1

Sequenced milestones with goals, deliverables, and a definition of done. Ordered so the **highest-priority module (Billing/POS)** is reachable as early as its dependencies allow, and shippable value accrues each milestone.

## Guiding Principles

- Vertical slices: each milestone delivers a working, testable feature end-to-end (DB → API → UI).
- Backend tests written alongside features; coverage gate ≥80% enforced from M1.
- Commit small and often with conventional commits; keep `main` green.
- Don't overengineer — implement exactly what the FRD scopes.

---

## M0 — Project Scaffolding & DevOps  *(foundation)*

- **Goal:** One-command local environment.
- **Tasks:** Repo layout (§8); backend FastAPI app factory + config + health; PostgreSQL + SQLAlchemy + Alembic baseline; frontend Vite + TS + Tailwind + ShadCN + Router + Query + Axios shell; Dockerfiles + `docker-compose`; CI (lint + tests + coverage); `.env.example`s; README local-dev guide.
- **DoD:** `docker compose up` runs db + backend + frontend; `/api/health` green; empty test suite + coverage gate wired; SPA shell loads.

## M1 — Tenancy, Auth & RBAC

- **Goal:** Secure, isolated multi-tenant foundation.
- **Tasks:** Tenants, Users, SubscriptionPlans, TenantSubscriptions, BillUsage models + migrations; register (tenant+owner atomic), login, refresh, logout; JWT + password hashing; tenant-scoped session dep; `require_role`; cross-tenant 404; seed plans.
- **DoD:** Register/login/logout works; tenant isolation test passes (T1 can't see T2); RBAC enforced; ≥80% coverage on this slice.

## M2 — Product Management

- **Goal:** Catalog ready for billing.
- **Tasks:** Product model + migration; CRUD + search + pagination; unique code per tenant; soft-delete when referenced; Products UI (table, form with RHF+Zod, search, pagination, empty/error states).
- **DoD:** Full product CRUD via UI and API; duplicate-code 409; tests passing.

## M3 — GST Engine + Billing/POS  *(highest priority)*

- **Goal:** Fast, correct POS — the core of the product.
- **Tasks:**
  - `gst_service`: inclusive/exclusive, CGST/SGST/IGST, rounding — pure + exhaustively unit-tested.
  - `billing_service`: cart preview + atomic save (Sale, SaleItems, Payments, InventoryTransactions OUT, usage increment, invoice number).
  - Subscription guard (block at 100% / inactive) wired into save.
  - Payments incl. split (sum must equal grand total).
  - POS UI: keyboard-first product search, cart (qty/discount/notes/remove/clear), live preview, payment panel, save, print, reprint.
- **DoD:** Bill saves atomically; stock + usage update; split payments validated; GST math verified against worked examples (inclusive & exclusive, intra & inter); print + reprint work; POS usable via keyboard. Integration test covers full save + rollback.

## M4 — Purchases & Inventory

- **Goal:** Stock stays accurate from both directions.
- **Tasks:** Suppliers; Purchases + PurchaseItems (save → IN, cancel → compensating); InventoryTransactions ledger; current stock; manual adjustment (reason required); low-stock list; UI for purchases, stock, ledger, adjustments.
- **DoD:** Purchase increases stock; sale decreases stock; ledger balances reconcile; adjustments require reason; low-stock surfaces correctly.

## M5 — Subscription Visibility & Enforcement (complete)

- **Goal:** Full plan/usage lifecycle.
- **Tasks:** Usage endpoint with percent + 80% warning; monthly reset semantics (Asia/Kolkata); manual activate/upgrade endpoint; subscription UI panel; POS/dashboard warning + block banners.
- **DoD:** 80% warning shows; 100%/inactive blocks new bills with clear message; manual activation updates limits immediately; monthly window correct.

## M6 — Reports & Export

- **Goal:** Auditor-ready outputs.
- **Tasks:** Daily/Monthly sales; GST Summary (by rate); HSN Summary; Current Stock valuation; PDF (weasyprint/reportlab) + Excel (openpyxl) exporters reusing on-screen figures; Reports UI with date filters + export buttons.
- **DoD:** All reports match underlying data; PDF + Excel exports produce correct, identical figures; empty-range handled.

## M7 — Dashboard & Settings

- **Goal:** At-a-glance ops + configuration.
- **Tasks:** Dashboard KPIs endpoint + cards (today/monthly sales, bills, usage, low-stock); Settings (business profile, invoice prefix/footer, GST mode default, place of supply) + user management UI.
- **DoD:** Dashboard accurate per tenant; settings persist and apply to new invoices.

## M8 — Hardening, QA & Release Prep

- **Goal:** Production-ready Phase 1.
- **Tasks:** Coverage to ≥80% across backend; e2e smoke of critical flows (register→product→bill→report); polish loading/empty/error states + confirm dialogs; security pass (RBAC, isolation, secrets in env, password handling); performance check on POS save (<400ms target); finalize README + local dev guide; production compose + nginx.
- **DoD:** All ACs in §3 pass; coverage gate green; compose deploy verified; no P0/P1 defects open.

---

## Milestone Dependency Order

```
M0 ─▶ M1 ─▶ M2 ─▶ M3 ─▶ M4 ─▶ M5 ─▶ M6 ─▶ M7 ─▶ M8
                 (POS core)         (reports rely on M3/M4 data)
```

## Cross-Cutting (every milestone)

- Tests written with the feature; coverage gate enforced.
- Conventional commits; small PRs; `main` stays green.
- UI: consistent loading/empty/error/confirm states.
- No secrets in code; env-driven config; tenant isolation never bypassed.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| GST rounding disputes | Pure, table-tested `gst_service` with worked examples; document rounding rule. |
| Bill-save consistency under failure | Single DB transaction for sale+stock+usage; integration test for rollback. |
| Tenant data leakage | Isolation enforced in repositories + leading `tenant_id` indexes + explicit isolation tests. |
| POS speed | Debounced search, indexed lookups, lightweight preview endpoint, optimistic UI where safe. |
| Scope creep | FRD §1.6 out-of-scope list is the boundary; defer extras to later phases. |

---

## Sign-off

These nine deliverables define Phase 1. **Awaiting approval.** On approval, implementation proceeds milestone-by-milestone starting at **M0**. Open questions in FRD §1.8 should be answered at or before sign-off (trial defaults, negative-stock policy, invoice number format, manual-activation actor).
