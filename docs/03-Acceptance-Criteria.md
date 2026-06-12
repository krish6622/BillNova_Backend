# 3. Acceptance Criteria — BillNova Phase 1

Gherkin-style (`Given / When / Then`). Each block references its user story.

---

## A — Onboarding, Auth & Tenancy

### AC-A1 (US-A1) Owner registration
- Given a valid Business Name, Owner Name, Mobile, Email, password (and optional GST Number)
- When the owner submits registration
- Then a new tenant is created with status **Trial** and `created_date = now`
- And an Owner user is created with the hashed password
- And the response returns access + refresh tokens
- And registering with an email that already exists returns `409 Conflict`.

### AC-A2 (US-A2) Login
- Given a registered, active user
- When they POST valid credentials
- Then they receive a JWT access token (with `sub`, `tenant_id`, `role`) and a refresh token
- And invalid credentials return `401` with a generic "invalid credentials" message (no user enumeration).

### AC-A3 (US-A3) Logout
- Given a logged-in user with a refresh token
- When they call logout
- Then the refresh token is revoked and cannot mint new access tokens.

### AC-A4 (US-A4) Tenant isolation
- Given two tenants T1 and T2 each with products and sales
- When a T1 user requests any list/detail endpoint
- Then only T1 rows are returned
- And requesting a T2 resource id directly returns `404` (not `403`, to avoid leaking existence).

### AC-A5 (US-A5/A6) User management
- Given an authenticated Owner
- When they create a Cashier with email + name
- Then a Cashier user is created in the same tenant with a temporary/owner-set password
- And a Cashier attempting to create users receives `403`
- And deactivated users cannot log in.

---

## B — Subscription & Usage

### AC-B1 (US-B1) Usage visibility
- Given a tenant on a plan with limit N
- When the owner opens the dashboard/subscription view
- Then the system shows `used / N` bills and the percentage for the current calendar month.

### AC-B2 (US-B2) 80% warning
- Given usage ≥ 80% and < 100% of the plan limit
- When any user loads the POS or dashboard
- Then a non-blocking warning banner is shown
- And bill creation still succeeds.

### AC-B3 (US-B3) 100% block
- Given usage ≥ 100% OR subscription status ∈ {Expired, Suspended}
- When a user attempts to save a new bill
- Then the request is rejected with `403` and code `SUBSCRIPTION_LIMIT_REACHED` (or `SUBSCRIPTION_INACTIVE`)
- And reprint/print of existing bills still works.

### AC-B4 (US-B4) Manual activation
- Given an internal/admin activation operation with tenant, plan, status, period start/end
- When it is applied
- Then the tenant's plan + status + period update
- And usage limit reflects the new plan immediately.

### AC-B5 (US-B5) Monthly reset
- Given usage recorded in month M
- When the calendar rolls to M+1 (server tz Asia/Kolkata)
- Then usage for M+1 starts at 0 while M's record is retained for history.

---

## C — Billing / POS

### AC-C1 (US-C1) Product search
- Given products exist in the tenant
- When the cashier types ≥1 char in search
- Then matching active products (by code/name/HSN) return within the debounce window
- And inactive products are excluded from POS search.

### AC-C2 (US-C2/C3) Cart operations
- Given a product in search results
- When the cashier adds it, sets quantity Q and discount D
- Then a line is added/updated with line total recomputed
- And removing the line or clearing the cart updates totals immediately
- And quantity must be > 0 and discount within [0, line subtotal].

### AC-C4 (US-C4) Live totals
- Given a cart with multiple lines
- Then the preview shows per-line taxable value + GST and a footer with total taxable, total CGST/SGST/IGST, total discount, and grand total
- And totals recompute on every cart change with consistent rounding (half-up to 2 decimals).

### AC-C5 (US-C5) Save invoice (atomic)
- Given a valid cart and an in-limit, active subscription
- When the cashier saves
- Then a Sale + SaleItems + Payments + InventoryTransactions(OUT) are written in one transaction
- And the tenant's monthly usage increments by 1
- And stock decreases by sold quantities
- And a unique tenant-scoped invoice number is assigned
- And if any step fails, the whole save rolls back (no partial sale, no usage increment, no stock change).

### AC-C6 (US-C6) Payments / split
- Given a grand total G
- When payments are recorded (one or many rows across Cash/UPI/Card)
- Then the sum of payment amounts must equal G (else `422`)
- And split payment stores one row per mode.

### AC-C7 (US-C7/C8) Print & reprint
- Given a saved sale
- When the user prints or reprints
- Then a print-friendly invoice renders with business header, line items, GST breakup, payments, and invoice number
- And reprint does not alter usage or stock.

### AC-C10 (US-C10) Keyboard
- Then the POS supports: focus search, add highlighted result, adjust qty, jump to payment, and save — all via keyboard, documented on-screen.

---

## D — GST

### AC-D1 (US-D1) Inclusive
- Given a product priced inclusive at P with rate r%
- Then taxable = `P / (1 + r/100)`, GST = `P − taxable`, and the customer-facing line total = P (rounded half-up to 2 dp).

### AC-D2 (US-D2) Exclusive
- Given a product priced exclusive at P with rate r%
- Then GST = `P * r/100`, line total = `P + GST`.

### AC-D3 (US-D3/D4) CGST/SGST/IGST
- Given place of supply = intra-state
- Then GST splits into CGST = SGST = GST/2, IGST = 0
- Given place of supply = inter-state
- Then IGST = full GST, CGST = SGST = 0
- And all four values are stored per SaleItem.

---

## E — Products

### AC-E1 (US-E1/E2) CRUD
- Given an Owner
- When they create a product with all required fields
- Then it is saved scoped to the tenant
- And editing updates it; deleting a product **referenced by sales/purchases** soft-deletes (sets inactive) instead of hard delete
- And a duplicate Product Code in the same tenant returns `409`.

### AC-E3 (US-E3) Search + pagination
- Then product listing supports search and page/limit params and returns total count for pagination.

---

## F — Purchases

### AC-F1 (US-F1/F2) Create purchase increases stock
- Given a purchase with items
- When saved
- Then for each item an InventoryTransaction(IN) is created and current stock increases by the purchased quantity (atomic).

### AC-F3 (US-F3) Edit/cancel adjusts stock
- When a purchase is cancelled or quantities edited
- Then compensating inventory transactions are written so current stock reflects the change correctly.

---

## G — Inventory

### AC-G1/G2 (US-G1/G2) Current stock + ledger
- Then current stock per product is queryable
- And the stock ledger lists IN/OUT/ADJUST entries with timestamp, reference (sale/purchase/adjustment), and running balance.

### AC-G3 (US-G3) Manual adjustment
- Given an Owner provides product, delta, and reason
- When saved
- Then an InventoryTransaction(ADJUST) is created and stock updates; reason is required.

### AC-G4 (US-G4) Low stock
- Given products with current stock ≤ reorder threshold (threshold > 0)
- Then they appear in the low-stock list and the dashboard low-stock count.

---

## H — Reports

### AC-H1 (US-H1) Sales reports
- Given a date / month filter
- Then daily and monthly sales totals (bill count, gross, discount, taxable, GST, net) are returned, tenant-scoped.

### AC-H2 (US-H2) GST/HSN
- Then GST Summary aggregates taxable + CGST/SGST/IGST by rate, and HSN Summary aggregates by HSN code with quantity and tax — both auditor-ready.

### AC-H3/H4 (US-H3/H4) Stock + export
- Then current stock report lists product, stock, value (stock × purchase price)
- And every report exports to PDF and Excel with the same figures shown on screen.

---

## I — Dashboard & Settings

### AC-I1 (US-I1) Dashboard
- Then the dashboard shows: Today's Sales (amount + count), Monthly Sales, Bills this month, Subscription usage (used/limit + %), Low Stock count — all for the current tenant.

### AC-I2/I3 (US-I2/I3) Settings
- Then the Owner can update business profile, invoice prefix/footer, default GST mode, and place of supply; changes apply to new invoices.

---

## J — Platform / NFR

### AC-J1 (US-J1) UI states
- Then every data view renders distinct loading, empty, and error states; destructive actions require a confirmation dialog.

### AC-J2 (US-J2) Compose
- Then `docker compose up` brings up db + backend + frontend, and the app is reachable locally.

### AC-J3 (US-J3) Coverage
- Then backend test suite reports ≥ 80% coverage in CI.
