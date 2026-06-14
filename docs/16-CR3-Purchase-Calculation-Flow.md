# CR-3 — Deliverable 2: Purchase Calculation Flow

The authoritative definition of the **two independent** money flows on the Purchase screen.
**Approved decisions (CR-3 "approve all"):** rename `profit_amount→markup_amount`; reuse existing
`purchase_items.gst_amount`/`line_total` for purchase GST/payable; auto-code = previewed hint + server-authoritative;
GST default **0%**; rename label in Products edit too.

Rounding everywhere: `Decimal`, `ROUND_HALF_UP`, 2 dp (per `gst_service` / `pricing`).

---

## 2.1 Two flows, never mixed

```
        PURCHASE SIDE (supplier)                    SALES SIDE (customer)
        uses purchase_price ONLY                    uses selling_price ONLY
   ┌──────────────────────────────┐          ┌──────────────────────────────┐
   │ Purchase Total = pp × qty    │          │ selling = pp + markup        │
   │ Purchase GST   = total × r%  │          │ Customer (excl) = sp×(1+r%)  │
   │ Supplier Payable = total+gst │          │ Customer (incl) = sp         │
   └──────────────────────────────┘          │   taxable = sp/(1+r%)        │
        → Purchase Summary card               │   gst     = sp − taxable     │
        → purchase_items / purchases          │ Margin = markup              │
        → Input GST / Purchase Register       └──────────────────────────────┘
                                                   → Pricing Preview card
                                                   → POS / sale_items / Output GST
```

`r` = `gst_percentage`. The only shared input is the GST **rate** and the product's `purchase_price`
(which seeds `selling_price` via the markup). GST **amounts** are computed independently on each side.

---

## 2.2 Purchase side (supplier) — formulas

Per line:
```
purchase_total_line   = purchase_price × quantity
purchase_gst_line     = round(purchase_total_line × gst_percentage / 100, 2)
purchase_payable_line = purchase_total_line + purchase_gst_line
```
Aggregated (the Purchase Summary card):
```
Purchase Total   = Σ purchase_total_line
Purchase GST     = Σ purchase_gst_line
Supplier Payable = Σ purchase_payable_line
```

**Worked example** (PP 250, qty 1, GST 10%):
```
Purchase Total   = 250.00
Purchase GST     = 25.00
Supplier Payable = 275.00          ← the screenshot's ₹275 (CORRECT)
```

**Source of truth:** the backend `purchase_service.create_purchase` already computes these and persists
`purchase_items.gst_amount` (= purchase_gst_line), `purchase_items.line_total` (= purchase_payable_line),
`purchases.total_gst`, `purchases.total_amount`. The Purchase Summary card mirrors them for the live
(pre-save) form; on save the backend values are authoritative.

> Purchase side is **independent of markup, selling price, and GST inclusive/exclusive mode** — a supplier
> invoice is always tax-on-cost.

---

## 2.3 Sales side (customer) — formulas

Per unit (the Pricing Preview card):
```
selling_price            = round(purchase_price + markup_amount, 2)
customer_price_exclusive = round(selling_price × (1 + gst_percentage/100), 2)
customer_price_inclusive = selling_price
   taxable_inclusive     = round(selling_price / (1 + gst_percentage/100), 2)
   gst_inclusive         = selling_price − taxable_inclusive
expected_margin          = markup_amount
```

**Worked example** (PP 250, markup 252, GST 10%):
```
Selling Price             = 502.00
Customer Price (Exclusive)= 552.20      (502 × 1.10;  GST 50.20)
Customer Price (Inclusive)= 502.00      (taxable 456.36, GST 45.64)
Expected Margin           = 252.00
```

**Which one a real sale uses** is decided at POS time by the tenant's `gst_mode_default`
(inclusive/exclusive, overridable per sale) — the preview shows **both** so the retailer can see the
customer-facing number under either mode. The preview is presentational; the persisted sale GST is computed
by `gst_service` at sale time from `selling_price` (CR-2.1 invariant, never `purchase_price`).

---

## 2.4 Where each value is computed

| Value | Computed in | Persisted? |
|-------|-------------|-----------|
| Purchase Total / GST / Payable | `purchase_service` (authoritative); mirrored live in `Purchases.tsx` | yes — `purchase_items`, `purchases` |
| `selling_price` | `pricing.compute_selling_price(pp, markup)` on purchase save & product edit | yes — `products.selling_price` |
| Pricing Preview (customer excl/incl, margin) | `Purchases.tsx` only (mirrors `gst_service`) | no — display only |
| Sale taxable / CGST / SGST / IGST | `gst_service.compute_bill` at POS | yes — `sale_items` |

## 2.5 Multi-line & multi-qty notes

- **Purchase Summary** aggregates across all lines (qty-scaled): a 2-line purchase sums both payables.
- **Pricing Preview** is **per unit / per line** product economics — markup and selling price are unit
  properties, independent of purchase quantity. (Line value at sale time = unit × qty, handled by POS.)
- Inclusive split keeps `cgst + sgst == gst` exactly (penny assigned to SGST), per existing `gst_service`.

## 2.6 Invariants (locked)

1. Purchase GST uses `purchase_price`; Sales GST uses `selling_price`. **No crossover.** (guarded by tests)
2. `selling_price = purchase_price + markup_amount` (read-only, derived).
3. Supplier Payable is GST-mode-independent; Customer Price depends on inclusive/exclusive.
4. All money rounds half-up to 2 dp at each computed step.

---

> **STOP — Deliverable 2 (Purchase Calculation Flow).** Approve to proceed to **Deliverable 3: Database Review**
> (confirm field coverage; spec migration `0008` renaming `products.profit_amount → markup_amount`, data-preserving).
