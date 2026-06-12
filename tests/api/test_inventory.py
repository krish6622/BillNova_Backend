"""Inventory tests: stock list, ledger, adjustment, low-stock."""

from tests.conftest import auth_headers, register

PRODUCT = {
    "product_code": "TS-001",
    "name": "Cotton Saree",
    "unit": "PCS",
    "purchase_price": 600,
    "selling_price": 999,
    "gst_percentage": 5,
    "current_stock": 50,
    "reorder_level": 5,
}


def _setup(client, **overrides):
    headers = auth_headers(register(client).json()["access_token"])
    pid = client.post("/api/products", headers=headers, json={**PRODUCT, **overrides}).json()["id"]
    return headers, pid


def test_stock_list_includes_value(client):
    headers, _ = _setup(client)
    resp = client.get("/api/inventory/stock", headers=headers)
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["current_stock"] == 50.0
    assert item["stock_value"] == 30000.0  # 50 * 600


def test_manual_adjustment_updates_stock_and_ledger(client):
    headers, pid = _setup(client)
    adj = client.post(
        "/api/inventory/adjust",
        headers=headers,
        json={"product_id": pid, "delta": -3, "reason": "Damaged stock"},
    )
    assert adj.status_code == 200
    assert adj.json()["current_stock"] == 47.0

    ledger = client.get(f"/api/inventory/ledger/{pid}", headers=headers).json()
    assert any(e["type"] == "ADJUST" and e["reason"] == "Damaged stock" for e in ledger)


def test_adjustment_requires_reason(client):
    headers, pid = _setup(client)
    resp = client.post("/api/inventory/adjust", headers=headers, json={"product_id": pid, "delta": -1})
    assert resp.status_code == 422


def test_ledger_records_purchase_in(client):
    headers, pid = _setup(client)
    client.post(
        "/api/purchases",
        headers=headers,
        json={
            "supplier_name": "Mills Co",
            "purchase_date": "2026-06-10",
            "items": [{"product_id": pid, "quantity": 10, "purchase_price": 600, "gst_percentage": 5}],
        },
    )
    ledger = client.get(f"/api/inventory/ledger/{pid}", headers=headers).json()
    in_entry = next(e for e in ledger if e["type"] == "IN")
    assert in_entry["quantity"] == 10.0
    assert in_entry["balance_after"] == 60.0


def test_low_stock_list(client):
    headers, pid = _setup(client, current_stock=3, reorder_level=5)
    resp = client.get("/api/inventory/low-stock", headers=headers)
    assert resp.status_code == 200
    assert any(i["product_id"] == pid for i in resp.json())
