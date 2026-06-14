# CR-6 — Thermal/Invoice pricing display fix (Qty × Rate must equal Amount)

**Status:** implemented · **Severity:** critical (counter disputes) · **Date:** 2026-06-13

---

## 1. Root Cause Analysis
The receipt renderer (`receiptInnerHTML`) and the A4 PDF printed **Rate = `unit_price`** (the
pre-GST selling price) while **Amount = `line_total`** (GST-inclusive). In the default
exclusive/GST-hidden mode these differ by the GST, so a customer reading the slip saw
`3 × ₹200 = ₹630` — which doesn't compute (`3 × 200 = 600`). The grand total was correct;
only the *displayed unit rate* was wrong for the hidden-GST layout.

## 2–3. Fix + shared pricing (no duplicate logic)
One rule, applied by a single shared helper on each side
(`app/services/pricing.py` ⇄ `src/lib/pricing.ts`), so POS, thermal preview, reprint, side
preview and A4 PDF all agree:

| Mode | Displayed Rate | Displayed Amount | Identity |
|------|----------------|------------------|----------|
| **GST hidden** (default) | `customer_unit_rate = line_total / qty` (₹210) | `line_total` (₹630) | `qty × rate = amount` |
| **GST visible** | `net_unit_rate = taxable / qty` (₹200, = selling in exclusive) | `taxable` (₹600) + GST line (₹30) | `(qty × rate) + GST = grand_total` |

Frontend `thermalLineItems()` and backend `customer_unit_rate`/`net_unit_rate` are the single
source of truth; the renderers only format their output.

## 4–5. Template redesign (thermal + register/reprint previews)
Supermarket layout: `Item · Qty · Rate · Amount` table with dashed rules, a consolidated
`GST (x%)` line in visible mode, then `TOTAL / <payment modes> / BALANCE`. Header now shows
store name, address, `Ph:`, **GSTIN only when configured**, `Bill No`, `Date` (with time),
`Cashier`, `Customer` (defaults to *Walk-in*). Footer: "Thank You For Shopping! / Please Visit
Again" + optional **"Powered by BillNova"** (merchant-toggleable). The side-panel and reprint
previews use the same `receiptInnerHTML`, so they inherit the fix automatically.

## 6. Backend
- `pricing.py`: `customer_unit_rate`, `net_unit_rate` (pure, ROUND_HALF_UP).
- `invoice_service.invoice_pdf`: rebuilt to the corrected per-unit logic + cashier line +
  TOTAL/payments/BALANCE + branding footer.
- `cashier_name` resolved into the invoice payload (`/sales/{id}/invoice`, `/invoices/{id}`,
  reprint) via `invoice_service.cashier_name`.
- `tenants.show_branding` (migration `0012`, default true) exposed in settings + invoice payload.

## 7. Frontend
`lib/pricing.ts` (shared helpers + `thermalLineItems`), `print.ts` (redesigned `receiptInnerHTML`
+ CSS), `sales/types.ts` (`cashier_name`, `show_branding`), `settings` (branding toggle). The
`ThermalInvoicePreview`/`InvoiceSideSheet`/register/reprint consume the shared renderer.

## 8–9. Tests & verification
- **Frontend (new Vitest harness, Node18-pinned vitest@1.6):** `src/features/sales/print.test.ts`
  — 12 tests: helper identities, `thermalLineItems` qty×rate==amount (both modes), rendered HTML
  hidden (210/630, no GST line, branding) and visible (200/600, GST (5%) 30, total 630), GSTIN
  only-if-configured, cashier/Walk-in. **12 passed.** `npm test` added.
- **Backend:** `tests/unit/test_cr6_thermal_pricing.py` (rate identities) +
  `tests/api/test_cr6_thermal_invoice.py` (cashier in payload, branding default+toggle, PDF bytes).
  Full suite **134 passed**.
- **Live (:8001):** canonical Milk×3 → hidden 210×3=630, visible 200+30=630, cashier "Admin",
  branding on, PDF `%PDF`. Frontend `tsc` clean, build OK, dev server 200.

## Validation rules (locked)
- GST hidden: `qty × displayed_rate == displayed_amount` (always).
- GST visible: `(qty × displayed_rate) + GST == grand_total` (always).
