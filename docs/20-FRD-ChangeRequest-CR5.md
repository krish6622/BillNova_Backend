# CR-5 — Invoice Register + Thermal Printing (supermarket-style POS)

**Status:** implemented · **Date:** 2026-06-13

Redesigns the POS print flow to match Indian supermarkets (D-Mart/Reliance Smart): instant
thermal printing with no interrupting A4 preview, plus a central **Invoice Register** to
review/reprint/void/export every bill.

---

## 1. Save & Print flow (changed)
**Before:** Save → open A4 invoice in a new browser tab (interrupts billing).
**After:** Save → direct-print to the configured format → clear cart → refocus product search.
- Thermal (80/58mm) prints via a hidden iframe — **no new tab, no preview page**.
- A4 fetches the server-rendered PDF and opens it (the only format that previews).
- Print failure never blocks the next bill (the sale is saved and in the register).
- Next bill is ready in ~1s (cart cleared, F2 search focused automatically).

> Browser reality: web pages cannot bypass the OS print dialog unless the browser is run
> in kiosk/silent-print mode with a default printer. The hidden-iframe path is the standard
> "direct print" web approach and prints silently when the terminal is configured for it.

## 2. Invoice Register (`/invoices`)
Premium data table (custom primitives — no new deps): **Invoice # · Date & Time · Customer ·
Total · Payment · Cashier · Status** with actions **View / Reprint / Void / Download PDF**.
Filters: invoice number, date range, payment type, cashier, status. Server-side pagination.

## 3. Side preview (no navigation)
**View** opens a right slide-over (`Sheet`, ~480px, Framer Motion) showing the thermal preview
(`ThermalInvoicePreview`) + **Reprint / Download PDF / Close**. ESC closes it. The preview uses
the *same* renderer (`receiptInnerHTML`) as the printer, so what you see is what prints.

## 4–7. Thermal format & invoice type
80mm (302px) / 58mm (219px) monospace receipt: store name/address/phone, invoice/date/time,
cashier-agnostic customer line, items (Qty × Rate, line amount), totals, payment, footer, GSTIN.
Tenant setting **invoice_type**: `thermal_80` (default) | `thermal_58` | `a4`. A4 → PDF preview;
thermal → direct print.

## 8. POS workflow & shortcuts
Checkout → Save → direct print → cart cleared → focus product search. Shortcuts: **F10** Save &
Print, **F9** Invoice Register (global), **F2** product search, **ESC** close side panel.

## 10. Backend (`/api/invoices`, tenant-isolated)
| Endpoint | Purpose |
|---|---|
| `GET /api/invoices` | list + filters (date/number/payment/cashier/status) + pagination |
| `GET /api/invoices/cashiers` | cashier options for the filter |
| `GET /api/invoices/{id}` | full invoice payload (business + sale) |
| `POST /api/invoices/{id}/reprint` | non-mutating re-fetch for printing |
| `POST /api/invoices/{id}/void` | **full void**: mark status, reverse stock, reverse usage |
| `GET /api/invoices/{id}/pdf` | A4 PDF (reportlab), honours show_gst_on_invoice |

Mounted at `/api/invoices` to match BillNova's existing `/api/...` convention (no `/v1`).

### Void semantics (full void)
Sets `sales.status='void'` + `voided_at`, returns each line's stock to inventory (an `IN`
ledger txn, reason "Invoice voided"), and decrements the bill from its month's usage. Voided
sales are excluded from **every** sales aggregation (daily/monthly/GST/HSN/top-products,
dashboard KPIs, and the POS top-selling ranking). Idempotent — double-void → 400.

### Schema (migration `0011_cr5_invoice_register`, additive)
- `sales.status` (active|void, default active) · `sales.voided_at` · `sales.customer_name`
- `tenants.invoice_type` (thermal_80 default)
Historical invoices are untouched; existing rows backfill to active / thermal_80.

## 11. Frontend pieces
`Sheet` (ui), `InvoiceRegister` (page), `InvoiceSideSheet`, `ThermalInvoicePreview`, refactored
`print.ts` (shared `receiptInnerHTML`, `printThermal`, `printInvoiceByType`, `openPdfBlob`),
`features/invoices/{api,types}`, nav + route + Settings invoice-type selector + POS direct-print.

## 12. Tests & verification
- `tests/api/test_cr5_invoices.py` (8 cases): enriched list, all filters, detail+invoice_type,
  non-mutating reprint, **void reverses stock+usage+reports**, double-void rejected, PDF bytes,
  tenant isolation (cross-tenant 404). Full suite: **126 passed**.
- Live E2E on :8001 confirmed: sale 252 → register row (UPI/cashier/customer) → PDF `%PDF`
  → void restores stock 48→50, usage 1→0, daily report bills→0; double-void 400.
- Frontend: `tsc --noEmit` clean, production build OK, dev server HMR clean.
- **Gap:** the frontend repo has no test runner (no vitest/jest). UI behaviours were verified by
  type-check + build + live API; a vitest harness for `receiptInnerHTML`/components can be added.
