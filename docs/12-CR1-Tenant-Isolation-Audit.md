# CR-1 — Deliverable 7: Repository Tenant-Isolation Audit

**Principle:** tenant id comes only from the JWT (`get_current_tenant_id`) — never from a request body/query.
Every business-table read/write filters `tenant_id`. Cross-tenant access returns **404** (existence not leaked).

## Audit results

| Module | Scoping | Status |
|--------|---------|--------|
| `repositories/base.TenantRepository` | `_scoped()` adds `WHERE tenant_id`; `get()` returns None if `obj.tenant_id != tenant_id` | ✅ |
| `repositories/product_repo` | all queries via `_scoped()` / `code_exists` scoped | ✅ |
| `services/product_service` | recent/top-selling/list/get/update all `WHERE tenant_id`; top-selling subquery filters `SaleItem.tenant_id` and re-filters `Product.tenant_id` | ✅ |
| `services/billing_service` | `_load_products`, `get_sale`, `list_sales` all tenant-scoped; sale/items/payments/txns written with `tenant_id` | ✅ |
| `services/purchase_service` | `_resolve_product` checks `tenant_id`; `get/list/cancel` scoped; items/txns written with `tenant_id` | ✅ |
| `services/inventory_service` | stock list / ledger / adjust / low-stock all `WHERE tenant_id` | ✅ |
| `services/supplier_service` | list/update scoped (`tenant_id`) | ✅ |
| `services/report_service` | daily/monthly/gst/hsn/stock/top-products all filter `tenant_id` (and join `Sale.tenant_id`) | ✅ |
| `services/subscription_service` | summary/usage/guard/activate scoped by `tenant_id` | ✅ |
| `services/settings_service` | `Tenant` fetched by id-from-JWT | ✅ |
| `services/dashboard_service` | composes the above (all scoped) | ✅ |
| `repositories/user_repo` | `list` scoped; `get_user_in_tenant` checks tenant | ✅ |
| `services/auth_service` | register/login | ⚠️ `get_user_by_email` is **intentionally global** (login has no tenant context yet). Email is globally unique, so this is a lookup, not data exposure. |

## Conclusion

No missing tenant filters on business data. The cross-tenant visibility reported in the field was a **frontend
query-cache bleed** (cache not cleared on account switch), fixed in CR-1.7 by `queryClient.clear()` on
login/register/logout. Structural guarantees (composite `tenant_id`-leading indexes + `UNIQUE(tenant_id, …)`)
remain in place. The `tenant_isolation` API tests assert cross-tenant `GET → 404` and scoped listings.
