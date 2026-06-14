"""CR-6 — invoice payload carries cashier name + branding flag; A4 PDF still renders."""

from tests.conftest import auth_headers, register, seed_product


def _owner_with_sale(client):
    headers = auth_headers(register(client).json()["access_token"])  # owner "Ravi"
    p = seed_product(client, headers, code="MK-1", name="Milk",
                     purchase_price=160, markup_amount=40, gst=5, hsn="0401", qty=50)
    # selling 200; exclusive default qty3 -> grand 630
    prev = client.post("/api/sales/preview", headers=headers,
                       json={"items": [{"product_id": p["id"], "quantity": 3}]}).json()
    grand = prev["totals"]["grand_total"]
    sale = client.post("/api/sales", headers=headers,
                       json={"items": [{"product_id": p["id"], "quantity": 3}],
                             "payments": [{"mode": "Cash", "amount": grand}]}).json()
    return headers, sale, grand


def test_invoice_payload_has_cashier_and_branding(client):
    headers, sale, grand = _owner_with_sale(client)
    assert grand == 630.0
    inv = client.get(f"/api/invoices/{sale['id']}", headers=headers).json()
    assert inv["sale"]["cashier_name"] == "Ravi"
    assert inv["business"]["show_branding"] is True       # default on
    # The line carries the raw figures the renderer turns into rate/amount.
    item = inv["sale"]["items"][0]
    assert item["taxable_value"] == 600.0 and item["line_total"] == 630.0


def test_sales_invoice_endpoint_also_has_cashier(client):
    headers, sale, _ = _owner_with_sale(client)
    inv = client.get(f"/api/sales/{sale['id']}/invoice", headers=headers).json()
    assert inv["sale"]["cashier_name"] == "Ravi"


def test_settings_branding_default_and_toggle(client):
    headers, _, _ = _owner_with_sale(client)
    assert client.get("/api/settings", headers=headers).json()["show_branding"] is True
    upd = client.put("/api/settings", headers=headers, json={"show_branding": False})
    assert upd.status_code == 200 and upd.json()["show_branding"] is False


def test_pdf_still_renders_after_redesign(client):
    headers, sale, _ = _owner_with_sale(client)
    resp = client.get(f"/api/invoices/{sale['id']}/pdf", headers=headers)
    assert resp.status_code == 200 and resp.content[:4] == b"%PDF"
