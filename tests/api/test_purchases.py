"""Purchases + suppliers tests (CR-1: purchases create/restock products)."""

from tests.conftest import auth_headers, register, seed_product


def _owner(client):
    return auth_headers(register(client).json()["access_token"])


def test_create_purchase_inline_creates_product_and_stock(client):
    headers = _owner(client)
    resp = client.post("/api/purchases", headers=headers, json={
        "supplier_name": "Mills Co", "purchase_date": "2026-06-10",
        "items": [{"product_name": "Cotton Saree", "hsn_code": "5407", "gst_percentage": 5,
                   "purchase_price": 600, "margin_type": "amount", "margin_value": 399, "quantity": 10}],
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_amount"] == 6300.0  # 6000 + 300 gst
    assert body["total_gst"] == 300.0
    assert body["status"] == "active"

    prod = next(p for p in client.get("/api/products", headers=headers).json()["items"] if p["name"] == "Cotton Saree")
    assert prod["current_stock"] == 10.0
    assert prod["selling_price"] == 999.0  # 600 + 399


def test_cancel_purchase_reverses_stock(client):
    headers = _owner(client)
    p = seed_product(client, headers, code="TS-1", qty=50)
    # restock +10 via a second purchase, then cancel it
    purchase = client.post("/api/purchases", headers=headers, json={
        "supplier_name": "Mills Co", "purchase_date": "2026-06-10",
        "items": [{"product_id": p["id"], "purchase_price": 600, "margin_type": "amount",
                   "margin_value": 399, "gst_percentage": 5, "quantity": 10}],
    }).json()
    assert client.get(f"/api/products/{p['id']}", headers=headers).json()["current_stock"] == 60.0

    cancel = client.post(f"/api/purchases/{purchase['id']}/cancel", headers=headers)
    assert cancel.status_code == 200 and cancel.json()["status"] == "cancelled"
    assert client.get(f"/api/products/{p['id']}", headers=headers).json()["current_stock"] == 50.0


def test_supplier_crud(client):
    headers = _owner(client)
    created = client.post("/api/suppliers", headers=headers, json={"name": "Mills Co", "mobile": "999"})
    assert created.status_code == 201
    sid = created.json()["id"]
    assert any(s["id"] == sid for s in client.get("/api/suppliers", headers=headers).json())
    upd = client.put(f"/api/suppliers/{sid}", headers=headers, json={"gst_number": "33AAA"})
    assert upd.status_code == 200 and upd.json()["gst_number"] == "33AAA"


def test_purchases_owner_only(client):
    owner = _owner(client)
    client.post("/api/users", headers=owner,
                json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"})
    cashier = auth_headers(
        client.post("/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"}).json()["access_token"]
    )
    assert client.get("/api/purchases", headers=cashier).status_code == 403
