"""Central RBAC permission matrix.

Single source of truth for "which role may do what". Roles are the existing
``OWNER`` (a.k.a. Admin / business owner) and ``CASHIER`` (billing-only staff).

Permissions are ``resource:action`` strings. The matrix is intentionally explicit
(no wildcards for CASHIER) so the blast radius of a cashier account is obvious at a
glance and easy to test. The same matrix is mirrored on the frontend in
``src/lib/rbac.ts`` — keep the two in sync.
"""

from app.models.user import ROLE_CASHIER, ROLE_OWNER

# ---- Permission catalogue -------------------------------------------------
# Dashboard / billing surface available to every authenticated user.
DASHBOARD_VIEW = "dashboard:view"
SALE_CREATE = "sale:create"          # operate the POS, take payments
INVOICE_VIEW = "invoice:view"        # list / search / view in the register
INVOICE_REPRINT = "invoice:reprint"  # re-fetch + reprint an existing bill
PRODUCT_VIEW = "product:view"        # read-only product lookup (POS search)

# Owner-only (administrative / business) permissions.
INVOICE_VOID = "invoice:void"
INVOICE_EXPORT = "invoice:export"    # PDF download / auditor exports
PRODUCT_MANAGE = "product:manage"
PURCHASE_MANAGE = "purchase:manage"
SUPPLIER_MANAGE = "supplier:manage"
INVENTORY_VIEW = "inventory:view"
INVENTORY_ADJUST = "inventory:adjust"
REPORT_VIEW = "report:view"
SETTINGS_MANAGE = "settings:manage"
USER_MANAGE = "user:manage"
AUDIT_VIEW = "audit:view"

# Permissions granted to a cashier. Everything not in this set is Owner-only.
_CASHIER_PERMISSIONS: frozenset[str] = frozenset(
    {
        DASHBOARD_VIEW,
        SALE_CREATE,
        INVOICE_VIEW,
        INVOICE_REPRINT,
        PRODUCT_VIEW,
    }
)

# The Owner (Admin) can do everything: the cashier set plus all administrative ones.
_OWNER_PERMISSIONS: frozenset[str] = _CASHIER_PERMISSIONS | frozenset(
    {
        INVOICE_VOID,
        INVOICE_EXPORT,
        PRODUCT_MANAGE,
        PURCHASE_MANAGE,
        SUPPLIER_MANAGE,
        INVENTORY_VIEW,
        INVENTORY_ADJUST,
        REPORT_VIEW,
        SETTINGS_MANAGE,
        USER_MANAGE,
        AUDIT_VIEW,
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_OWNER: _OWNER_PERMISSIONS,
    ROLE_CASHIER: _CASHIER_PERMISSIONS,
}


def has_permission(role: str, permission: str) -> bool:
    """True if ``role`` is granted ``permission`` by the matrix."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
