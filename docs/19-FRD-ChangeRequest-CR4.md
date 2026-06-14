# CR-4 — POS pricing must mirror the Purchase Pricing Preview (GST exclusive by default)

**Status:** implemented · **Severity:** critical (profit loss) · **Date:** 2026-06-13

---

## 1. Root Cause Analysis

The complaint was that the POS invoice total equalled the selling price (₹100) while the
Purchase Pricing Preview showed ₹105, so GST appeared to be "not added" and markup was lost.

Investigation found **the pricing engine is NOT duplicated and its math is correct**:

- Every persisted sale flows through one function — `gst_service.compute_bill`.
- `billing_service` feeds it `unit_price = product.selling_price` (CR-2.1 invariant).
- Reports / dashboard / invoice only **read** the stored `Sale` totals; they never recompute.

The defect was a **wrong default mode**. `compute_bill` supports two modes and both are
correct; which one a sale uses is `tenant.gst_mode_default`, which defaulted to
**`"inclusive"`**. In inclusive mode GST is carved **out** of the selling price instead of
added **on top**:

| mode | selling | taxable | GST | grand total | merchant keeps | margin (cost ₹80) |
|------|---------|---------|-----|-------------|----------------|-------------------|
| inclusive *(old default)* | 100 | 95.24 | 4.76 | **100** | 95.24 | **15.24** ❌ |
| exclusive *(correct)*     | 100 | 100.00 | 5.00 | **105** | 100.00 | **20.00** ✅ |

The Purchase Pricing Preview's headline "Customer Price (Exclusive)" is `selling × (1+rate)`
= ₹105, so the two modules diverged purely because the POS resolved the `inclusive` default.

**The standard formula in the brief — `Selling + GST = Customer Price` — is GST-exclusive.**
Root cause: the system defaulted to inclusive, silently absorbing markup into GST.

## 2. Fix (shared engine, single default change)

- **`tenant.gst_mode_default` default → `"exclusive"`** (model `default` + `server_default`).
- **Migration `0010_cr4_default_gst_exclusive`**: sets the server default and corrects
  existing tenants still on the defective `inclusive` default. **Historical sales are
  untouched** — each `sales` row stores its own `gst_mode` + frozen taxable/GST/grand_total.
- **Inclusive remains a first-class opt-in** (per tenant in Settings, per sale via
  `gst_mode` on `/sales/preview` and `/sales`). The engine already handled both modes.
- No change to `compute_bill` / `billing_service` / reports — already correct & authoritative.

### Shared pricing engine
- **Backend (authoritative):** `pricing.compute_selling_price` (SP = purchase + markup) and
  `gst_service.compute_bill` (taxable / GST / line & bill totals, both modes, intra/inter).
- **Frontend:** consolidated into one module `src/lib/pricing.ts` (mirrors the backend);
  `features/products/types.ts` re-exports from it — no duplicated formulas. The POS reads
  numbers from `/sales/preview` (server is the single source of truth for persisted money).

## 3. UX changes (frontend)
- **POS cart line:** Rate · Qty · GST% · **Line GST** · Line Total (per-line GST is explicit).
- **Payment panel:** **Subtotal / GST / Grand Total** (CGST/SGST shown as sub-rows).
- **Settings:** Default GST Mode selector fallback = exclusive, with an explanatory note.
- **Invoice (`print.ts`):** unchanged — already keeps GST inside the grand total under the
  Hide-GST slip (Amount = line_total = ₹105, Total = ₹105; never reduced to ₹100).

## 4. Test matrix (all green — 118 passed)
- `tests/unit/test_cr4_pricing_engine.py` — canonical 80/20/100 @5%: exclusive qty1→105,
  qty3→315; inclusive qty1→100; **full-markup-preserved** assertion; intra split sums to GST.
- `tests/api/test_cr4_pos_pricing.py` — exclusive **default** qty1/qty3; preview == saved
  sale; inclusive override → 100; Hide-GST invoice grand total still includes GST; paying the
  bare selling price (100) under the exclusive default is correctly rejected.
- Legacy inclusive-number tests pinned to explicit `gst_mode="inclusive"` so they remain
  deterministic regardless of the default; the default assertion updated to `exclusive`.

## 5. Invariants (locked)
1. `selling_price = purchase_price + markup_amount` (derived, read-only).
2. Sales GST is always derived from `selling_price`, never `purchase_price` (CR-2.1).
3. **Default mode is exclusive**: customer price = selling + GST; full markup = profit.
4. Inclusive mode is supported per-tenant / per-sale; historical sales keep their own mode.
5. Grand total always includes GST internally, even when the slip hides the tax breakup.
