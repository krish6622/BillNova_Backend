"""Purchases + suppliers + product soft-delete tests."""

from tests.conftest import auth_headers, register

PRODUCT = {
    "product_code": "TS-001",
    "name": "Cotton Saree",
    "unit": "PCS",
    "purchase_price": 600,
    "selling_price": 999,
    "gst_percentage": 5,
    "hsn_code": "5407",
    "current_stock": 50,
    "reorder_level": 5,
}


def _setup(client):
    headers = auth_headers(register(client).json()["access_token"])
    pid = client.post("/api/products", headers=headers, json=PRODUCT).json()["id"]
    return headers, pid


def _purchase_body(pid, qty=10, price=600, gst=5):
    return {
        "supplier_name": "Mills Co",
        "purchase_date": "2026-06-10",
        "items": [{"product_id": pid, "quantity": qty, "purchase_price": price, "gst_percentage": gst}],
    }


def test_create_purchase_increases_stock(client):
    headers, pid = _setup(client)
    resp = client.post("/api/purchases", headers=headers, json=_purchase_body(pid))
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_amount"] == 6300.0  # 6000 + 300 gst
    assert body["total_gst"] == 300.0
    assert body["status"] == "active"

    prod = client.get(f"/api/products/{pid}", headers=headers).json()
    assert prod["current_stock"] == 60.0  # 50 + 10


def test_cancel_purchase_reverses_stock(client):
    headers, pid = _setup(client)
    purchase = client.post("/api/purchases", headers=headers, json=_purchase_body(pid)).json()
    assert client.get(f"/api/products/{pid}", headers=headers).json()["current_stock"] == 60.0

    cancel = client.post(f"/api/purchases/{purchase['id']}/cancel", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert client.get(f"/api/products/{pid}", headers=headers).json()["current_stock"] == 50.0


def test_supplier_crud(client):
    headers, _ = _setup(client)
    created = client.post("/api/suppliers", headers=headers, json={"name": "Mills Co", "mobile": "999"})
    assert created.status_code == 201
    sid = created.json()["id"]

    listed = client.get("/api/suppliers", headers=headers).json()
    assert any(s["id"] == sid for s in listed)

    upd = client.put(f"/api/suppliers/{sid}", headers=headers, json={"gst_number": "33AAA"})
    assert upd.status_code == 200
    assert upd.json()["gst_number"] == "33AAA"


def test_delete_referenced_product_soft_deletes(client):
    headers, pid = _setup(client)
    client.post("/api/purchases", headers=headers, json=_purchase_body(pid))

    # product is now referenced by a purchase -> soft delete (deactivate)
    assert client.delete(f"/api/products/{pid}", headers=headers).status_code == 204
    got = client.get(f"/api/products/{pid}", headers=headers)
    assert got.status_code == 200
    assert got.json()["is_active"] is False


def test_delete_unreferenced_product_hard_deletes(client):
    headers, _ = _setup(client)
    pid2 = client.post(
        "/api/products", headers=headers, json={**PRODUCT, "product_code": "X2"}
    ).json()["id"]
    assert client.delete(f"/api/products/{pid2}", headers=headers).status_code == 204
    assert client.get(f"/api/products/{pid2}", headers=headers).status_code == 404
