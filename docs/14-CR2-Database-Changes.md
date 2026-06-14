# CR-2 — Deliverable 2: Database Changes

Schema design for CR-2. Migration implementation follows in **Deliverable 3** (Alembic `0007`).

**Approved decisions (CR-2 sign-off, "approve all"):**
1. Rename `products.margin_value` → **`profit_amount`**; **drop** `margin_type`.
2. Hide-mode invoice label → "INVOICE" (template-only; no DB impact).
3. Purchase Price strictly **> 0** (already enforced in `PurchaseItemInput`; reaffirmed).
4. Dashboard GST widget / Profit Report **not built** — audit-only; no schema.
5. Backfill `profit_amount` from existing prices; **`selling_price` left unchanged**.
6. `show_gst_on_invoice` default **FALSE** for all tenants (new + existing).

---

## 2.1 `tenants` table — target schema (delta only)

| Column | Type | Change | Notes |
|--------|------|--------|-------|
| … existing … | | — | business/GST/invoice settings unchanged |
| place_of_supply | VARCHAR(10) | — | `intra` \| `inter` |
| gst_mode_default | VARCHAR(10) | — | `inclusive` \| `exclusive` |
| invoice_prefix | VARCHAR(10) | — | |
| invoice_footer | VARCHAR(500) | — | |
| **show_gst_on_invoice** | **BOOLEAN** | **ADD** | `NOT NULL`, `server_default false`; controls customer-invoice tax display **only** |

> BillNova stores invoice settings as columns on `tenants` (there is **no** separate `invoice_settings` table). The CR's "InvoiceSettings" maps to this invoice-settings column group. Adding one boolean here keeps the existing `SettingsOut`/`SettingsUpdate` passthrough pattern intact (Deliverable 5).

## 2.2 `products` table — target schema (delta only)

| Column | Type | Change | Notes |
|--------|------|--------|-------|
| id / tenant_id / product_code / name / unit | — | — | unchanged |
| purchase_price | NUMERIC(12,2) | — | must be **> 0** (validated at purchase input) |
| ~~margin_type~~ | ~~VARCHAR(10)~~ | **DROP** | percentage pricing removed entirely |
| ~~margin_value~~ | ~~NUMERIC(10,2)~~ | **DROP** | replaced by `profit_amount` |
| **profit_amount** | **NUMERIC(10,2)** | **ADD** | `NOT NULL`, `server_default 0`, **≥ 0**; the only profit driver |
| selling_price | NUMERIC(12,2) | semantics simplified | **stored, derived** = `round(purchase_price + profit_amount, 2)`; never client-set |
| gst_percentage / hsn_code / current_stock / reorder_level / is_active / timestamps | — | — | unchanged |

**Derived selling price (computed at write, both create-from-purchase and edit):**
```
selling_price = round(purchase_price + profit_amount, 2)     # the single rule
```
No percentage branch remains.

## 2.3 Constraints

- `UNIQUE (tenant_id, product_code)` (`uq_product_code_tenant`) — unchanged.
- No DB CHECK for `profit_amount >= 0` / `purchase_price > 0` (kept at app layer, consistent with CR-1's "no DB enum/check for migration simplicity"). Pydantic enforces both.
- `show_gst_on_invoice` — `NOT NULL DEFAULT false` is the structural guarantee that satisfies CR-2.10 ("must have default, never null").

## 2.4 Indexes

No index changes. CR-1 already added `ix_products_tenant_created`. Dropping `margin_type`/`margin_value` and adding `profit_amount` touch no index (none referenced them). `show_gst_on_invoice` is not indexed (read with the tenant row, never filtered on).

## 2.5 Backfill (existing rows) — data-preserving

Run **inside migration `0007`, before dropping the old columns**:

```sql
-- 1) Tenants: every existing business starts in privacy-default Hide mode.
--    (Column added NOT NULL DEFAULT false already backfills false; explicit for clarity.)
UPDATE tenants SET show_gst_on_invoice = false WHERE show_gst_on_invoice IS NULL;

-- 2) Products: record the equivalent fixed profit so SP = PP + profit_amount holds
--    for every existing row, WITHOUT changing any selling_price.
UPDATE products
   SET profit_amount = GREATEST(COALESCE(selling_price, 0) - COALESCE(purchase_price, 0), 0);
```

- Rows previously priced by **percentage** keep their exact `selling_price`; only the stored *driver* becomes the equivalent amount (e.g. PP 100, SP 125 → `profit_amount = 25`).
- Rows where `selling_price < purchase_price` (shouldn't occur) clamp to `profit_amount = 0` via `GREATEST`, matching the `≥ 0` rule.
- `selling_price` values are **never modified** by this migration.

## 2.6 Migration ordering (critical)

`0007` upgrade order so no data is lost and no NULLs violate constraints:
1. `ADD COLUMN tenants.show_gst_on_invoice BOOLEAN NOT NULL DEFAULT false`.
2. `ADD COLUMN products.profit_amount NUMERIC(10,2) NOT NULL DEFAULT 0`.
3. **Backfill** `products.profit_amount` from `selling_price - purchase_price` (§2.5).
4. `DROP COLUMN products.margin_value`.
5. `DROP COLUMN products.margin_type`.

Downgrade reverses: add `margin_type` (`server_default 'amount'`) + `margin_value`, backfill `margin_value = profit_amount`, drop `profit_amount`, drop `show_gst_on_invoice`. (Downgrade restores as **fixed-amount** margin — the only semantics CR-2 keeps — so SP stays consistent.)

## 2.7 SQLAlchemy model deltas

`app/models/tenant.py`:
```python
# add (with the other invoice settings):
show_gst_on_invoice: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
```

`app/models/product.py`:
```python
# remove:
margin_type: Mapped[str]  = mapped_column(String(10), default="percentage")
margin_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

# add:
profit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default="0", default=0)
# selling_price stays a stored column, set by the service as purchase_price + profit_amount.
```

## 2.8 Tables that DO NOT change

`purchase_items` **does not store margin** today (only `purchase_price`, `gst_percentage`, `gst_amount`, `line_total`) — so **no schema change**. The `margin_type`/`margin_value` on `PurchaseItemInput` are **transient request fields** (Pydantic), replaced by `profit_amount` in **Deliverable 5**, not a DB migration.

Unchanged tables: `sales`, `sale_items`, `payments`, `purchases`, `purchase_items`, `inventory_transactions`, `suppliers`, `users`, `tenant_subscriptions`, `bill_usage`. Sale items already snapshot full tax (`taxable_value`, `cgst`, `sgst`, `igst`, `gst_percentage`) — CR-2's invoice toggle is a **render-time** decision, so no sales-side column is needed.

## 2.9 Statutory-independence guarantee (structural)

No reporting table or column reads `show_gst_on_invoice`. GST/HSN/auditor figures derive solely from `sale_items` snapshots. The toggle is physically incapable of altering report data — there is no column linking them. (Reaffirmed by an integration test in Deliverable 9.)

---

> **STOP — Deliverable 2 (Database Changes).** Approve to proceed to **Deliverable 3: Alembic Migration** —
> migration `0007_cr2_pricing_invoice_gst` implementing §2.5–2.7 (add `show_gst_on_invoice`, add `profit_amount` + backfill, drop `margin_type`/`margin_value`), data-preserving and validated against Neon.
