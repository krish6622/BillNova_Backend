"""RBAC enhancement — cashier lockdown, owner full access, and audit logging.

Roles: OWNER (Admin / business owner) and CASHIER (billing-only staff). A cashier may
operate the POS and view/reprint invoices but must be blocked from every administrative
surface, and each block must be recorded in the access audit log.
"""

import pytest

from tests.conftest import auth_headers, register, seed_product


def _owner_token(client) -> str:
    return register(client).json()["access_token"]


def _make_cashier(client, owner_token: str, *, email: str = "cash@shop.in", password: str = "cashierpass1"):
    """Create a cashier under the owner's tenant and return its login token."""
    resp = client.post(
        "/api/users",
        headers=auth_headers(owner_token),
        json={"name": "Cashier", "email": email, "password": password, "role": "CASHIER"},
    )
    assert resp.status_code == 201, resp.text
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


@pytest.fixture
def owner_and_cashier(client):
    owner = _owner_token(client)
    cashier = _make_cashier(client, owner)
    return owner, cashier


def _bill(client, headers, product_id: str, qty: int = 1) -> str:
    """Create a sale (payments must equal the previewed grand total) and return its id."""
    items = [{"product_id": product_id, "quantity": qty}]
    preview = client.post(
        "/api/sales/preview", headers=headers, json={"items": items, "gst_mode": "inclusive"}
    )
    assert preview.status_code == 200, preview.text
    total = preview.json()["totals"]["grand_total"]
    sale = client.post(
        "/api/sales", headers=headers,
        json={"items": items, "payments": [{"mode": "Cash", "amount": total}], "gst_mode": "inclusive"},
    )
    assert sale.status_code == 201, sale.text
    return sale.json()["id"]


# ---- Cashier is denied every administrative surface -----------------------

# (path, method) pairs a cashier must NOT reach. GETs for reads, POST/PUT for writes.
FORBIDDEN_FOR_CASHIER = [
    ("get", "/api/settings"),
    ("put", "/api/settings"),
    ("get", "/api/users"),
    ("post", "/api/users"),
    ("get", "/api/users/audit-logs"),
    ("get", "/api/purchases"),
    ("post", "/api/purchases"),
    ("get", "/api/reports/sales/daily"),
    ("get", "/api/reports/inventory/stock"),
    ("get", "/api/inventory/stock"),
    ("post", "/api/inventory/adjust"),
    ("get", "/api/suppliers"),
]


@pytest.mark.parametrize("method,path", FORBIDDEN_FOR_CASHIER)
def test_cashier_blocked_from_admin_endpoints(owner_and_cashier, client, method, path):
    _owner, cashier = owner_and_cashier
    kwargs = {"headers": auth_headers(cashier)}
    if method != "get":
        kwargs["json"] = {}
    resp = getattr(client, method)(path, **kwargs)
    assert resp.status_code == 403, f"{method.upper()} {path} should be 403 for cashier"
    assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_cashier_cannot_manage_products(owner_and_cashier, client):
    _owner, cashier = owner_and_cashier
    # Read is allowed (POS lookup); create/update/delete are Owner-only.
    assert client.get("/api/products", headers=auth_headers(cashier)).status_code == 200
    assert client.put(
        "/api/products/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(cashier), json={"reorder_level": 5},
    ).status_code == 403


# ---- Cashier CAN do their job ---------------------------------------------

def test_cashier_can_bill_and_use_register(owner_and_cashier, client):
    owner, cashier = owner_and_cashier
    product = seed_product(client, auth_headers(owner), code="P1", qty=10)

    # POS billing works for the cashier.
    sale_id = _bill(client, auth_headers(cashier), product["id"], qty=2)

    # Invoice register: list, view, reprint all allowed.
    assert client.get("/api/invoices", headers=auth_headers(cashier)).status_code == 200
    assert client.get(f"/api/invoices/{sale_id}", headers=auth_headers(cashier)).status_code == 200
    assert client.post(f"/api/invoices/{sale_id}/reprint", headers=auth_headers(cashier)).status_code == 200


def test_cashier_cannot_void_or_export_invoice(owner_and_cashier, client):
    owner, cashier = owner_and_cashier
    product = seed_product(client, auth_headers(owner), code="P2", qty=10)
    sale_id = _bill(client, auth_headers(cashier), product["id"], qty=1)

    assert client.post(f"/api/invoices/{sale_id}/void", headers=auth_headers(cashier)).status_code == 403
    assert client.get(f"/api/invoices/{sale_id}/pdf", headers=auth_headers(cashier)).status_code == 403
    # Owner can void and export the same invoice.
    assert client.get(f"/api/invoices/{sale_id}/pdf", headers=auth_headers(owner)).status_code == 200
    assert client.post(f"/api/invoices/{sale_id}/void", headers=auth_headers(owner)).status_code == 200


# ---- Owner retains full access --------------------------------------------

def test_owner_has_full_access(client):
    owner = _owner_token(client)
    for path in ["/api/settings", "/api/users", "/api/purchases",
                 "/api/reports/sales/daily", "/api/inventory/stock", "/api/dashboard"]:
        assert client.get(path, headers=auth_headers(owner)).status_code == 200, path


# ---- Role-scoped dashboard ------------------------------------------------

def test_dashboard_is_role_scoped(owner_and_cashier, client):
    owner, cashier = owner_and_cashier
    owner_dash = client.get("/api/dashboard", headers=auth_headers(owner)).json()
    cashier_dash = client.get("/api/dashboard", headers=auth_headers(cashier)).json()

    assert owner_dash["scope"] == "owner"
    assert "top_products" in owner_dash and "monthly_sales" in owner_dash

    # Cashier sees only their own billing summary — no business analytics.
    assert cashier_dash["scope"] == "cashier"
    assert "recent_bills" in cashier_dash and "bills_generated" in cashier_dash
    for leaked in ("monthly_sales", "top_products", "low_stock_count", "subscription"):
        assert leaked not in cashier_dash


# ---- Audit logging --------------------------------------------------------

def test_denied_access_is_audited(owner_and_cashier, client):
    owner, cashier = owner_and_cashier
    # Cashier triggers a couple of denials.
    client.get("/api/settings", headers=auth_headers(cashier))
    client.get("/api/users", headers=auth_headers(cashier))

    logs = client.get("/api/users/audit-logs", headers=auth_headers(owner))
    assert logs.status_code == 200
    rows = logs.json()
    assert len(rows) >= 2
    paths = {r["path"] for r in rows}
    assert "/api/settings" in paths and "/api/users" in paths
    assert all(r["result"] == "ACCESS_DENIED" for r in rows)
    assert all(r["role"] == "CASHIER" for r in rows)
