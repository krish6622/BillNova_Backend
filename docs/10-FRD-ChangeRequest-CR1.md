# BillNova — FRD Change Request CR-1 (Purchase-Driven Products + Tenant Isolation)

**Type:** Product redesign + critical bug-fix release
**Status:** Deliverable 1 of 9 — awaiting approval before DB changes.

This document updates [01-FRD.md](01-FRD.md). Where they conflict, CR-1 wins.

---

## CR-1.0 Summary & Rationale

Small Indian retailers don't maintain a product master separately — **purchases create products**. CR-1 removes
standalone product creation, makes Purchase Entry the source of truth, derives selling price from a profit margin,
drops Category, auto-generates product codes, standardises the unit to **NOS**, and hardens **multi-tenant isolation**.

---

## CR-1.1 Remove Standalone "Add Product"

- **Remove:** Add Product button, create page/modal, and the **`POST /api/products`** endpoint.
- **Remove:** product **deletion** (`DELETE /api/products/{id}`). Deletion is never allowed.
- Products become **read-only master records** created via purchases.
- **Keep:** Product **List**, **Search**, **Edit** (limited fields), **Status toggle** (Active/Inactive via soft-disable `is_active`).

**FR:** A user can never create or hard-delete a product directly. Deactivation hides it from POS/search but preserves history.

## CR-1.2 Purchase Becomes Product Creation

Purchase Entry supports, per line, **either**:
- **Select existing product** (search → pick), **or**
- **Create new product inline** (no separate navigation).

On save, any inline-new product is created first (auto code, margin → selling price), then the purchase proceeds
(stock IN, ledger, totals) — **atomically** in one transaction.

**Purchase line fields:** Product Code, Product Name, HSN Code, GST %, Purchase Price, Profit Margin Type,
Profit Margin Value, **Calculated Selling Price (read-only)**, Quantity, Unit.

## CR-1.3 Profit-Margin-Based Selling Price

- Selling Price is **always derived** and **read-only** (never hand-edited).
- **Percentage:** `selling = purchase_price × (1 + margin/100)` → e.g. 100 @ 25% = **125**.
- **Fixed Amount:** `selling = purchase_price + margin` → e.g. 100 + 20 = **120**.
- UI: radio (○ Percentage ○ Amount) + margin value + live, read-only computed selling price.
- Persisted on the product: `margin_type` (`percentage`|`amount`), `margin_value`, and the computed `selling_price`.
- Editing a product's margin/purchase price **recomputes** selling price server-side.

## CR-1.4 Remove Product Category (completely)

- **Remove:** category field, filters, APIs, and the **`products.category` column** (Alembic migration, data preserved otherwise).
- **POS:** replace category chips with **Recent Products**, **Top Selling Products**, and search suggestions.

## CR-1.5 Auto Product Codes

- Auto-generate per tenant: **`PD-00001`, `PD-00002`, …** (next = highest existing `PD-#####` + 1, tenant-scoped).
- Pre-filled by default; **user may overwrite** (e.g. `TEXT-001`).
- **Duplicate codes never allowed** within a tenant — backend uniqueness + frontend pre-check + clear error:
  *"This product code already exists."*

## CR-1.6 Unit → NOS

- Default unit becomes **NOS** (was PCS), editable.
- Applies everywhere: Purchase, Inventory, Product List, POS, Reports, Print templates.
- **Decision needed:** convert existing `PCS` rows to `NOS`, or only change the default for new products? (Recommend: change default only; leave historical values untouched. Confirm at sign-off.)

## CR-1.7 Multi-Tenant Isolation (CRITICAL)

**Root-cause finding (verified):**
- **Backend is already row-level isolated** — every repository/service filters `WHERE tenant_id = <jwt tenant>`; tenant id comes only from the JWT (never the request body); cross-tenant `GET /{id}` returns **404**; the `tenant_isolation` tests pass. A **full repo audit (Deliverable 7)** will confirm no query is missed.
- **The visible bleed is a frontend cache issue:** TanStack Query keys are resource-only (`["products"]`, `["sales"]`, …) and the auth store never clears the cache on **login/logout**. Switching tenants in the same browser tab shows the *previous* tenant's cached rows until refetch.

**Fix (both layers):**
1. **Frontend:** call `queryClient.clear()` on login and logout, **and** namespace every query key with the tenant id (`["products", tenantId, …]`) so caches can never collide.
2. **Backend:** audit all repositories (Products, Purchases, PurchaseItems, InventoryTransactions, Sales, SaleItems, Suppliers, BillUsage, Reports, Dashboard, Search, Exports, Settings) to guarantee `tenant_id` filtering; add a tenant-scoped repository base assertion.
3. **DB:** enforce uniqueness/indexes per CR-1.8 so isolation is also structural.

## CR-1.8 Database Constraints & Indexes

- `UNIQUE (tenant_id, product_code)` (already present — reaffirmed).
- Product Name: duplicates allowed.
- Indexes: `tenant_id`, `(tenant_id, product_code)`, `(tenant_id, created_at)` on products; verify same pattern on sales/purchases/inventory.

## CR-1.9 Data Migration (Alembic, data-preserving)

1. **Drop** `products.category` (+ its index).
2. **Add** `products.margin_type` (default `percentage`), `products.margin_value` (default 0). Backfill existing rows by
   inferring margin from current `purchase_price`/`selling_price` (amount margin = selling − purchase; 0 if purchase is 0).
3. Reaffirm `UNIQUE (tenant_id, product_code)` + add `(tenant_id, created_at)` index.
4. No destructive data loss beyond the category column.

## CR-1.10 UI Changes

- **Products → "Product Catalogue"** (read-only): Code, Name, Purchase Price, Selling Price, Current Stock, GST, Status;
  actions = Edit, View Stock Ledger, Deactivate. **No Add Product button.**
- **Purchase:** premium entry — inline add-new or select-existing; shows Purchase Price, Margin Type, Margin Value,
  computed Selling Price, Quantity, Unit (default NOS), GST, HSN — all live.
- **POS:** remove category filters → Recent Products + Top Selling Products + search suggestions.

## CR-1.11 Validation Rules

| Field | Rule |
|-------|------|
| Selling Price | Read-only (derived) |
| Quantity | > 0 |
| Purchase Price | > 0 |
| Margin | ≥ 0 (not negative) |
| Product Code | Unique within tenant; auto-default `PD-#####`, overwritable |
| Product Name | Required |

## CR-1.12 Testing

Auto product creation via purchase; %-margin and fixed-amount selling-price calc; duplicate-code prevention
(within tenant); **tenant isolation & cross-tenant access prevention** (backend + the frontend cache-clear);
inventory sync; purchase → inventory updates.

---

## Impacted Data Model (preview — detail in Deliverable 2)

- **products:** **drop** `category`; **add** `margin_type`, `margin_value`; `selling_price` becomes derived; default `unit = 'NOS'`.
- No other table schema changes (purchases already create inventory IN; sale_items snapshot product fields).

## Decisions / Open Questions

1. Convert existing `PCS` units to `NOS`, or default-only? (Recommend default-only.)
2. Backfill margin for existing products as **fixed amount** (selling − purchase)? (Recommended.)
3. Keep `selling_price` as a stored derived column (recommended, for fast POS reads) vs. compute on the fly.
4. Inline-new product in a purchase with a code that already exists → reject the whole purchase with the duplicate error (recommended) vs. treat as "select existing."

---

> **STOP — Deliverable 1 (Updated FRD).** Approve to proceed to **Deliverable 2: Database Changes**.
