"""CR-4 — POS pricing mirrors the Purchase Pricing Preview (exclusive by default).

End-to-end proof that a real sale, with no per-sale override, adds GST ON TOP of the
selling price (selling 100 + 5% -> 105) and that the persisted invoice keeps GST inside
the grand total even when the customer slip hides the tax breakup.

Seed: purchase 80 + markup 20 -> selling 100, GST 5%.
"""

from tests.conftest import auth_headers, register, seed_product


def _owner_with_product(client, qty=50):
    headers = auth_headers(register(client).json()["access_token"])
    p = seed_product(client, headers, code="RIN-1", name="Rin Powder",
                     purchase_price=80, markup_amount=20, gst=5, hsn="3402", qty=qty)
    return headers, p["id"]


def test_default_mode_is_exclusive_qty1(client):
    """No gst_mode in the request -> tenant default (exclusive) -> grand 105, not 100."""
    headers, pid = _owner_with_product(client)
    prev = client.post(
        "/api/sales/preview", headers=headers,
        json={"items": [{"product_id": pid, "quantity": 1}]},
    ).json()
    assert prev["gst_mode"] == "exclusive"
    assert prev["totals"]["total_taxable"] == 100.0
    assert prev["totals"]["total_gst"] == 5.0
    assert prev["totals"]["grand_total"] == 105.0
    line = prev["items"][0]
    assert line["unit_price"] == 100.0 and line["line_total"] == 105.0


def test_default_mode_exclusive_qty3(client):
    headers, pid = _owner_with_product(client)
    prev = client.post(
        "/api/sales/preview", headers=headers,
        json={"items": [{"product_id": pid, "quantity": 3}]},
    ).json()
    assert prev["totals"]["total_taxable"] == 300.0
    assert prev["totals"]["total_gst"] == 15.0
    assert prev["totals"]["grand_total"] == 315.0


def test_preview_and_saved_sale_are_identical(client):
    """The number shown in preview is exactly what gets persisted (single engine)."""
    headers, pid = _owner_with_product(client)
    body = {"items": [{"product_id": pid, "quantity": 3}]}
    prev = client.post("/api/sales/preview", headers=headers, json=body).json()
    grand = prev["totals"]["grand_total"]
    sale = client.post(
        "/api/sales", headers=headers,
        json={**body, "payments": [{"mode": "Cash", "amount": grand}]},
    ).json()
    assert sale["grand_total"] == grand == 315.0
    assert sale["total_taxable"] == prev["totals"]["total_taxable"] == 300.0
    assert sale["total_gst"] == prev["totals"]["total_gst"] == 15.0
    assert sale["gst_mode"] == "exclusive"
    assert sale["items"][0]["line_total"] == prev["items"][0]["line_total"] == 315.0


def test_inclusive_override_carves_gst_out(client):
    headers, pid = _owner_with_product(client)
    prev = client.post(
        "/api/sales/preview", headers=headers,
        json={"gst_mode": "inclusive", "items": [{"product_id": pid, "quantity": 1}]},
    ).json()
    assert prev["gst_mode"] == "inclusive"
    assert prev["totals"]["total_taxable"] == 95.24
    assert prev["totals"]["total_gst"] == 4.76
    assert prev["totals"]["grand_total"] == 100.0


def test_hide_gst_invoice_keeps_gst_in_grand_total(client):
    """show_gst_on_invoice=False hides the tax breakup on the slip, but the grand total
    still INCLUDES GST (105, never reduced to 100)."""
    headers, pid = _owner_with_product(client)
    sale = client.post(
        "/api/sales", headers=headers,
        json={"items": [{"product_id": pid, "quantity": 1}],
              "payments": [{"mode": "Cash", "amount": 105}]},
    ).json()
    inv = client.get(f"/api/sales/{sale['id']}/invoice", headers=headers).json()
    assert inv["sale"]["show_gst_on_invoice"] is False       # CR-7: per-bill, default Hide
    assert inv["sale"]["grand_total"] == 105.0               # GST still inside the total
    assert inv["sale"]["total_gst"] == 5.0                   # recorded internally
    assert inv["sale"]["items"][0]["line_total"] == 105.0


def test_payment_must_equal_exclusive_grand_total(client):
    """Paying the bare selling price (100) under the exclusive default is rejected —
    this is exactly the bug that previously slipped through as a balanced bill."""
    headers, pid = _owner_with_product(client)
    resp = client.post(
        "/api/sales", headers=headers,
        json={"items": [{"product_id": pid, "quantity": 1}],
              "payments": [{"mode": "Cash", "amount": 100}]},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "PAYMENT_MISMATCH"
