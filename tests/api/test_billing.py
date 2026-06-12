"""Billing / POS API tests."""

from datetime import date

from sqlalchemy.orm import sessionmaker

from app.models.usage import BillUsage
from tests.conftest import auth_headers, register

# tenant defaults: gst_mode=inclusive, place=intra
PRODUCT = {
    "product_code": "TS-001",
    "name": "Cotton Saree",
    "unit": "PCS",
    "purchase_price": 600,
    "selling_price": 105,
    "gst_percentage": 5,
    "hsn_code": "5407",
    "current_stock": 50,
    "reorder_level": 5,
}


def _setup(client):
    token = register(client).json()
    headers = auth_headers(token["access_token"])
    pid = client.post("/api/products", headers=headers, json=PRODUCT).json()["id"]
    return token, headers, pid


def test_preview_computes_inclusive_gst(client):
    _, headers, pid = _setup(client)
    resp = client.post(
        "/api/sales/preview",
        headers=headers,
        json={"items": [{"product_id": pid, "quantity": 2}]},
    )
    assert resp.status_code == 200
    totals = resp.json()["totals"]
    assert totals["total_taxable"] == 200.0
    assert totals["total_gst"] == 10.0
    assert totals["grand_total"] == 210.0


def test_save_sale_updates_stock_and_usage(client):
    _, headers, pid = _setup(client)
    resp = client.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": pid, "quantity": 2}],
            "payments": [{"mode": "Cash", "amount": 210}],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["invoice_number"] == f"INV-{date.today().year}-0001"
    assert body["grand_total"] == 210.0
    assert len(body["items"]) == 1 and len(body["payments"]) == 1

    # stock reduced 50 -> 48
    prod = client.get(f"/api/products/{pid}", headers=headers).json()
    assert prod["current_stock"] == 48.0

    # usage incremented
    sub = client.get("/api/subscription", headers=headers).json()
    assert sub["usage"]["bills_count"] == 1


def test_split_payment_ok(client):
    _, headers, pid = _setup(client)
    resp = client.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": pid, "quantity": 2}],
            "payments": [{"mode": "Cash", "amount": 100}, {"mode": "UPI", "amount": 110}],
        },
    )
    assert resp.status_code == 201
    assert len(resp.json()["payments"]) == 2


def test_payment_mismatch_rejected(client):
    _, headers, pid = _setup(client)
    resp = client.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": pid, "quantity": 2}],
            "payments": [{"mode": "Cash", "amount": 200}],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "PAYMENT_MISMATCH"


def test_insufficient_stock_rejected(client):
    _, headers, pid = _setup(client)
    resp = client.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": pid, "quantity": 9999}],
            "payments": [{"mode": "Cash", "amount": 1}],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_subscription_limit_blocks_billing(client, engine):
    token, headers, pid = _setup(client)
    tenant_id = token["tenant"]["id"]

    # Force this month's usage to the trial quota (50).
    Session = sessionmaker(bind=engine, future=True)
    s = Session()
    today = date.today()
    s.add(BillUsage(tenant_id=tenant_id, year=today.year, month=today.month, bills_count=50))
    s.commit()
    s.close()

    resp = client.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": pid, "quantity": 1}],
            "payments": [{"mode": "Cash", "amount": 105}],
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SUBSCRIPTION_LIMIT_REACHED"


def test_get_and_list_and_invoice(client):
    _, headers, pid = _setup(client)
    sale = client.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": pid, "quantity": 1}],
            "payments": [{"mode": "Cash", "amount": 105}],
        },
    ).json()

    got = client.get(f"/api/sales/{sale['id']}", headers=headers)
    assert got.status_code == 200

    listing = client.get("/api/sales", headers=headers).json()
    assert listing["total"] == 1

    invoice = client.get(f"/api/sales/{sale['id']}/invoice", headers=headers).json()
    assert invoice["business"]["business_name"] == "Sri Textiles"
    assert invoice["sale"]["invoice_number"] == f"INV-{date.today().year}-0001"


def test_cashier_can_create_bill(client):
    _, owner_headers, pid = _setup(client)
    client.post(
        "/api/users", headers=owner_headers,
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    cashier = client.post(
        "/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"}
    ).json()["access_token"]

    resp = client.post(
        "/api/sales",
        headers=auth_headers(cashier),
        json={
            "items": [{"product_id": pid, "quantity": 1}],
            "payments": [{"mode": "Cash", "amount": 105}],
        },
    )
    assert resp.status_code == 201
