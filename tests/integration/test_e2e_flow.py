"""End-to-end critical-flow smoke: register -> product -> purchase -> bill -> reports -> export.

This exercises the full Phase 1 happy path across all modules in one transaction-of-truth.
"""

from datetime import date

from tests.conftest import auth_headers, register


def test_full_business_flow(client):
    # 1) Register a business (Owner + Trial subscription).
    reg = register(client).json()
    headers = auth_headers(reg["access_token"])
    assert reg["tenant"]["subscription_status"] == "Trial"

    # 2) Configure invoice prefix.
    client.put("/api/settings", headers=headers, json={"invoice_prefix": "BN"})

    # 3 + 4) Purchase 100 units of a NEW product (created inline) -> stock 100, selling 105.
    client.post(
        "/api/purchases",
        headers=headers,
        json={"supplier_name": "Mills Co", "purchase_date": "2026-06-10",
              "items": [{"product_code": "TS-001", "product_name": "Cotton Saree", "hsn_code": "5407",
                         "gst_percentage": 5, "purchase_price": 60, "margin_type": "amount",
                         "margin_value": 45, "quantity": 100, "unit": "NOS"}]},
    )
    pid = client.get("/api/products", headers=headers).json()["items"][0]["id"]
    assert client.get(f"/api/products/{pid}", headers=headers).json()["current_stock"] == 100.0

    # 5) Sell 2 units (inclusive GST) -> stock 98, usage 1, invoice BN-YYYY-0001.
    sale = client.post(
        "/api/sales",
        headers=headers,
        json={"items": [{"product_id": pid, "quantity": 2}],
              "payments": [{"mode": "Cash", "amount": 105}, {"mode": "UPI", "amount": 105}]},
    ).json()
    assert sale["invoice_number"] == f"BN-{date.today().year}-0001"
    assert sale["grand_total"] == 210.0
    assert client.get(f"/api/products/{pid}", headers=headers).json()["current_stock"] == 98.0

    # 6) Dashboard reflects the activity.
    dash = client.get("/api/dashboard", headers=headers).json()
    assert dash["today_sales"] == {"amount": 210.0, "count": 1}
    assert dash["bills_this_month"] == 1
    assert dash["subscription"]["used"] == 1

    # 7) Reports compute correctly.
    gst = client.get("/api/reports/gst/summary", headers=headers).json()
    row = next(r for r in gst["rows"] if r["gst_percentage"] == 5.0)
    assert row["taxable"] == 200.0 and row["total_gst"] == 10.0

    stock = client.get("/api/reports/inventory/stock", headers=headers).json()
    assert next(r for r in stock["rows"] if r["product_code"] == "TS-001")["current_stock"] == 98.0

    # 8) Exports return real files.
    xlsx = client.get("/api/reports/gst-summary/export?format=excel", headers=headers)
    assert "spreadsheetml" in xlsx.headers["content-type"] and len(xlsx.content) > 0
    pdf = client.get("/api/reports/stock/export?format=pdf", headers=headers)
    assert pdf.content[:4] == b"%PDF"

    # 9) Reprint the invoice.
    invoice = client.get(f"/api/sales/{sale['id']}/invoice", headers=headers).json()
    assert invoice["sale"]["invoice_number"] == f"BN-{date.today().year}-0001"
