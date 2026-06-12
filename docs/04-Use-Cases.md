# 4. Use Cases — BillNova Phase 1

Each use case: actor, preconditions, main flow, alternate/exception flows, postconditions.

---

## UC-1 — Register Business (Owner)

- **Actor:** Prospective Owner
- **Precondition:** Not logged in; email not already registered.
- **Main flow:**
  1. Owner opens Register and enters business + personal details + password.
  2. System validates input (email format, mobile, password strength, unique email).
  3. System creates Tenant (status=Trial) and Owner user atomically.
  4. System issues access + refresh tokens and redirects to Dashboard.
- **Alternates / exceptions:**
  - 2a. Email already exists → `409`, prompt to log in.
  - 2b. Validation fails → field-level errors, no records created.
- **Postcondition:** Tenant + Owner exist; trial subscription active.

---

## UC-2 — Login / Logout

- **Actor:** Owner or Cashier
- **Precondition:** Active account exists.
- **Main flow:** User submits credentials → system verifies hash → issues tokens → loads role-appropriate UI. Logout revokes refresh token.
- **Exceptions:** Invalid credentials → `401` generic message; deactivated user → `403`.
- **Postcondition:** Authenticated session (or cleanly ended session).

---

## UC-3 — Manage Cashier Users (Owner)

- **Actor:** Owner
- **Precondition:** Logged in as Owner.
- **Main flow:** Owner creates a Cashier (name, email, temp password) → user added to tenant with role Cashier → optionally deactivate or reset password.
- **Exceptions:** Cashier attempts this → `403`; duplicate email in tenant → `409`.
- **Postcondition:** Cashier can log in with restricted access.

---

## UC-4 — Create Bill at POS (Cashier/Owner) — *core*

- **Actor:** Cashier or Owner
- **Precondition:** Logged in; subscription active and usage < 100%.
- **Main flow:**
  1. User searches a product; selects a result.
  2. System adds a cart line (default qty 1) and recomputes totals with GST.
  3. User adjusts qty/discount/notes; optionally adds more products.
  4. User opens payment; chooses Cash/UPI/Card or splits across modes.
  5. User saves the bill.
  6. System checks subscription + usage + stock, then writes Sale, SaleItems, Payments, InventoryTransactions(OUT), increments usage — atomically — and assigns an invoice number.
  7. System shows success and offers Print.
- **Alternates / exceptions:**
  - 1a. No results → empty state with "add product" hint (Owner only).
  - 4a. Split payments don't sum to grand total → `422`, block save.
  - 6a. Usage ≥ limit or subscription inactive → `403`, save blocked with guidance.
  - 6b. Insufficient stock (if hard-block enabled) → `422` listing offending items.
  - 6c. Any persistence error → full rollback; no usage/stock change.
- **Postcondition:** Persisted sale; stock reduced; usage +1; invoice printable.

---

## UC-5 — Print / Reprint Invoice

- **Actor:** Cashier or Owner
- **Precondition:** A saved sale exists in the tenant.
- **Main flow:** User selects a sale (just-saved or from history) → system renders print-friendly invoice (business header, lines, GST breakup, payments, invoice no.) → user prints.
- **Exceptions:** Sale not in tenant → `404`.
- **Postcondition:** Invoice printed; no change to usage or stock.

---

## UC-6 — Manage Products (Owner)

- **Actor:** Owner
- **Precondition:** Logged in as Owner.
- **Main flow:** Create/edit/delete products; search with pagination. Cashier can view/search but not mutate.
- **Exceptions:** Duplicate Product Code → `409`; delete of referenced product → soft-delete (deactivate); Cashier mutate → `403`.
- **Postcondition:** Catalog reflects changes.

---

## UC-7 — Record Purchase (Owner)

- **Actor:** Owner
- **Precondition:** Logged in as Owner; products exist.
- **Main flow:** Enter supplier + date + items (product, qty, purchase price, GST) → save → system writes Purchase + PurchaseItems + InventoryTransaction(IN) per item, increasing stock — atomically.
- **Alternates:** Edit/cancel purchase → compensating inventory transactions keep stock correct.
- **Postcondition:** Purchase recorded; stock increased.

---

## UC-8 — Inventory: Ledger & Adjustment (Owner)

- **Actor:** Owner
- **Precondition:** Logged in as Owner.
- **Main flow:** View current stock and stock ledger per product; make a manual adjustment with delta + reason → system writes InventoryTransaction(ADJUST) and updates stock.
- **Exceptions:** Missing reason → `422`.
- **Postcondition:** Stock and ledger reflect adjustment.

---

## UC-9 — View Reports & Export (Owner)

- **Actor:** Owner
- **Precondition:** Logged in as Owner; data exists.
- **Main flow:** Choose report (Daily/Monthly Sales, GST Summary, HSN Summary, Current Stock) + date filter → system computes tenant-scoped figures → user exports to PDF/Excel.
- **Exceptions:** No data in range → empty report with zeros.
- **Postcondition:** Report viewed/exported.

---

## UC-10 — Monitor Subscription & Usage

- **Actor:** Owner; **System** (enforcement)
- **Precondition:** Tenant has a subscription.
- **Main flow:** Owner views plan/status/usage. System increments usage on each saved bill, shows 80% warning, and blocks at 100% / inactive. Usage windows reset monthly.
- **Alternates:** Manual activation/upgrade updates plan + status + period (no payment gateway).
- **Postcondition:** Usage accurately gated and visible.

---

## UC-11 — View Dashboard

- **Actor:** Owner (full), Cashier (limited)
- **Main flow:** On login, system loads tenant KPIs: today's sales, monthly sales, bills this month, subscription usage, low-stock count.
- **Postcondition:** At-a-glance operational view.
