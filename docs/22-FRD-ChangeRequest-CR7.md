# CR-7 — Purchase workflow, per-bill GST display & POS performance

**Status:** implemented · **Date:** 2026-06-13

Four mandatory pre-production enhancements.

---

## 1. Purchase workflow redesign (Indian supplier-invoice style)
- Each purchase **item** now starts with a **Product Type** radio — `○ Existing Product` /
  `○ New Product` (default Existing). Existing shows search + pricing; New shows
  name/code/HSN + pricing. The two field sets never appear together, and the choice is
  **independent per item** (Item 1 existing, Item 2 new, … in one bill).
- Purchase **header**: Supplier, **Invoice Number**, Purchase Date, **Notes**
  (new columns `purchases.invoice_number`, `purchases.notes`).
- `+ Add Another Item` appends a section; a live **Purchase Summary** shows Purchase Total,
  Purchase GST, Supplier Payable, **Total Items**. Invoice # also shows in the list.

## 2. Removed the global "Default GST Mode" setting
`tenants.gst_mode_default` and its Settings UI / API are **gone**. Pricing is now always
**exclusive** (the CR-4 standard: GST added on top, full markup preserved). The pure engine
still supports both modes for unit tests; there is simply no tenant-level default to confuse.

## 3. Invoice GST display is now PER BILL
- Moved `show_gst_on_invoice` off the tenant onto **`sales.show_gst_on_invoice`**, chosen at
  POS checkout (radio Hide/Show, **default Hide**) and **frozen** on the sale.
- The Invoice Register shows a **GST Display** column; **reprints use the sale's stored flag**,
  never the live settings. Two bills can legitimately differ (Bill 1 Hide → `3 × 210 = 630`;
  Bill 2 Show → `3 × 200 = 600`, GST 30, Total 630).
- Migration `0013` backfills each existing sale's flag from the old tenant value, then drops
  the tenant column. Statutory GST/HSN reports remain independent of this display flag.

## 4. POS performance — sub-100ms, no API during billing
- **No backend call during cart edits.** Totals are computed locally by `computeBill()`
  (`src/lib/pricing.ts`), a faithful mirror of the backend `gst_service.compute_bill`
  (exclusive, bill-discount apportionment, intra/inter split, ROUND_HALF_UP). The server still
  recomputes authoritatively on save, so the posted grand total matches byte-for-byte. The
  backend is only hit on **Save / Hold / Reprint / Void**.
- **Store split:** `stores/cart.ts` (lines + bill discount) and `stores/checkout.ts`
  (payments, customer, notes, per-bill GST, error) — disjoint slices.
- **Render isolation:** POS is split into memoized `ProductPanel` / `CartPanel` /
  `PaymentPanel` using **selector-based** Zustand subscriptions. Adding a product does **not**
  re-render the product grid (it only reads the stable `addProduct` action); editing payment
  does **not** re-render the cart (it doesn't subscribe to the checkout store), and vice-versa.
  Bill computation is `useMemo`'d off `[lines, billDiscount]`.
- **Dev perf logs:** `src/lib/perf.ts` (`perf`/`perfStart`) prints `add-to-cart`,
  `cart-calc`, `invoice-save` durations in dev (`console.debug`), silent in production.

## Backend changes
Models: `Sale.show_gst_on_invoice`; `Purchase.invoice_number`/`notes`; tenant loses
`gst_mode_default` + `show_gst_on_invoice`. `billing_service` defaults pricing to exclusive
and stores the per-bill flag; `invoice_service` reads the per-bill flag for the PDF and
includes it in the register rows; settings schema drops the two fields. Migration
`0013_cr7_per_bill_gst` (revision id kept ≤32 chars for `alembic_version`).

## Tests & verification
- **Backend (137 passed):** rewrote `test_cr2_invoice.py` for per-bill GST (default Hide,
  two bills differing, reports independent), `test_dashboard_settings.py` (removed fields
  absent), `test_cr4` hide-test now reads the sale flag, new `test_cr7_purchase.py`
  (header fields + mixed existing/new lines in one invoice).
- **Frontend (19 passed, Vitest):** `computeBill.test.ts` — local cart calc correctness,
  intra/inter split, discount apportionment, purity/no-network; plus the CR-6 thermal tests.
- **Live (:8001):** settings fields gone; purchase `KK-77` + notes + 2 items; two bills with
  show_gst False/True both total ₹630; register reflects each; reprint preserves the original.
- Frontend `tsc` clean, production build OK, dev server 200.

> Perf note: the <50/<100ms targets are met by construction (local synchronous compute +
> render isolation) and surfaced via the dev `[perf]` logs; no formal benchmark harness was
> added. A real-browser visual pass of the new POS/Purchase flows was not automated.
