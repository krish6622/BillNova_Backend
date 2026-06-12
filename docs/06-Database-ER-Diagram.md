# 6. Database ER Diagram & Schema — BillNova Phase 1

PostgreSQL, shared-schema multi-tenancy. Every business table carries `tenant_id`. Money = `NUMERIC(12,2)`; quantities = `NUMERIC(12,3)`; timestamps = `TIMESTAMPTZ`.

## 6.1 ER Diagram (Mermaid)

```mermaid
erDiagram
    TENANTS ||--o{ USERS : has
    TENANTS ||--o{ PRODUCTS : owns
    TENANTS ||--o{ SUPPLIERS : owns
    TENANTS ||--o{ PURCHASES : owns
    TENANTS ||--o{ SALES : owns
    TENANTS ||--o{ INVENTORY_TRANSACTIONS : owns
    TENANTS ||--o{ BILL_USAGE : tracks
    TENANTS ||--|| TENANT_SUBSCRIPTIONS : has

    SUBSCRIPTION_PLANS ||--o{ TENANT_SUBSCRIPTIONS : defines

    SUPPLIERS ||--o{ PURCHASES : supplies
    PURCHASES ||--o{ PURCHASE_ITEMS : contains
    PRODUCTS  ||--o{ PURCHASE_ITEMS : referenced_by

    SALES ||--o{ SALE_ITEMS : contains
    SALES ||--o{ PAYMENTS : settled_by
    PRODUCTS ||--o{ SALE_ITEMS : referenced_by

    PRODUCTS ||--o{ INVENTORY_TRANSACTIONS : moves
    USERS   ||--o{ SALES : created_by

    TENANTS {
        uuid id PK
        string business_name
        string owner_name
        string mobile
        string email
        string gst_number "nullable"
        string subscription_status "Trial|Active|Expired|Suspended"
        string place_of_supply "intra|inter"
        string gst_mode_default "inclusive|exclusive"
        timestamptz created_at
    }
    USERS {
        uuid id PK
        uuid tenant_id FK
        string name
        string email
        string password_hash
        string role "OWNER|CASHIER"
        boolean is_active
        int token_version
        timestamptz created_at
    }
    SUBSCRIPTION_PLANS {
        uuid id PK
        string name "Starter|Standard|Professional"
        int monthly_bill_limit "500|2000|5000"
        numeric price_inr
        boolean is_active
    }
    TENANT_SUBSCRIPTIONS {
        uuid id PK
        uuid tenant_id FK
        uuid plan_id FK
        string status "Trial|Active|Expired|Suspended"
        date period_start
        date period_end
        timestamptz created_at
        timestamptz updated_at
    }
    BILL_USAGE {
        uuid id PK
        uuid tenant_id FK
        int year
        int month
        int bills_count
        timestamptz updated_at
    }
    PRODUCTS {
        uuid id PK
        uuid tenant_id FK
        string product_code
        string name
        string category
        string unit
        numeric purchase_price
        numeric selling_price
        numeric gst_percentage
        string hsn_code
        numeric current_stock
        numeric reorder_level
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    SUPPLIERS {
        uuid id PK
        uuid tenant_id FK
        string name
        string mobile
        string gst_number "nullable"
        timestamptz created_at
    }
    PURCHASES {
        uuid id PK
        uuid tenant_id FK
        uuid supplier_id FK "nullable"
        string supplier_name
        date purchase_date
        numeric total_amount
        numeric total_gst
        string status "active|cancelled"
        timestamptz created_at
    }
    PURCHASE_ITEMS {
        uuid id PK
        uuid tenant_id FK
        uuid purchase_id FK
        uuid product_id FK
        numeric quantity
        numeric purchase_price
        numeric gst_percentage
        numeric gst_amount
        numeric line_total
    }
    SALES {
        uuid id PK
        uuid tenant_id FK
        string invoice_number
        uuid created_by FK
        string gst_mode "inclusive|exclusive"
        string place_of_supply "intra|inter"
        numeric total_taxable
        numeric total_discount
        numeric total_cgst
        numeric total_sgst
        numeric total_igst
        numeric total_gst
        numeric grand_total
        string notes "nullable"
        timestamptz created_at
    }
    SALE_ITEMS {
        uuid id PK
        uuid tenant_id FK
        uuid sale_id FK
        uuid product_id FK
        string product_name "snapshot"
        string hsn_code "snapshot"
        numeric quantity
        numeric unit_price
        numeric discount
        numeric gst_percentage
        numeric taxable_value
        numeric cgst
        numeric sgst
        numeric igst
        numeric line_total
        string notes "nullable"
    }
    PAYMENTS {
        uuid id PK
        uuid tenant_id FK
        uuid sale_id FK
        string mode "Cash|UPI|Card"
        numeric amount
        string reference "nullable"
    }
    INVENTORY_TRANSACTIONS {
        uuid id PK
        uuid tenant_id FK
        uuid product_id FK
        string type "IN|OUT|ADJUST"
        numeric quantity "signed: +in / -out"
        numeric balance_after
        string ref_type "SALE|PURCHASE|ADJUSTMENT"
        uuid ref_id "nullable"
        string reason "nullable"
        timestamptz created_at
    }
```

## 6.2 Table Notes & Constraints

| Table | Key constraints / notes |
|-------|-------------------------|
| **tenants** | `email` unique. `subscription_status` mirrors the active `tenant_subscriptions.status` for quick reads. |
| **users** | Unique `(tenant_id, email)`. `token_version` bumped on logout/password-reset to invalidate refresh tokens. |
| **subscription_plans** | Seeded reference data: Starter/Standard/Professional with limits 500/2000/5000. |
| **tenant_subscriptions** | One active row per tenant; `period_start/end` define the paid window; manual activation updates this. |
| **bill_usage** | Unique `(tenant_id, year, month)`; `bills_count` incremented atomically per saved sale. |
| **products** | Unique `(tenant_id, product_code)`. `current_stock` maintained from inventory transactions. Soft-delete via `is_active`. |
| **suppliers** | Optional master; purchases also store `supplier_name` snapshot for simplicity. |
| **purchases / purchase_items** | Saving writes IN transactions; cancel writes compensating movements. |
| **sales** | Unique `(tenant_id, invoice_number)`. Stores GST mode + place of supply used at sale time. |
| **sale_items** | Snapshots product_name/hsn for historical accuracy; per-line GST split stored. |
| **payments** | One row per mode; split = multiple rows; `SUM(amount) = sales.grand_total` enforced in service + check at write. |
| **inventory_transactions** | Append-only ledger; `quantity` signed; `balance_after` gives running balance; `ref_type/ref_id` links to source. |

## 6.3 Indexes

```text
users                  (tenant_id), unique (tenant_id, email)
products               (tenant_id), unique (tenant_id, product_code),
                       (tenant_id, name), (tenant_id, hsn_code), (tenant_id, is_active)
suppliers              (tenant_id)
purchases              (tenant_id, purchase_date)
purchase_items         (tenant_id, purchase_id), (tenant_id, product_id)
sales                  (tenant_id, created_at), unique (tenant_id, invoice_number)
sale_items             (tenant_id, sale_id), (tenant_id, product_id)
payments               (tenant_id, sale_id)
inventory_transactions (tenant_id, product_id, created_at)
bill_usage             unique (tenant_id, year, month)
tenant_subscriptions   (tenant_id)
```
Composite indexes lead with `tenant_id` so every tenant-scoped query is index-served.

## 6.4 Referential & Integrity Rules

- All FKs include `tenant_id` consistency (enforced in app layer; cross-tenant FKs impossible by construction).
- `NUMERIC` everywhere for money/quantity — no floating point.
- Atomic operations (bill save, purchase save, adjustments) run in a single DB transaction.
- Soft delete for products referenced by history; hard delete only for never-referenced rows.

## 6.5 Seed Data

- `subscription_plans`: Starter (500), Standard (2000), Professional (5000).
- Optional demo tenant + sample products for local dev (behind a seed script, not in prod migrations).
