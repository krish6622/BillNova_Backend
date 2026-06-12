# CR-1 — Deliverable 2: Database Changes

Schema design for CR-1. Migration implementation follows in **Deliverable 3**.
Recommended answers approved: NOS default-only, backfill margin as fixed amount, `selling_price` stored-derived, inline-duplicate code rejects the purchase.

---

## 2.1 `products` table — target schema

| Column | Type | Change | Notes |
|--------|------|--------|-------|
| id | UUID PK | — | |
| tenant_id | UUID FK→tenants | — | isolation key |
| product_code | VARCHAR(50) | — | auto `PD-#####`, unique per tenant |
| name | VARCHAR(255) | — | required; duplicates allowed |
| ~~category~~ | ~~VARCHAR(100)~~ | **DROP** | category removed entirely |
| unit | VARCHAR(20) | default → **`NOS`** | app-level default only; existing rows untouched |
| purchase_price | NUMERIC(12,2) | — | must be > 0 (validated) |
| **margin_type** | VARCHAR(10) | **ADD** | `percentage` \| `amount`; server_default `percentage` |
| **margin_value** | NUMERIC(10,2) | **ADD** | server_default `0`; ≥ 0 |
| selling_price | NUMERIC(12,2) | semantics change | **stored, derived** from purchase_price + margin (never hand-edited) |
| gst_percentage | NUMERIC(5,2) | — | |
| hsn_code | VARCHAR(20) | — | |
| current_stock | NUMERIC(12,3) | — | purchase/sale/adjust driven |
| reorder_level | NUMERIC(12,3) | — | |
| is_active | BOOLEAN | — | soft-disable (no delete) |
| created_at / updated_at | TIMESTAMPTZ | — | |

**Derived selling price (computed at write):**
- `percentage`: `selling_price = round(purchase_price × (1 + margin_value/100), 2)`
- `amount`: `selling_price = round(purchase_price + margin_value, 2)`

## 2.2 Constraints

- `UNIQUE (tenant_id, product_code)` — **already present** (`uq_product_code_tenant`); reaffirmed.
- Product name: no uniqueness.
- `margin_type` restricted to `{percentage, amount}` at the app layer (no DB enum, for migration simplicity).

## 2.3 Indexes (products)

| Index | Status |
|-------|--------|
| `ix_products_tenant_id` (tenant_id) | exists |
| `uq_product_code_tenant` (tenant_id, product_code) | exists |
| `ix_products_name` (name) | exists |
| `ix_products_hsn_code` (hsn_code) | exists |
| `ix_products_is_active` (is_active) | exists |
| **`ix_products_tenant_created` (tenant_id, created_at)** | **ADD** (Recent Products / fast tenant-scoped listing) |

## 2.4 Backfill (existing rows)

```sql
-- every existing product gets a fixed-amount margin inferred from current prices
UPDATE products
   SET margin_type  = 'amount',
       margin_value = GREATEST(COALESCE(selling_price,0) - COALESCE(purchase_price,0), 0);
```
- `selling_price` values are **left unchanged** (already correct historically).
- `unit` values left unchanged (existing `PCS` stay `PCS`; only the new-row default becomes `NOS`).

## 2.5 Category removal

- BillNova never had a separate `categories` table — category was only `products.category` (a column).
- Migration drops the column. No FK/table teardown required. POS category usage is replaced by Recent/Top-Selling (UI layer).

## 2.6 Tenant-isolation (structural reaffirmation)

No schema change needed for isolation — every business table already carries `tenant_id` and leads its composite
indexes/uniques with it (tenants, users, products, suppliers, purchases, purchase_items, sales, sale_items,
payments, inventory_transactions, bill_usage, tenant_subscriptions). The CR-1.7 fix is in the **repository audit
(Deliverable 7)** and **frontend cache** — not the schema. Indexes above keep tenant-scoped reads fast.

## 2.7 SQLAlchemy model delta (`app/models/product.py`)

```python
# remove:
category: Mapped[str | None] = mapped_column(String(100), nullable=True)

# add:
margin_type: Mapped[str] = mapped_column(String(10), default="percentage")
margin_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

# change default:
unit: Mapped[str] = mapped_column(String(20), default="NOS")   # was "PCS"
# selling_price stays a stored column, but is set by the service from margin (never client-supplied)
```

## 2.8 No other tables change

purchases / purchase_items / sales / sale_items / payments / inventory_transactions / suppliers / subscriptions /
bill_usage / tenants / users — **unchanged**. Purchase already drives inventory IN; CR-1's purchase-creates-product
logic is service-layer (Deliverable 6), not schema.

---

> **STOP — Deliverable 2 (Database Changes).** Approve to proceed to **Deliverable 3: Alembic Migration Plan**
> (migration `0006` — drop category, add margin columns + backfill, add `(tenant_id, created_at)` index; data-preserving, validated against Neon).
