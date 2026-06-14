"""CR-5 — Invoice Register: list/filter, detail, reprint, void (stock + reports + usage),
PDF export, customer capture, and tenant isolation."""

from datetime import date

from tests.conftest import auth_headers, register, seed_product


def _owner_with_product(client, qty=50):
    headers = auth_headers(register(client).json()["access_token"])
    p = seed_product(client, headers, code="RIN-1", name="Rin Powder",
                     purchase_price=80, markup_amount=20, gst=5, hsn="3402", qty=qty)
    return headers, p["id"]


def _sell(client, headers, pid, qty=2, **extra):
    # inclusive keeps selling*qty == grand_total for simple payment amounts (100×qty).
    body = {"gst_mode": "inclusive", "items": [{"product_id": pid, "quantity": qty}],
            "payments": [{"mode": "Cash", "amount": 100 * qty}], **extra}
    return client.post("/api/sales", headers=headers, json=body).json()


def test_register_lists_enriched_rows(client):
    headers, pid = _owner_with_product(client)
    _sell(client, headers, pid, qty=1, customer_name="Asha")
    resp = client.get("/api/invoices", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    row = body["items"][0]
    assert row["invoice_number"].startswith("INV-")
    assert row["customer_name"] == "Asha"
    assert row["payment_modes"] == ["Cash"]
    assert row["cashier_name"] == "Ravi"          # the registered owner
    assert row["status"] == "active"
    assert row["grand_total"] == 100.0


def test_filters_invoice_number_payment_status(client):
    headers, pid = _owner_with_product(client)
    _sell(client, headers, pid, qty=1)
    # invoice_number partial match
    assert client.get("/api/invoices?invoice_number=INV-", headers=headers).json()["total"] == 1
    assert client.get("/api/invoices?invoice_number=ZZZ", headers=headers).json()["total"] == 0
    # payment_mode
    assert client.get("/api/invoices?payment_mode=Cash", headers=headers).json()["total"] == 1
    assert client.get("/api/invoices?payment_mode=Card", headers=headers).json()["total"] == 0
    # status
    assert client.get("/api/invoices?status=active", headers=headers).json()["total"] == 1
    assert client.get("/api/invoices?status=void", headers=headers).json()["total"] == 0
    # date range (today)
    today = date.today().isoformat()
    assert client.get(f"/api/invoices?date_from={today}&date_to={today}", headers=headers).json()["total"] == 1
    assert client.get("/api/invoices?date_from=2000-01-01&date_to=2000-01-02", headers=headers).json()["total"] == 0


def test_detail_carries_invoice_type_and_items(client):
    headers, pid = _owner_with_product(client)
    sale = _sell(client, headers, pid, qty=1)
    inv = client.get(f"/api/invoices/{sale['id']}", headers=headers).json()
    assert inv["business"]["invoice_type"] == "thermal_80"   # default
    assert inv["sale"]["status"] == "active"
    assert len(inv["sale"]["items"]) == 1


def test_reprint_is_non_mutating(client):
    headers, pid = _owner_with_product(client)
    sale = _sell(client, headers, pid, qty=1)
    r = client.post(f"/api/invoices/{sale['id']}/reprint", headers=headers)
    assert r.status_code == 200
    assert r.json()["sale"]["invoice_number"] == sale["invoice_number"]
    # still active, still one row
    assert client.get("/api/invoices?status=active", headers=headers).json()["total"] == 1


def test_void_reverses_stock_usage_and_reports(client):
    headers, pid = _owner_with_product(client, qty=50)
    sale = _sell(client, headers, pid, qty=2)          # stock 50 -> 48, usage 1
    assert client.get(f"/api/products/{pid}", headers=headers).json()["current_stock"] == 48.0
    assert client.get("/api/subscription", headers=headers).json()["usage"]["bills_count"] == 1

    void = client.post(f"/api/invoices/{sale['id']}/void", headers=headers)
    assert void.status_code == 200
    assert void.json()["status"] == "void"

    # stock restored, usage reversed
    assert client.get(f"/api/products/{pid}", headers=headers).json()["current_stock"] == 50.0
    assert client.get("/api/subscription", headers=headers).json()["usage"]["bills_count"] == 0
    # excluded from sales reports
    today = date.today().isoformat()
    summary = client.get(f"/api/reports/sales/daily?date={today}", headers=headers).json()["summary"]
    assert summary["bills"] == 0 and summary["gross"] == 0.0
    # dashboard too
    dash = client.get("/api/dashboard", headers=headers).json()
    assert dash["today_sales"] == {"amount": 0.0, "count": 0}


def test_double_void_rejected(client):
    headers, pid = _owner_with_product(client)
    sale = _sell(client, headers, pid, qty=1)
    assert client.post(f"/api/invoices/{sale['id']}/void", headers=headers).status_code == 200
    again = client.post(f"/api/invoices/{sale['id']}/void", headers=headers)
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "APP_ERROR"


def test_pdf_export_returns_pdf(client):
    headers, pid = _owner_with_product(client)
    sale = _sell(client, headers, pid, qty=1)
    resp = client.get(f"/api/invoices/{sale['id']}/pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert sale["invoice_number"] in resp.headers["content-disposition"]


def test_tenant_isolation(client):
    headers_a, pid = _owner_with_product(client)
    sale = _sell(client, headers_a, pid, qty=1)
    headers_b = auth_headers(register(client, email="other@shop.in").json()["access_token"])
    # Tenant B cannot see, reprint, void, or export Tenant A's invoice.
    assert client.get(f"/api/invoices/{sale['id']}", headers=headers_b).status_code == 404
    assert client.post(f"/api/invoices/{sale['id']}/void", headers=headers_b).status_code == 404
    assert client.get(f"/api/invoices/{sale['id']}/pdf", headers=headers_b).status_code == 404
    assert client.get("/api/invoices", headers=headers_b).json()["total"] == 0
