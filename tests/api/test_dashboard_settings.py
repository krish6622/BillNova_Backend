"""Dashboard KPIs + settings tests."""

from datetime import date

from tests.conftest import auth_headers, register

PRODUCT = {
    "product_code": "TS-001",
    "name": "Cotton Saree",
    "unit": "PCS",
    "purchase_price": 600,
    "selling_price": 105,
    "gst_percentage": 5,
    "hsn_code": "5407",
    "current_stock": 3,
    "reorder_level": 5,  # below reorder -> low stock
}


def _setup(client):
    headers = auth_headers(register(client).json()["access_token"])
    pid = client.post("/api/products", headers=headers, json=PRODUCT).json()["id"]
    return headers, pid


def test_dashboard_kpis(client):
    headers, pid = _setup(client)
    client.post(
        "/api/sales", headers=headers,
        json={"items": [{"product_id": pid, "quantity": 2}], "payments": [{"mode": "Cash", "amount": 210}]},
    )
    resp = client.get("/api/dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["today_sales"] == {"amount": 210.0, "count": 1}
    assert body["bills_this_month"] == 1
    assert body["subscription"]["used"] == 1
    assert body["low_stock_count"] == 1  # stock 1 (3-2) <= reorder 5


def test_settings_get_and_update(client):
    headers, _ = _setup(client)
    got = client.get("/api/settings", headers=headers)
    assert got.status_code == 200
    assert got.json()["invoice_prefix"] == "INV"
    assert got.json()["gst_mode_default"] == "inclusive"

    upd = client.put(
        "/api/settings",
        headers=headers,
        json={"gst_mode_default": "exclusive", "invoice_prefix": "BILL", "address": "Main Rd"},
    )
    assert upd.status_code == 200
    assert upd.json()["gst_mode_default"] == "exclusive"
    assert upd.json()["invoice_prefix"] == "BILL"
    assert upd.json()["address"] == "Main Rd"


def test_invoice_prefix_applies_to_new_sales(client):
    headers, pid = _setup(client)
    client.put("/api/settings", headers=headers, json={"invoice_prefix": "BILL"})
    sale = client.post(
        "/api/sales", headers=headers,
        json={"items": [{"product_id": pid, "quantity": 1}], "payments": [{"mode": "Cash", "amount": 105}]},
    ).json()
    assert sale["invoice_number"] == f"BILL-{date.today().year}-0001"


def test_settings_owner_only(client):
    headers, _ = _setup(client)
    client.post(
        "/api/users", headers=headers,
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    cashier = client.post(
        "/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"}
    ).json()["access_token"]
    assert client.get("/api/settings", headers=auth_headers(cashier)).status_code == 403
