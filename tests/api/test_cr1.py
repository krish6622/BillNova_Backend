"""CR-1 API tests: purchase-creates-product, auto code, profit pricing, duplicate
code rejection, existing-product restock, inventory sync. (CR-2: profit-amount pricing.)"""

from tests.conftest import auth_headers, register


def _owner(client):
    return auth_headers(register(client).json()["access_token"])


def _purchase(client, h, **item):
    base = {"gst_percentage": 5, "purchase_price": 100, "markup_amount": 0,
            "quantity": 10, "unit": "NOS"}
    return client.post("/api/purchases", headers=h, json={
        "supplier_name": "S", "purchase_date": "2026-06-10", "items": [{**base, **item}],
    })


def test_auto_product_code_sequence(client):
    h = _owner(client)
    _purchase(client, h, product_name="Item A")
    _purchase(client, h, product_name="Item B")
    codes = {p["product_code"] for p in client.get("/api/products", headers=h).json()["items"]}
    assert "PD-00001" in codes and "PD-00002" in codes


def test_zero_profit_selling_equals_purchase(client):
    h = _owner(client)
    _purchase(client, h, product_name="Zero", purchase_price=100, markup_amount=0)
    p = next(p for p in client.get("/api/products", headers=h).json()["items"] if p["name"] == "Zero")
    assert p["selling_price"] == 100.0


def test_markup_amount_via_purchase(client):
    h = _owner(client)
    _purchase(client, h, product_name="Amt", purchase_price=100, markup_amount=20)
    p = next(p for p in client.get("/api/products", headers=h).json()["items"] if p["name"] == "Amt")
    assert p["selling_price"] == 120.0  # 100 + 20


def test_duplicate_code_rejected(client):
    h = _owner(client)
    assert _purchase(client, h, product_code="DUP", product_name="One").status_code == 201
    dup = _purchase(client, h, product_code="DUP", product_name="Two")
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"


def test_existing_product_restock_updates_stock_and_pricing(client):
    h = _owner(client)
    _purchase(client, h, product_code="EX-1", product_name="Existing", purchase_price=100,
              markup_amount=20, quantity=10)
    p = next(p for p in client.get("/api/products", headers=h).json()["items"] if p["product_code"] == "EX-1")
    assert p["current_stock"] == 10.0 and p["selling_price"] == 120.0

    # restock the same product with a new cost/profit
    client.post("/api/purchases", headers=h, json={
        "supplier_name": "S", "purchase_date": "2026-06-11",
        "items": [{"product_id": p["id"], "purchase_price": 110, "markup_amount": 55,
                   "gst_percentage": 5, "quantity": 5, "unit": "NOS"}],
    })
    p2 = client.get(f"/api/products/{p['id']}", headers=h).json()
    assert p2["current_stock"] == 15.0           # 10 + 5
    assert p2["purchase_price"] == 110.0
    assert p2["selling_price"] == 165.0          # 110 + 55


def test_new_product_requires_name(client):
    h = _owner(client)
    resp = _purchase(client, h)  # no product_id, no product_name
    assert resp.status_code == 422
