"""CR-2 / CR-7: the invoice GST-display flag is chosen PER BILL and frozen on the sale,
full tax is always persisted regardless, and GST/HSN reports are independent of the flag."""

from tests.conftest import auth_headers, register, seed_product


def _owner_and_product(client):
    headers = auth_headers(register(client).json()["access_token"])
    p = seed_product(client, headers, code="TS-001", name="Cotton Saree",
                     purchase_price=60, markup_amount=45, gst=5, hsn="5407", qty=50)
    return headers, p["id"]


def _sell(client, headers, pid, *, show_gst):
    # inclusive keeps selling*qty == grand_total: selling 105, qty 2 -> 210.
    return client.post(
        "/api/sales", headers=headers,
        json={"gst_mode": "inclusive", "show_gst_on_invoice": show_gst,
              "items": [{"product_id": pid, "quantity": 2}],
              "payments": [{"mode": "Cash", "amount": 210}]},
    ).json()


def test_invoice_default_hides_gst_but_persists_tax(client):
    headers, pid = _owner_and_product(client)
    sale = _sell(client, headers, pid, show_gst=False)
    inv = client.get(f"/api/sales/{sale['id']}/invoice", headers=headers).json()
    assert inv["sale"]["show_gst_on_invoice"] is False        # CR-7: per bill, default Hide
    # Tax is ALWAYS computed and stored, regardless of the display flag.
    assert inv["sale"]["total_taxable"] == 200.0
    assert inv["sale"]["total_gst"] == 10.0
    assert inv["sale"]["total_cgst"] == 5.0
    assert inv["sale"]["total_sgst"] == 5.0


def test_invoice_reflects_per_bill_show_flag(client):
    headers, pid = _owner_and_product(client)
    sale = _sell(client, headers, pid, show_gst=True)
    inv = client.get(f"/api/sales/{sale['id']}/invoice", headers=headers).json()
    assert inv["sale"]["show_gst_on_invoice"] is True
    assert inv["sale"]["total_gst"] == 10.0  # internals unchanged


def test_two_bills_can_differ_in_gst_display(client):
    headers, pid = _owner_and_product(client)
    hidden = _sell(client, headers, pid, show_gst=False)
    shown = _sell(client, headers, pid, show_gst=True)
    reg = client.get("/api/invoices", headers=headers).json()["items"]
    by_no = {r["invoice_number"]: r for r in reg}
    assert by_no[hidden["invoice_number"]]["show_gst_on_invoice"] is False
    assert by_no[shown["invoice_number"]]["show_gst_on_invoice"] is True


def test_reports_identical_regardless_of_invoice_flag(client):
    headers, pid = _owner_and_product(client)
    _sell(client, headers, pid, show_gst=False)
    _sell(client, headers, pid, show_gst=True)
    gst = client.get("/api/reports/gst/summary", headers=headers).json()
    row = next(r for r in gst["rows"] if r["gst_percentage"] == 5.0)
    # Both bills carry full tax in statutory reports irrespective of their display flag.
    assert row["total_gst"] == 20.0
    assert row["cgst"] == 10.0 and row["sgst"] == 10.0
