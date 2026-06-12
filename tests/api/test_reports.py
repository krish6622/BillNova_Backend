"""Reports + export tests."""

from datetime import date

from tests.conftest import auth_headers, register

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


def _setup_with_sale(client):
    headers = auth_headers(register(client).json()["access_token"])
    pid = client.post("/api/products", headers=headers, json=PRODUCT).json()["id"]
    client.post(
        "/api/sales",
        headers=headers,
        json={"items": [{"product_id": pid, "quantity": 2}], "payments": [{"mode": "Cash", "amount": 210}]},
    )
    return headers


def test_daily_sales_report(client):
    headers = _setup_with_sale(client)
    today = date.today().isoformat()
    resp = client.get(f"/api/reports/sales/daily?date={today}", headers=headers)
    assert resp.status_code == 200
    s = resp.json()["summary"]
    assert s["bills"] == 1
    assert s["gross"] == 210.0
    assert s["taxable"] == 200.0
    assert s["gst"] == 10.0


def test_monthly_sales_report(client):
    headers = _setup_with_sale(client)
    today = date.today()
    resp = client.get(f"/api/reports/sales/monthly?year={today.year}&month={today.month}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["bills"] == 1
    assert len(body["days"]) == 1


def test_gst_summary_report(client):
    headers = _setup_with_sale(client)
    resp = client.get("/api/reports/gst/summary", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    row = next(r for r in rows if r["gst_percentage"] == 5.0)
    assert row["taxable"] == 200.0
    assert row["cgst"] == 5.0
    assert row["sgst"] == 5.0
    assert row["total_gst"] == 10.0


def test_hsn_summary_report(client):
    headers = _setup_with_sale(client)
    resp = client.get("/api/reports/gst/hsn", headers=headers)
    assert resp.status_code == 200
    row = next(r for r in resp.json()["rows"] if r["hsn_code"] == "5407")
    assert row["quantity"] == 2.0
    assert row["taxable"] == 200.0
    assert row["gst"] == 10.0


def test_stock_report(client):
    headers = _setup_with_sale(client)
    resp = client.get("/api/reports/inventory/stock", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    item = body["rows"][0]
    assert item["current_stock"] == 48.0  # 50 - 2 sold
    assert body["total_value"] == 48.0 * 600


def test_export_excel(client):
    headers = _setup_with_sale(client)
    resp = client.get("/api/reports/gst-summary/export?format=excel", headers=headers)
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
    assert resp.headers["content-disposition"].endswith('.xlsx"')
    assert len(resp.content) > 0


def test_export_pdf(client):
    headers = _setup_with_sale(client)
    resp = client.get("/api/reports/stock/export?format=pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_reports_owner_only(client):
    headers = auth_headers(register(client).json()["access_token"])
    client.post(
        "/api/users", headers=headers,
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    cashier = client.post(
        "/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"}
    ).json()["access_token"]
    assert client.get("/api/reports/inventory/stock", headers=auth_headers(cashier)).status_code == 403
