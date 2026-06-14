# CR-3 — Deliverable 3: Database Review

Confirms every field CR-3 §10 requires already exists, and specifies the single schema change.

---

## 3.1 Required-field coverage (CR-3 §10)

| CR-3 required field | Where it lives today | Action |
|---------------------|----------------------|--------|
| `purchase_price` | `products.purchase_price`, `purchase_items.purchase_price` | ✅ exists |
| `markup_amount` | `products.profit_amount` | **rename** → `markup_amount` (migration 0008) |
| `selling_price` | `products.selling_price` (derived = pp + markup) | ✅ exists |
| `purchase_gst_amount` | `purchase_items.gst_amount` (per line), `purchases.total_gst` (per purchase) | ✅ exists — **reuse** (Q2) |
| `purchase_payable` | `purchase_items.line_total` (per line), `purchases.total_amount` (per purchase) | ✅ exists — **reuse** (Q2) |
| `gst_percentage` | `products.gst_percentage`, `purchase_items.gst_percentage` | ✅ exists |
| `hsn_code` | `products.hsn_code`, `sale_items.hsn_code` | ✅ exists |

**Net schema change: one column rename.** Purchase GST and Supplier Payable are already first-class
persisted columns (`purchase_items.gst_amount` / `line_total`); per the approved decision we reuse them
rather than add duplicate `purchase_gst_amount` / `purchase_payable` columns.

## 3.2 `products` table — target delta

| Column | Type | Change |
|--------|------|--------|
| ~~profit_amount~~ | NUMERIC(10,2) NOT NULL DEFAULT 0 | **RENAME → `markup_amount`** (same type/constraints/values) |

Selling-price rule unchanged: `selling_price = round(purchase_price + markup_amount, 2)`.

## 3.3 Migration `0008` (data-preserving)

`alembic/versions/0008_cr3_markup_rename.py`:
```python
def upgrade():
    op.alter_column("products", "profit_amount", new_column_name="markup_amount")
def downgrade():
    op.alter_column("products", "markup_amount", new_column_name="profit_amount")
```
- `RENAME COLUMN` carries every value as-is — **no data transformation, no loss**.
- Transactional DDL (Postgres) — atomic.
- `down_revision = 0007_cr2_pricing_invoice_gst`; `0008` becomes the new head.
- Not applied to Neon in this deliverable: the live backend's models still reference `profit_amount`;
  renaming now would break it until the D4/D5 code lands. Validated non-destructively here; applied
  for real once the code is coherent (end of D5), so the app flips atomically — same approach as CR-2.

## 3.4 Constraints / indexes — unchanged

- `UNIQUE (tenant_id, product_code)` (`uq_product_code_tenant`) reaffirmed — backs CR-3.7 duplicate-code
  prevention. No new index; the renamed column was never indexed.

## 3.5 SQLAlchemy model delta (preview — applied in D4)

`app/models/product.py`:
```python
# rename:
markup_amount: Mapped[float] = mapped_column(
    Numeric(10, 2), nullable=False, server_default="0", default=0
)   # was profit_amount
```

## 3.6 Tables unchanged

`purchases`, `purchase_items`, `sales`, `sale_items`, `payments`, `inventory_transactions`, `suppliers`,
`tenants`, `users`, `tenant_subscriptions`, `bill_usage` — no change. Purchase GST/payable already persisted.

---

> **STOP — Deliverable 3 (Database Review).** Approve to proceed to **Deliverable 4: Backend Service Fixes**
> (rename `profit_amount→markup_amount` through models/services/schemas, verify purchase-vs-sales GST separation).
