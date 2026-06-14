# BillNova — FRD Change Request CR-2 (GST-on-Selling-Price, Profit-Amount Pricing, Invoice GST Privacy, Clean Numeric Inputs)

**Type:** Business-rule update + UX enhancement
**Status:** Deliverable 1 of 9 — awaiting approval before any DB/code changes.

This document updates [01-FRD.md](01-FRD.md) and supersedes the pricing parts of [10-FRD-ChangeRequest-CR1.md](10-FRD-ChangeRequest-CR1.md). Where they conflict, **CR-2 wins**.

---

## CR-2.0 Summary & Rationale

Small Indian retailers want **simple customer-facing bills** (often a plain item-and-total slip with **no tax breakup**) while still keeping **full GST records** for their accountant/auditor and statutory filing. CR-2 also simplifies pricing to a single, intuitive **Profit Amount** model and cleans up numeric data entry.

CR-2 delivers five changes:

1. **Lock GST to Selling Price** everywhere (sales/output tax) — and add a guard + tests so purchase price can never drive sales GST.
2. **Profit-Amount-only pricing** — remove margin *percentage*; `Selling Price = Purchase Price + Profit Amount` (read-only, auto-calculated).
3. **Invoice GST Privacy toggle** — new setting *Invoice GST Display* (Show / **Hide**, default **Hide**) that controls only what the **customer invoice** shows. Internals and reports are unaffected.
4. **Numeric inputs without spinners** — remove browser up/down controls on all amount/number fields.
5. **Validation hardening** for the above.

---

## CR-2.1 Verified Finding — GST is *already* computed from Selling Price ⚠️

The CR states GST currently uses **Purchase Price**. A full read of the code shows this is **not the case for sales**. Stating it plainly so we don't "fix" a non-bug and miss the real work:

| Path | GST basis today | Verdict |
|------|-----------------|---------|
| POS preview & `create_sale` (`billing_service._line_inputs`) | `product.selling_price` | ✅ already Selling Price |
| `gst_service.compute_bill` (inclusive: `taxable = base/(1+r)`, exclusive: `gst = base×r`) | line `unit_price` = selling price | ✅ correct |
| `sale_items` snapshot (`taxable_value`, `cgst/sgst/igst`, `gst_percentage`) | from the above | ✅ correct |
| GST Summary, HSN Summary, Sales report, Dashboard, PDF/Excel exports | read stored `sale_items` values | ✅ correct (never recompute from purchase price) |
| **Purchase entry** (`purchase_service`: `gst_amount = qty×purchase_price×rate`) | `purchase_price` | ✅ **correct & must stay** — this is *input/ITC tax* on the supplier bill, not customer GST |

**Conclusion:** No incorrect GST math exists in sales. CR-2.1 therefore **codifies the rule as an invariant** rather than changing formulas:

- **Rule (locked):** *Customer/output GST is always derived from `selling_price`. `purchase_price` is used only for purchase/input GST and stock valuation — never for sales GST.*
- **Action:** add a small assertion/comment in `billing_service._line_inputs` and a dedicated unit test (`test_sales_gst_uses_selling_price_not_purchase`) that fails if a future change wires purchase price into a sale line.
- Modules listed in the CR (Billing POS, Sales Invoice, Invoice Preview, GST Reports, HSN Summary, Dashboard GST widgets, Auditor Exports, Profit Reports) are **audited** under this rule in Deliverable 4. Note: a *Dashboard GST widget* and a standalone *Profit Report* do **not exist yet** (Decision Q4) — flagged, not silently skipped.

> If you actually observed GST that looked like it came from purchase price, it was almost certainly the **percentage margin** making `selling_price` a function of `purchase_price` (e.g. PP ₹100 @ 25% → SP ₹125 → GST on ₹125). CR-2.2 removes that percentage coupling, which makes the selling price explicit and removes the confusion at its source.

---

## CR-2.2 Profit-Amount-Only Pricing (remove Margin %)

**Today:** product pricing uses `margin_type ∈ {percentage, amount}` + `margin_value`; `pricing.compute_selling_price` supports both; UI shows a **% / Amount** selector (Products edit, Purchase line). Default is **percentage @ 25**.

**Required:**

- Remove **Margin Percentage** entirely — type selector, percentage math, percentage UI/API/DB.
- Keep a single **Profit Amount**. Formula (the only one):
  `Selling Price = Purchase Price + Profit Amount`  → e.g. PP ₹100 + Profit ₹25 = **SP ₹125**.
- **Selling Price** stays **stored, derived, read-only**, and updates instantly in the UI as Purchase Price / Profit Amount change. Users may never type Selling Price.

**Renames (clarity):** `margin_value` → **`profit_amount`**; drop `margin_type`. `compute_selling_price(purchase_price, profit_amount)` becomes a one-line add. Frontend `previewSellingPrice` simplifies to `pp + profit`.

---

## CR-2.3 Invoice GST Display Setting (the core feature)

**New setting** — *Settings → Invoice Settings → Invoice GST Display*:

- Options: **○ Show GST on Invoice** / **○ Hide GST on Invoice**
- **Default: Hide GST on Invoice** (i.e. `show_gst_on_invoice = FALSE`).

Stored on the tenant's invoice settings (BillNova keeps invoice settings as columns on `tenants`; there is no separate `invoice_settings` table — see Deliverable 2).

**This toggle affects the customer invoice rendering only.** It never changes what is computed or stored, and never changes reports.

---

## CR-2.4 Billing Logic — internals always complete

POS billing is unchanged internally. Every sale continues to compute and **persist**: `taxable_value`, `gst_amount`, `cgst`, `sgst`, `igst`, `gst_percentage`, `gst_mode`, `place_of_supply` per line and per bill. These feed Auditor reports, GST Summary, HSN, and tax filing **regardless of the display toggle**.

---

## CR-2.5 Customer Invoice — two render modes

The invoice template (frontend `features/sales/print.ts`; the print/reprint slip) branches on `show_gst_on_invoice`:

**Hide GST (default)** — simplified slip:
```
Item            Qty   Rate    Amount
Product A         1   ₹500     ₹500
Product B         1   ₹300     ₹300
---------------------------------------
Grand Total                    ₹800
```
Omit: Taxable column, GST% column, GST column, CGST/SGST/IGST totals, any tax breakup. Header label becomes a neutral **"INVOICE"** (not "TAX INVOICE").

**Show GST** — full tax invoice (current behaviour): Item, Qty, Rate, Disc, Taxable, GST%, GST, Amount columns; Taxable / CGST / SGST / IGST / Discount / Grand Total; header **"TAX INVOICE"**, GSTIN shown.

The backend must expose `show_gst_on_invoice` to the frontend invoice payload (via the existing business/settings data the invoice already loads). Thermal/print template mirrors the same branching.

---

## CR-2.6 Reports are never affected by invoice display (statutory)

**Hard rule:** GST Summary, HSN Summary, Sales GST report, and Auditor/PDF/Excel exports **always** show full tax detail, independent of `show_gst_on_invoice`. No reporting query reads the toggle. (Reaffirmed by a test that runs a report with the toggle both on and off and asserts identical tax figures.)

---

## CR-2.7 Remove Numeric Spinner Controls (UX)

Remove browser increment/decrement arrows on **all** numeric fields, keeping `type="number"` (for mobile numeric keypads + validation) and entering values manually.

- **Affected fields (verified in code):** Purchase Price, Profit Amount, GST % (Products edit, Purchase line), Quantity (Purchase, POS), Discount, Cash/UPI/Card amounts (POS payments), Opening Stock / Stock Adjustment delta (Inventory), Reports year/month.
- **Implementation:** one global rule in `src/index.css` (no per-input changes), applied to `input[type="number"]`:
  - Chrome/Edge/Safari: `::-webkit-outer-spin-button, ::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }`
  - Firefox: `input[type=number] { -moz-appearance: textfield; appearance: textfield; }`
- This honours the client-ui rule "no inline styles" — it's a single base-layer stylesheet rule, not inline.

---

## CR-2.8 Database Changes (preview — detail in Deliverable 2)

On **`tenants`** (invoice settings group):
- **ADD** `show_gst_on_invoice BOOLEAN NOT NULL DEFAULT FALSE`.

On **`products`**:
- **ADD** `profit_amount NUMERIC(10,2) NOT NULL DEFAULT 0`.
- **DROP** `margin_type`, **DROP** `margin_value` (data preserved by backfilling `profit_amount` first).

**Data preservation / backfill (before dropping):**
```sql
UPDATE products
   SET profit_amount = GREATEST(COALESCE(selling_price,0) - COALESCE(purchase_price,0), 0);
-- selling_price is left unchanged (historically correct); this just records the equivalent
-- fixed profit so SP = PP + profit_amount continues to hold for every existing row.
```
Alembic migration `0007` (one upgrade/downgrade), validated against Neon, no destructive loss beyond the two margin columns.

---

## CR-2.9 API Updates (preview — detail in Deliverable 5)

- `SettingsOut` / `SettingsUpdate`: add `show_gst_on_invoice: bool` (update validated, has a default → CR-2.10).
- `ProductOut`: replace `margin_type`/`margin_value` with `profit_amount`. `ProductUpdate`: replace with `profit_amount: float (ge=0)`; drop `margin_type`.
- Purchase line schema (`PurchaseItemCreate`): replace `margin_type`/`margin_value` with `profit_amount`.
- No change to sale/preview response shapes (tax fields already present); invoice consumer reads `show_gst_on_invoice` from settings/business payload.

---

## CR-2.10 Validation Rules

| Field | Rule |
|-------|------|
| Profit Amount | ≥ 0 (cannot be negative) |
| Purchase Price | > 0 (must be greater than zero) |
| Selling Price | derived, read-only (never accepted from client) |
| GST % | 0 ≤ x ≤ 100 |
| Invoice GST Display | boolean, **must have default** (`FALSE`); never null |

Server-side is authoritative (Pydantic + service); client mirrors for UX. `> 0` on Purchase Price is a CR-2 tightening (was `≥ 0`) — see Decision Q3.

---

## CR-2.11 Testing (preview — Deliverables 8 & 9)

Unit:
- Sales GST derived from **Selling Price**, not Purchase Price (invariant guard).
- `Selling Price = Purchase Price + Profit Amount` (auto-calc, rounding).
- Profit Amount validation (reject negative); Purchase Price `> 0`; GST % bounds.
- `compute_bill` inclusive & exclusive still correct after pricing change.

Integration:
- Invoice **Hide** mode: response/template omits all tax rows; shows Item/Qty/Rate/Amount/Grand Total.
- Invoice **Show** mode: full tax breakup.
- GST/HSN/Auditor reports **identical** with toggle ON vs OFF (statutory independence).
- Settings update persists `show_gst_on_invoice`; default is FALSE for new tenants.

UI/manual:
- Spinner controls absent on all numeric fields (Chrome + Firefox), values still entered/validated.
- Products & Purchase show read-only live Selling Price; no Margin %/type control remains.

---

## Impacted Surface (map to deliverables)

| Deliverable | Scope |
|-------------|-------|
| 2 — DB Changes | `tenants.show_gst_on_invoice`; `products`: +`profit_amount`, −`margin_type`/`margin_value` |
| 3 — Alembic | migration `0007` (add toggle, add profit_amount, backfill, drop margin cols) |
| 4 — Backend services | `pricing.compute_selling_price` (profit only), `product_service`, `purchase_service`, `billing` invariant guard + comment; settings service passthrough |
| 5 — API/schemas | `settings`, `product`, `purchase` schemas |
| 6 — React UI | Products/Purchase (remove % selector, Profit Amount + read-only SP), Settings (GST Display toggle), `index.css` spinner rule |
| 7 — Invoice templates | `print.ts` Show/Hide branching (+ thermal) |
| 8 — Unit tests | pricing, GST invariant, validation |
| 9 — Integration tests | invoice modes, report independence, settings default |

---

## Decisions / Open Questions (please confirm at sign-off)

1. **Naming:** rename `margin_value` → `profit_amount` and drop `margin_type` (recommended, clearest), **vs.** keep the column name `margin_value` and just force "amount" semantics (smaller migration). *Recommend rename.*
2. **Invoice label in Hide mode:** show **"INVOICE"** (recommended) vs keep "TAX INVOICE". A hidden-GST slip arguably should not say "TAX INVOICE".
3. **Purchase Price `> 0`:** enforce strictly per the CR (recommended) — note this means a ₹0 "free sample" purchase line is rejected; confirm that's acceptable.
4. **Non-existent targets:** the CR lists *Dashboard GST widgets* and *Profit Reports*, which **don't exist today**. Options: (a) treat as "audit-only, nothing to change" (recommended), or (b) add a new Profit Report (PP vs SP vs GST) as extra scope. *Recommend (a)* — flag, don't silently build.
5. **Existing data:** backfill `profit_amount = max(selling − purchase, 0)` keeping every current `selling_price` unchanged (recommended). Rows previously priced by % keep their exact selling price; only the stored driver becomes the equivalent amount.
6. **Default rollout:** new toggle defaults to **Hide** for *all* tenants including existing ones (per CR). Confirm existing businesses currently issuing full tax invoices are OK flipping to Hide by default (they can switch to Show in Settings).

---

> **STOP — Deliverable 1 (Updated FRD).** Approve (and answer the 6 decisions, or accept the recommendations) to proceed to **Deliverable 2: Database Changes**.
