# 1. Functional Requirement Document (FRD) — BillNova Phase 1

## 1.1 Document Purpose

This FRD defines the functional scope of BillNova Phase 1. It is the source of truth for what the system must do. Anything not listed here is out of Phase 1 scope.

## 1.2 Product Summary

BillNova is a multi-tenant SaaS billing/POS platform for small Indian retail businesses. Each business is a **tenant**. An Owner registers a business, manages products/purchases/inventory, runs a fast POS to bill customers, and views reports. Subscriptions gate monthly bill volume and are activated manually (no payment gateway in Phase 1).

## 1.3 Actors

| Actor | Description |
|-------|-------------|
| **Owner** | Registers the business, full access to all modules, manages users, subscription is bound to their tenant. |
| **Cashier** | Staff user created by the Owner. Can create bills and view products only. |
| **System** | Background/derived behaviors: usage counting, stock movements, GST computation, subscription expiry checks. |
| **Platform Admin** (manual ops) | Out-of-app for Phase 1; activates/changes subscriptions directly (documented as a manual procedure / internal endpoint). |

## 1.4 Functional Modules

### FR-1 Multi-Tenancy
- FR-1.1 Each tenant stores: Business Name, Owner Name, Mobile Number, Email, GST Number (optional), Subscription Status, Created Date.
- FR-1.2 Every business data row (products, sales, purchases, inventory, etc.) is scoped by `tenant_id`.
- FR-1.3 A user belongs to exactly one tenant. Cross-tenant data access is impossible.
- FR-1.4 Tenant isolation is enforced at the data-access layer (every query filters by `tenant_id` from the JWT), not just the UI.

### FR-2 Authentication & Authorization
- FR-2.1 Owner self-registration creates a tenant + the first Owner user atomically.
- FR-2.2 Login issues a JWT access token (and refresh token) containing `sub` (user id), `tenant_id`, `role`.
- FR-2.3 Logout invalidates the refresh token (server-side revocation list / token version).
- FR-2.4 Passwords hashed with Passlib (bcrypt). Never stored or logged in plaintext.
- FR-2.5 Roles: **Owner** (all modules) and **Cashier** (create bills, view products). RBAC enforced server-side on every endpoint.
- FR-2.6 Owner can create, deactivate, and reset password for Cashier users within their tenant.

### FR-3 Subscription & Usage
- FR-3.1 Subscription statuses: **Trial**, **Active**, **Expired**, **Suspended**.
- FR-3.2 Plans: **Starter** (500 bills/mo), **Standard** (2,000 bills/mo), **Professional** (5,000 bills/mo).
- FR-3.3 On registration, tenant starts in **Trial** (configurable trial length + trial bill quota).
- FR-3.4 Monthly bill usage is tracked per tenant per calendar month (`BillUsage`).
- FR-3.5 Warning surfaced at **80%** usage; hard block at **100%** usage.
- FR-3.6 When usage ≥ limit OR status ∈ {Expired, Suspended}, creating new bills is **prevented** with a clear error. Reprint/print of existing bills still allowed.
- FR-3.7 Subscription activation/upgrade is **manual** (no payment gateway). An internal/admin operation sets plan + status + period.

### FR-4 Billing / POS (Highest Priority)
- FR-4.1 Fast product search (by code/name/HSN), keyboard-friendly.
- FR-4.2 Add product to cart; set quantity; per-line discount; bill-level discount.
- FR-4.3 Per-line and bill-level notes.
- FR-4.4 Remove a line item; clear cart.
- FR-4.5 Live bill preview with taxable value, GST breakup, discount, and grand total.
- FR-4.6 Save invoice → persists Sale + SaleItems + Payments + InventoryTransactions, increments usage, decrements stock — atomically.
- FR-4.7 Print invoice (print-friendly layout). Reprint any previous invoice.
- FR-4.8 Payment modes: **Cash, UPI, Card, Split Payment** (split = multiple payment rows summing to grand total).
- FR-4.9 Each sale gets a tenant-scoped sequential invoice number.
- FR-4.10 A bill cannot be saved if it would drive stock negative (configurable: block vs. allow-negative warning).

### FR-5 GST Handling
- FR-5.1 Support **GST Inclusive** pricing: selling price already includes GST; system back-computes taxable value and GST.
- FR-5.2 Support **GST Exclusive** pricing: GST added on top of selling price.
- FR-5.3 Compute and store: Taxable Value, GST Amount, CGST, SGST, IGST per line.
- FR-5.4 Intra-state → CGST + SGST (half each); inter-state → IGST. Phase 1 default = intra-state (CGST+SGST); a tenant "place of supply" flag selects IGST.
- FR-5.5 GST rate comes from the product's GST Percentage.
- FR-5.6 Produce auditor-ready GST Summary and HSN Summary reports.

### FR-6 Product Management
- FR-6.1 Fields: Product Code, Product Name, Category, Unit, Purchase Price, Selling Price, GST Percentage, HSN Code, Current Stock, Active Status.
- FR-6.2 Create, Edit, Delete (soft delete if referenced by sales/purchases), Search, Pagination.
- FR-6.3 Product Code unique per tenant.

### FR-7 Purchase Module
- FR-7.1 Fields: Supplier Name, Purchase Date, Purchase Items (product, quantity, purchase price, GST).
- FR-7.2 Saving a purchase increases inventory automatically (InventoryTransaction IN).
- FR-7.3 Editing/cancelling a purchase reverses/adjusts the stock movement accordingly.

### FR-8 Inventory
- FR-8.1 Current stock per product (derived from transactions / maintained cache).
- FR-8.2 Stock Ledger: chronological IN/OUT/ADJUST transactions per product.
- FR-8.3 Manual stock adjustment with reason.
- FR-8.4 Low stock alert when current stock ≤ reorder threshold.
- FR-8.5 Sales reduce stock automatically; purchases increase stock automatically.

### FR-9 Reports
- FR-9.1 Sales: Daily Sales, Monthly Sales.
- FR-9.2 GST: GST Summary, HSN Summary.
- FR-9.3 Inventory: Current Stock Report.
- FR-9.4 Export to **PDF** and **Excel**.
- FR-9.5 All reports tenant-scoped and date-filterable.

### FR-10 Dashboard
- FR-10.1 Today's Sales, Monthly Sales, Number of Bills (this month), Subscription Usage (used/limit + %), Low Stock Count.

### FR-11 Settings
- FR-11.1 Business profile (name, GST number, contact, address for invoice header).
- FR-11.2 GST pricing mode default (inclusive/exclusive), place-of-supply.
- FR-11.3 User management (Owner only).
- FR-11.4 Invoice preferences (prefix, footer note).

## 1.5 Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | POS save round-trip target < 400ms on typical hardware. |
| NFR-2 | Tenant data isolation guaranteed; no cross-tenant leakage. |
| NFR-3 | Backend test coverage ≥ 80%. |
| NFR-4 | Responsive UI (desktop-first POS, usable on tablet). |
| NFR-5 | Keyboard-friendly POS (search focus, add, qty, pay, save via shortcuts). |
| NFR-6 | All money math uses fixed-precision decimals (no float drift); rounding rules documented. |
| NFR-7 | Dockerized; one-command local bring-up via Docker Compose. |
| NFR-8 | Clear loading / empty / error states across all pages. |
| NFR-9 | Secrets via environment variables only; never committed. |

## 1.6 Out of Scope (Phase 1)

- Payment gateway / online payments / auto-billing.
- E-invoicing / IRN / e-way bill government integration.
- Multi-branch / multi-warehouse per tenant.
- Customer master / loyalty / CRM.
- Barcode hardware integration (search-by-code only; scanner emits text, so it works, but no device config).
- Returns/credit notes, supplier payments/ledger, expense tracking.
- Mobile native apps.
- Advanced analytics / charts beyond the dashboard cards.

## 1.7 Assumptions

- Single currency: INR (₹).
- Single GST registration per tenant.
- Trial length and trial quota are config values (defaults: 14 days / 50 bills) — confirm at sign-off.
- Reorder threshold is a per-product field; default 0 (no alert) until set.
- Calendar-month usage windows reset on the 1st (server timezone Asia/Kolkata).

## 1.8 Open Questions (confirm before build)

1. Trial defaults (days + bill quota)?
2. Negative stock: hard-block at POS, or warn-and-allow?
3. Invoice numbering format (e.g., `INV-2026-0001` vs `0001`)?
4. Who performs manual subscription activation — Owner self-service request + internal admin endpoint, or a super-admin console (deferred)?
