# 2. User Stories — BillNova Phase 1

Format: `As a <role>, I want <capability>, so that <benefit>.`
IDs map to epics; acceptance criteria are in [03-Acceptance-Criteria.md](03-Acceptance-Criteria.md).

Priority: **P0** = must for launch, **P1** = important, **P2** = nice-to-have within Phase 1.

---

## Epic A — Onboarding, Auth & Tenancy

- **US-A1 (P0)** As a business owner, I want to register my business with my details, so that I get an isolated workspace and a trial subscription.
- **US-A2 (P0)** As an owner/cashier, I want to log in with email + password, so that I can access my business data securely.
- **US-A3 (P0)** As a logged-in user, I want to log out, so that my session can't be reused on a shared terminal.
- **US-A4 (P0)** As an owner, I want my data to be invisible to other businesses, so that my sales and stock stay private.
- **US-A5 (P1)** As an owner, I want to create cashier accounts, so that my staff can bill customers without full access.
- **US-A6 (P1)** As an owner, I want to deactivate a cashier or reset their password, so that I control who can access the system.
- **US-A7 (P2)** As a user, I want my session to refresh silently, so that I'm not logged out mid-shift.

## Epic B — Subscription & Usage

- **US-B1 (P0)** As an owner, I want to see my current plan, status, and monthly bill usage, so that I know how close I am to my limit.
- **US-B2 (P0)** As an owner, I want a warning at 80% usage, so that I can plan an upgrade before hitting the cap.
- **US-B3 (P0)** As a cashier/owner, I want to be blocked from creating bills at 100% usage (or when expired/suspended), so that the platform enforces the plan fairly — with a clear message on what to do.
- **US-B4 (P1)** As an owner, I want my subscription to be activated/upgraded manually after I pay offline, so that I can use the platform without an online payment gateway.
- **US-B5 (P1)** As an owner, I want usage to reset at the start of each month, so that my limit reflects the current billing month.

## Epic C — Billing / POS (highest priority)

- **US-C1 (P0)** As a cashier, I want to search products fast by code/name, so that I can add items quickly during checkout.
- **US-C2 (P0)** As a cashier, I want to add items with quantity and per-line discount, so that I can build an accurate bill.
- **US-C3 (P0)** As a cashier, I want to remove a line or clear the cart, so that I can fix mistakes quickly.
- **US-C4 (P0)** As a cashier, I want a live preview of taxable value, GST, discount, and grand total, so that I can confirm the amount before saving.
- **US-C5 (P0)** As a cashier, I want to save the invoice and have stock + usage update automatically, so that records stay consistent.
- **US-C6 (P0)** As a cashier, I want to choose Cash/UPI/Card or split the payment, so that I can record how the customer paid.
- **US-C7 (P0)** As a cashier, I want to print the invoice immediately, so that I can hand it to the customer.
- **US-C8 (P0)** As a cashier, I want to reprint a previous invoice, so that I can reissue a lost bill.
- **US-C9 (P1)** As a cashier, I want bill-level and line-level notes, so that I can capture special instructions.
- **US-C10 (P1)** As a cashier, I want keyboard shortcuts for search/add/pay/save, so that I can bill without the mouse.

## Epic D — GST

- **US-D1 (P0)** As an owner, I want GST-inclusive pricing where the customer sees only the final price, so that retail counter pricing stays simple.
- **US-D2 (P0)** As an owner, I want GST-exclusive pricing where GST is added on top, so that I can sell to businesses with tax shown separately.
- **US-D3 (P0)** As an owner, I want CGST/SGST/IGST computed and stored per line, so that my reports are auditor-ready.
- **US-D4 (P1)** As an owner, I want the system to pick CGST+SGST vs IGST based on place of supply, so that GST is applied correctly.

## Epic E — Product Management

- **US-E1 (P0)** As an owner, I want to create products with all required fields, so that I can bill and track them.
- **US-E2 (P0)** As an owner, I want to edit and delete products, so that I can keep my catalog accurate.
- **US-E3 (P0)** As an owner/cashier, I want to search products with pagination, so that I can find items in a large catalog.
- **US-E4 (P1)** As an owner, I want product codes to be unique in my shop, so that searches and reports are unambiguous.

## Epic F — Purchases

- **US-F1 (P0)** As an owner, I want to record a purchase with supplier, date, and items, so that I can replenish stock.
- **US-F2 (P0)** As an owner, I want a saved purchase to increase stock automatically, so that inventory stays accurate.
- **US-F3 (P1)** As an owner, I want editing/cancelling a purchase to adjust stock correctly, so that corrections don't corrupt inventory.

## Epic G — Inventory

- **US-G1 (P0)** As an owner, I want to see current stock per product, so that I know what's available.
- **US-G2 (P0)** As an owner, I want a stock ledger of all movements, so that I can audit changes.
- **US-G3 (P1)** As an owner, I want to make manual stock adjustments with a reason, so that I can correct counts after a physical audit.
- **US-G4 (P1)** As an owner, I want a low-stock alert, so that I reorder before running out.

## Epic H — Reports

- **US-H1 (P0)** As an owner, I want daily and monthly sales reports, so that I can track revenue.
- **US-H2 (P0)** As an owner, I want GST Summary and HSN Summary reports, so that I can file returns / hand them to my auditor.
- **US-H3 (P0)** As an owner, I want a current stock report, so that I can value and review inventory.
- **US-H4 (P0)** As an owner, I want to export reports to PDF and Excel, so that I can share and archive them.

## Epic I — Dashboard & Settings

- **US-I1 (P0)** As an owner, I want a dashboard showing today's sales, monthly sales, bill count, subscription usage, and low-stock count, so that I get an at-a-glance view.
- **US-I2 (P1)** As an owner, I want to set my business profile and invoice preferences, so that invoices show correct details.
- **US-I3 (P1)** As an owner, I want to set my default GST pricing mode and place of supply, so that billing defaults match my shop.

## Epic J — Platform / NFR

- **US-J1 (P0)** As a user, I want clear loading, empty, and error states, so that I'm never confused about what's happening.
- **US-J2 (P0)** As a developer, I want the stack to run with one Docker Compose command, so that onboarding and CI are simple.
- **US-J3 (P0)** As a developer, I want ≥80% backend coverage, so that we ship with confidence.
