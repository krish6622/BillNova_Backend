"""CR-3 integration: purchase-side totals (supplier payable), next-code endpoint,
GST dropdown values, duplicate-code prevention, and the invoice unit (NOS) snapshot."""

from tests.conftest import auth_headers, register, seed_product


def _owner(client):
    return auth_headers(register(client).json()["access_token"])


def _purchase_one(client, h, **over):
    # CR-3 worked example: purchase 250, markup 252, GST 10%, qty 1.
    item = {"product_name": "CR3 Item", "gst_percentage": 10, "purchase_price": 250,
            "markup_amount": 252, "quantity": 1, "unit": "NOS"}
    item.update(over)
    return client.post(
        "/api/purchases", headers=h,
        json={"supplier_name": "Sup", "purchase_date": "2026-06-13", "items": [item]},
    )


def test_purchase_totals_are_supplier_side(client):
    body = _purchase_one(client, _owner(client)).json()
    # Purchase Total 250 + Purchase GST 25 = Supplier Payable 275 (purchase price only).
    assert body["total_gst"] == 25.0
    assert body["total_amount"] == 275.0


def test_purchase_totals_multi_qty(client):
    body = _purchase_one(client, _owner(client), quantity=2).json()
    assert body["total_gst"] == 50.0       # 500 × 10%
    assert body["total_amount"] == 550.0   # 500 + 50


def test_created_product_selling_is_purchase_plus_markup(client):
    h = _owner(client)
    _purchase_one(client, h)
    p = next(p for p in client.get("/api/products", headers=h).json()["items"] if p["name"] == "CR3 Item")
    assert p["purchase_price"] == 250.0
    assert p["markup_amount"] == 252.0
    assert p["selling_price"] == 502.0     # purchase + markup (NOT affected by purchase GST)


def test_next_code_endpoint_increments(client):
    h = _owner(client)
    assert client.get("/api/products/next-code", headers=h).json()["product_code"] == "PD-00001"
    seed_product(client, h, name="X")      # auto-creates PD-00001
    assert client.get("/api/products/next-code", headers=h).json()["product_code"] == "PD-00002"


def test_gst_dropdown_values_accepted(client):
    h = _owner(client)
    for rate in (0, 5, 12, 18, 28):
        assert _purchase_one(client, h, product_name=f"G{rate}", gst_percentage=rate).status_code == 201


def test_invalid_gst_rejected(client):
    assert _purchase_one(client, _owner(client), gst_percentage=101).status_code == 422


def test_duplicate_code_rejected(client):
    h = _owner(client)
    assert _purchase_one(client, h, product_code="DUP", product_name="A").status_code == 201
    dup = _purchase_one(client, h, product_code="DUP", product_name="B")
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"


def test_invoice_snapshots_unit_nos(client):
    h = _owner(client)
    p = seed_product(client, h, code="U-1", name="UnitProd", qty=10)   # default unit NOS
    sale = client.post(
        "/api/sales", headers=h,
        json={"gst_mode": "inclusive", "items": [{"product_id": p["id"], "quantity": 1}],
              "payments": [{"mode": "Cash", "amount": p["selling_price"]}]},
    ).json()
    inv = client.get(f"/api/sales/{sale['id']}/invoice", headers=h).json()
    assert inv["sale"]["items"][0]["unit"] == "NOS"
