"""CR-7 — purchase supplier-invoice header (invoice_number, notes) and mixed
existing/new product lines under one supplier bill."""

from tests.conftest import auth_headers, register


def _owner(client):
    return auth_headers(register(client).json()["access_token"])


def test_purchase_header_fields_persist(client):
    headers = _owner(client)
    body = {
        "supplier_name": "King Krish", "invoice_number": "KK-9981", "notes": "Monthly stock",
        "purchase_date": "2026-06-13",
        "items": [{"product_name": "Milk", "gst_percentage": 5, "purchase_price": 160,
                   "markup_amount": 40, "quantity": 10, "unit": "NOS"}],
    }
    created = client.post("/api/purchases", headers=headers, json=body)
    assert created.status_code == 201, created.text
    out = created.json()
    assert out["invoice_number"] == "KK-9981"
    assert out["notes"] == "Monthly stock"
    # appears on the list too
    row = client.get("/api/purchases", headers=headers).json()["items"][0]
    assert row["invoice_number"] == "KK-9981"


def test_mixed_existing_and_new_items_in_one_invoice(client):
    headers = _owner(client)
    # First, create a product via an initial purchase.
    client.post("/api/purchases", headers=headers, json={
        "supplier_name": "S1", "purchase_date": "2026-06-13",
        "items": [{"product_code": "RICE-1", "product_name": "Rice", "gst_percentage": 5,
                   "purchase_price": 100, "markup_amount": 20, "quantity": 5, "unit": "NOS"}],
    })
    rice = next(p for p in client.get("/api/products", headers=headers).json()["items"] if p["name"] == "Rice")

    # Now one supplier invoice mixing an EXISTING line (Rice) and two NEW lines (Soap, Oil).
    body = {
        "supplier_name": "King Krish", "invoice_number": "KK-1002", "purchase_date": "2026-06-13",
        "items": [
            {"product_id": rice["id"], "gst_percentage": 5, "purchase_price": 105,
             "markup_amount": 20, "quantity": 8, "unit": "NOS"},
            {"product_name": "Soap", "gst_percentage": 18, "purchase_price": 30,
             "markup_amount": 10, "quantity": 12, "unit": "NOS"},
            {"product_name": "Oil", "gst_percentage": 5, "purchase_price": 120,
             "markup_amount": 30, "quantity": 6, "unit": "NOS"},
        ],
    }
    created = client.post("/api/purchases", headers=headers, json=body)
    assert created.status_code == 201, created.text
    assert len(created.json()["items"]) == 3
    # Rice restocked (5 + 8 = 13); Soap & Oil created.
    products = {p["name"]: p for p in client.get("/api/products", headers=headers).json()["items"]}
    assert products["Rice"]["current_stock"] == 13.0
    assert products["Soap"]["current_stock"] == 12.0
    assert products["Oil"]["current_stock"] == 6.0
