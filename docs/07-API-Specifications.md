# 7. API Specifications — BillNova Phase 1

Base path: `/api`. All responses JSON. Auth via `Authorization: Bearer <access_token>` except auth endpoints. Every business endpoint is implicitly tenant-scoped from the token — clients never send `tenant_id`.

## 7.1 Conventions

- **Auth header:** `Authorization: Bearer <jwt>`.
- **Pagination:** `?page=1&limit=20&search=` → `{ "items": [...], "total": N, "page": 1, "limit": 20 }`.
- **Errors:** `{ "error": { "code": "STRING_CODE", "message": "...", "details": {} } }`.
- **Roles:** `O` = Owner only, `C` = Cashier allowed (Owner always allowed). `*` = any authenticated.
- **IDs:** UUID. **Money:** decimal strings/numbers, 2 dp. **Dates:** ISO 8601.

---

## 7.2 Auth — `/api/auth`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/register` | public | Create tenant + Owner; returns tokens. |
| POST | `/login` | public | Email + password → tokens. |
| POST | `/refresh` | public | Refresh token → new access token. |
| POST | `/logout` | * | Revoke refresh token (bump token_version). |
| GET | `/me` | * | Current user + tenant + role + subscription summary. |

**POST /register**
```json
// request
{ "business_name": "Sri Textiles", "owner_name": "Ravi", "mobile": "9876543210",
  "email": "ravi@shop.in", "password": "•••••", "gst_number": "33ABCDE1234F1Z5" }
// 201
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer",
  "user": { "id": "...", "name": "Ravi", "role": "OWNER" },
  "tenant": { "id": "...", "business_name": "Sri Textiles", "subscription_status": "Trial" } }
```

**POST /login** → `{ access_token, refresh_token, token_type, user, tenant }`.

---

## 7.3 Users — `/api/users` (Owner)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/users` | O | List users in tenant. |
| POST | `/users` | O | Create Cashier (name, email, password, role=CASHIER). |
| PATCH | `/users/{id}` | O | Update name / is_active. |
| POST | `/users/{id}/reset-password` | O | Set new password. |

---

## 7.4 Subscription & Usage — `/api/subscription`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/subscription` | * | Current plan, status, period, limit, current-month usage, percent. |
| GET | `/subscription/plans` | * | List plans (Starter/Standard/Professional). |
| POST | `/subscription/activate` | admin/internal | Manual activate/upgrade: `{ plan_id, status, period_start, period_end }`. No payment gateway. |

```json
// GET /subscription → 200
{ "plan": "Standard", "status": "Active", "monthly_bill_limit": 2000,
  "usage": { "year": 2026, "month": 6, "bills_count": 1640, "percent": 82.0 },
  "warning": "APPROACHING_LIMIT", "period_end": "2026-07-31" }
```

---

## 7.5 Products — `/api/products`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/products` | C | List/search (`search`, `page`, `limit`, `active`). |
| GET | `/products/{id}` | C | Get one. |
| POST | `/products` | O | Create. |
| PUT | `/products/{id}` | O | Update. |
| DELETE | `/products/{id}` | O | Delete (soft if referenced). |

```json
// POST /products
{ "product_code": "TS-001", "name": "Cotton Saree", "category": "Sarees",
  "unit": "PCS", "purchase_price": 600.00, "selling_price": 999.00,
  "gst_percentage": 5, "hsn_code": "5407", "current_stock": 50, "reorder_level": 5 }
```

---

## 7.6 Billing / POS — `/api/sales`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/sales/preview` | C | Compute totals/GST for a cart without saving. |
| POST | `/sales` | C | Save bill (atomic; subscription + stock guarded). |
| GET | `/sales` | C | List sales (date filter, pagination). |
| GET | `/sales/{id}` | C | Get sale detail (for reprint). |
| GET | `/sales/{id}/invoice` | C | Print payload / rendered invoice (HTML/PDF). |

**POST /sales** (request)
```json
{ "gst_mode": "inclusive", "place_of_supply": "intra",
  "items": [
    { "product_id": "...", "quantity": 2, "discount": 0, "notes": null }
  ],
  "bill_discount": 0, "notes": "Festival sale",
  "payments": [ { "mode": "Cash", "amount": 1500.00 }, { "mode": "UPI", "amount": 498.00 } ] }
```
**Responses:** `201` with sale + invoice_number; `403 SUBSCRIPTION_LIMIT_REACHED` / `SUBSCRIPTION_INACTIVE`; `422 PAYMENT_MISMATCH` (payments ≠ grand total); `422 INSUFFICIENT_STOCK` (if hard-block on).

**POST /sales/preview** returns the same computed totals block (taxable, cgst, sgst, igst, discount, grand_total, per-line breakup) — used for live POS preview.

---

## 7.7 Suppliers — `/api/suppliers` (Owner)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/suppliers` | O | List/search. |
| POST | `/suppliers` | O | Create. |
| PUT | `/suppliers/{id}` | O | Update. |

---

## 7.8 Purchases — `/api/purchases` (Owner)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/purchases` | O | List (date filter, pagination). |
| GET | `/purchases/{id}` | O | Detail. |
| POST | `/purchases` | O | Create → increases stock (atomic). |
| POST | `/purchases/{id}/cancel` | O | Cancel → compensating stock movement. |

```json
// POST /purchases
{ "supplier_name": "Mills Co", "supplier_id": null, "purchase_date": "2026-06-10",
  "items": [ { "product_id": "...", "quantity": 100, "purchase_price": 600.00, "gst_percentage": 5 } ] }
```

---

## 7.9 Inventory — `/api/inventory`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/inventory/stock` | O | Current stock list (search, pagination). |
| GET | `/inventory/ledger/{product_id}` | O | Stock ledger (IN/OUT/ADJUST, running balance). |
| POST | `/inventory/adjust` | O | Manual adjustment: `{ product_id, delta, reason }`. |
| GET | `/inventory/low-stock` | O | Products at/below reorder level. |

---

## 7.10 Reports — `/api/reports`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/reports/sales/daily?date=` | O | Daily sales summary + lines. |
| GET | `/reports/sales/monthly?year=&month=` | O | Monthly sales summary. |
| GET | `/reports/gst/summary?from=&to=` | O | GST summary by rate (taxable, CGST/SGST/IGST). |
| GET | `/reports/gst/hsn?from=&to=` | O | HSN summary (qty, taxable, tax by HSN). |
| GET | `/reports/inventory/stock` | O | Current stock valuation. |
| GET | `/reports/{report}/export?format=pdf\|excel&...` | O | Export same data to PDF/Excel. |

---

## 7.11 Dashboard — `/api/dashboard`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/dashboard` | * | KPIs: today_sales, monthly_sales, bills_this_month, subscription usage, low_stock_count. |

```json
// GET /dashboard → 200
{ "today_sales": { "amount": 18450.00, "count": 23 },
  "monthly_sales": { "amount": 542300.00, "count": 640 },
  "bills_this_month": 640,
  "subscription": { "plan": "Standard", "limit": 2000, "used": 640, "percent": 32.0 },
  "low_stock_count": 7 }
```

---

## 7.12 Settings — `/api/settings` (Owner)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/settings` | O | Business profile + invoice + GST defaults. |
| PUT | `/settings` | O | Update profile, invoice prefix/footer, gst_mode_default, place_of_supply. |

---

## 7.13 System

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/health` | public | Liveness/readiness. |

---

## 7.14 Error Codes (catalog)

| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 422 | Bad/missing fields. |
| `INVALID_CREDENTIALS` | 401 | Login failed (generic). |
| `TOKEN_EXPIRED` / `TOKEN_INVALID` | 401 | Auth token issue. |
| `FORBIDDEN_ROLE` | 403 | Role lacks permission. |
| `SUBSCRIPTION_LIMIT_REACHED` | 403 | Monthly bill cap hit. |
| `SUBSCRIPTION_INACTIVE` | 403 | Expired/Suspended. |
| `PAYMENT_MISMATCH` | 422 | Payments ≠ grand total. |
| `INSUFFICIENT_STOCK` | 422 | Not enough stock (hard-block mode). |
| `DUPLICATE_RESOURCE` | 409 | Unique constraint (e.g., product code, email). |
| `NOT_FOUND` | 404 | Missing or cross-tenant resource. |
| `INTERNAL_ERROR` | 500 | Unhandled server error. |

> OpenAPI/Swagger is auto-generated by FastAPI at `/docs` once code is built; this document is the contract it must satisfy.
