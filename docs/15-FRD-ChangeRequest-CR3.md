# BillNova — FRD Change Request CR-3 (Purchase vs Sales Clarity, Markup Rename, Pricing Preview)

**Type:** UX-clarity fix + field/labelling changes (no GST math bug found)
**Status:** Deliverable 1 of 9 — awaiting approval before any flow/DB/code changes.

Updates [01-FRD.md](01-FRD.md); builds on [13-FRD-ChangeRequest-CR2.md](13-FRD-ChangeRequest-CR2.md). Where they conflict, **CR-3 wins**.

---

## CR-3.0 Summary & Rationale

Retailers were confused by the Purchase screen footer "**Total (incl. GST) ₹275**" shown next to a "Selling ₹ 502" field — it looks like purchase and sales figures are tangled. CR-3 makes the two sides **visually distinct**, renames Profit→**Markup**, and tidies the purchase form (HSN optional, Qty (NOS), auto product code, GST dropdown). No GST formula changes are needed on the backend.

---

## CR-3.1 Verified Finding — the ₹275 is CORRECT, the label is the bug ⚠️

The CR states the ₹275 "indicates GST mixing Purchase Price and Selling Price logic." A read of the code shows this is **not** happening. The footer (`Purchases.tsx`) computes:

```js
const base = l.quantity * l.purchasePrice;        // 1 × 250 = 250  (purchase price only)
total = base + base * l.gstPercentage / 100;      // 250 + 25  = 275
```

`₹275 = Purchase Total (₹250) + Purchase GST (₹25) = Supplier Payable` — **purchase-price only; selling price never enters**. This matches the CR's own "Purchase Payable = ₹275 — This is correct." So there is **no calculation bug**.

Backend confirms the same separation already holds (locked in CR-2.1):
- **Purchase/input GST** (`purchase_service`): `gst_amount = qty × purchase_price × rate` → purchase-side. ✅
- **Sales/output GST** (`billing_service` → `gst_service`): driven by `product.selling_price`. ✅ (guarded by `test_cr2_pricing_invariant`).

**Therefore CR-3 is a presentation/labelling change, not a math fix.** The defect is that one ambiguous footer label sits beside a selling-price field with no sales-side context. CR-3 fixes that by splitting the footer into two clearly-titled cards.

---

## CR-3.2 Purchase Summary Card (replaces the ambiguous footer)

Replace `Total (incl. GST) ₹275` with a titled **Purchase Summary** (purchase-price math only — unchanged numbers, clearer labels):

```
Purchase Total      ₹250.00      (Σ qty × purchase_price)
Purchase GST        ₹25.00       (Σ purchase_total × gst%)
Supplier Payable    ₹275.00      (purchase_total + purchase_gst)
```

Aggregated across all lines. This is exactly what the backend already returns as `purchase.total_amount` / `total_gst` (line `purchase_items.gst_amount` / `line_total`).

## CR-3.3 Pricing Preview Card (new — sales side, per line)

A separate, clearly-separated preview so purchase vs sales never blur:

```
──────── Pricing Preview ────────
Purchase Price            ₹250.00
Markup ₹                  ₹252.00
Selling Price             ₹502.00      (purchase_price + markup)
GST                       10%
Customer Price (Exclusive) ₹552.20     (selling × (1 + gst/100))
Customer Price (Inclusive) ₹502.00     (selling; taxable 456.36, gst 45.64)
Expected Margin           ₹252.00      (= markup)
──────────────────────────────
```

Pure frontend, updates instantly, mirrors `gst_service` (inclusive: `taxable = price/(1+r)`, exclusive: `gst = price×r`). Presentational only — persisted GST is still computed server-side at sale time.

## CR-3.4 Rename "Profit ₹" → "Markup ₹"

- UI label everywhere: **Markup ₹** (Purchase line, Products edit).
- Backend field `products.profit_amount` → **`markup_amount`** (Decision Q1 — note this is a *second* rename after CR-2's `margin_value→profit_amount`). Selling price rule is unchanged: `selling_price = purchase_price + markup_amount`.
- Schemas/types: `profit_amount` → `markup_amount` in `ProductOut`/`ProductUpdate`, `PurchaseItemInput`, and the React types + `previewSellingPrice`.

## CR-3.5 HSN Optional

- HSN is **already optional** in the schema (`hsn_code: str | None`) and the form has no required-check — so this is mainly a **label** change: "HSN" → "**HSN (Optional)**". Confirm no export path hard-blocks on a blank HSN (HSN report already coalesces missing codes to "—"). Purchases never blocked on HSN.

## CR-3.6 Qty label → "Qty (NOS)"

- Unit default is already **NOS** (CR-1). Change the field label "Qty" → "**Qty (NOS)**" on the purchase line; ensure NOS shows on Inventory/POS/Reports/Print where unit is rendered (mostly already the case).

## CR-3.7 Product Code — show the auto code by default

- Today the code field is blank with an "auto" placeholder; the server assigns `PD-#####` on save.
- CR-3: **pre-display the next code** (e.g. `PD-00007`) so the user sees it, still overridable (e.g. `RIN-001`). Server remains authoritative (Decision Q3 — a previewed code is a hint; the final unique code is assigned/validated server-side to avoid races).
- Duplicate prevention already enforced: `UNIQUE (tenant_id, product_code)` + `409 DUPLICATE_RESOURCE` → UI shows **"This product code already exists."** (reaffirmed, no DB change).

## CR-3.8 GST % → dropdown

- Replace the free numeric GST input with a **dropdown**: `0, 5, 12, 18, 28`. **Default 0%** (Decision Q4 — current new-line default is 5%; CR asks for 0%). Invalid percentages become impossible at the UI; backend keeps `0 ≤ gst ≤ 100`.

## CR-3.9 Backend Review (mostly verification)

Map CR service names → actual modules; confirm no purchase/sales GST mixing:

| CR name | Actual | Status |
|---------|--------|--------|
| PurchaseService | `purchase_service` | uses `purchase_price` only ✅ |
| SalesService | `billing_service` | uses `selling_price` only ✅ |
| GSTService | `gst_service` | pure engine; caller supplies the base ✅ |
| InventoryService | `inventory_service` | quantities only; no GST ✅ |
| ReportService | `report_service` | reads `sale_items` snapshots (selling-derived) ✅ |
| InvoiceService | `/sales/{id}/invoice` + `print.ts` | renders stored sale tax ✅ |

Work here = the `profit_amount→markup_amount` rename threaded through services, plus a unit/integration test asserting purchase GST ≠ sales GST for the same product (the CR-3.1 separation).

## CR-3.10 Database Review

Required fields vs current state:

| CR field | Current | Action |
|----------|---------|--------|
| purchase_price | `products.purchase_price`, `purchase_items.purchase_price` | exists |
| markup_amount | `products.profit_amount` | **rename** (Q1) |
| selling_price | `products.selling_price` | exists (derived) |
| purchase_gst_amount | `purchase_items.gst_amount`, `purchases.total_gst` | exists (Q2 — reuse, don't duplicate) |
| purchase_payable | `purchase_items.line_total`, `purchases.total_amount` | exists (Q2) |
| gst_percentage | `products.gst_percentage`, `purchase_items.gst_percentage` | exists |
| hsn_code | `products.hsn_code`, `sale_items.hsn_code` | exists |

- **Migration `0008`:** rename `products.profit_amount → markup_amount` (data-preserving: `ALTER ... RENAME COLUMN`, values carried as-is). No other schema change required (purchase GST/payable already persisted).
- "Do NOT calculate GST using purchase price for sales" — already guaranteed (CR-2.1 invariant + guard).

## CR-3.11 Testing

Unit: purchase GST (`qty×pp×rate`), supplier payable (`pp×qty + gst`), selling price (`pp + markup`), customer GST exclusive (`sp×(1+r)`) & inclusive (`taxable=sp/(1+r)`), purchase-vs-sales separation (same product → different GST bases), markup rename. Integration: purchase response totals (Purchase Total/GST/Payable), pricing-preview math parity, duplicate-code 409, GST dropdown values accepted.

---

## Decisions / Open Questions (please confirm at sign-off)

1. **Rename `profit_amount → markup_amount`** (recommended, matches §10 field list + UI label) vs keep the column `profit_amount` and relabel UI only (avoids a 2nd migration in two CRs). *Recommend rename.*
2. **purchase_gst_amount / purchase_payable**: reuse existing `purchase_items.gst_amount` / `line_total` (recommended — they already hold these) vs add duplicate explicitly-named columns. *Recommend reuse.*
3. **Auto code display**: show a *previewed* next code (hint) with the server assigning the authoritative code on save (recommended, race-safe) vs reserve the code up front. *Recommend preview+server-authoritative.*
4. **GST default 0%** per the CR (changes the current 5% new-line default). Confirm 0% is the desired default for new purchase lines.
5. **Markup wording in Products edit** too (not just Purchase): rename "Profit Amount (₹)" → "Markup (₹)" there as well (recommended, consistency).

---

> **STOP — Deliverable 1 (Updated FRD).** Approve (accepting the recommendations, or answering the 5 decisions) to proceed to **Deliverable 2: Purchase Calculation Flow**.
