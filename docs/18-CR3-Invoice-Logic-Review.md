# CR-3 — Deliverable 7: Invoice Logic Review

Verifies the customer invoice is **sales-side only** and unaffected by CR-3's purchase changes.

---

## 7.1 No purchase-side data can reach the invoice (structural proof)

The invoice payload is `InvoiceOut { business: InvoiceBusiness, sale: SaleOut }`:

- **`InvoiceBusiness`** fields: `business_name, gst_number, mobile, email, address, invoice_footer, show_gst_on_invoice`.
  → No `purchase_price`, `markup_amount`, or purchase GST. ✅
- **`SaleOut` / `SaleItemOut`** fields: `product_name, hsn_code, quantity, unit_price (selling snapshot),
  discount, gst_percentage, taxable_value, cgst, sgst, igst, line_total`, plus bill totals.
  → No purchase price / markup / supplier-payable anywhere. ✅

Because the schema has **no purchase columns**, the API is *structurally incapable* of leaking purchase
figures onto a customer invoice — there is nothing to serialize.

## 7.2 Invoice GST is selling-derived

`print.ts` renders `unit_price` (= the selling-price snapshot persisted on `sale_items` at sale time) and
the stored `taxable_value` / `cgst` / `sgst` / `igst` — all computed by `gst_service` from the **selling
price** (CR-2.1 invariant, guarded by tests). Purchase price never participates. ✅

## 7.3 CR-2 Hide/Show toggle still correct after CR-3

CR-3 changed pricing field naming (`markup_amount`) and the purchase form only — it did **not** touch
`print.ts` or the toggle. Re-verified the two render modes are intact:
- **Hide (default):** "INVOICE", columns Item/Qty/Rate/Amount, no tax rows, no GSTIN.
- **Show:** "TAX INVOICE", full tax breakup + GSTIN.

(Covered by `test_cr2_invoice.py`, still green — re-run in D9.)

## 7.4 Terminology on the slip

- **Markup:** internal-only; correctly **absent** from the customer invoice (a customer never sees cost or
  markup). No change needed.
- **NOS (CR-3.6):** the printed quantity currently shows a bare number (e.g. `2`) with **no unit label**.
  `sale_items` snapshot `product_name` and `hsn_code` but **not `unit`**, so the slip cannot show the
  per-item unit for historical sales. This is the one CR-3 gap on the invoice — see Decision below.

## 7.5 Finding & Decision — NOS on the printed quantity

To show "2 NOS" correctly on the invoice, the per-item `unit` must be available. Options:

| Option | What it takes | Correctness |
|--------|---------------|-------------|
| **A. Snapshot `unit` on `sale_items`** (recommended) | migration `0009` adds `sale_items.unit`; `billing_service` writes `product.unit`; `SaleItemOut` + `print.ts` show it | ✅ correct for any unit (NOS, KG, …), consistent with existing name/HSN snapshots; only future sales get it (historical rows show "—"/blank) |
| **B. Static "NOS" suffix in `print.ts`** | one-line template change, no DB | ⚠️ wrong if a product uses a non-NOS unit (unit is editable) |
| **C. Defer** | nothing | quantity stays unlabeled on the slip |

**Recommendation: A** — it's small, matches how name/HSN are already snapshotted, and is correct for any
unit. It adds one migration (`0009`, `sale_items.unit VARCHAR DEFAULT 'NOS'`) beyond D3's rename.

---

> **STOP — Deliverable 7 (Invoice Logic Review).** Invoice is verified sales-side-only and toggle-safe.
> **One decision needed (7.5):** how to show NOS on the printed quantity — A (snapshot, recommended), B (static), or C (defer). Approve to proceed to **Deliverable 8: Unit Tests** (I'll implement the chosen NOS option as part of D8/D9 if A or B).
