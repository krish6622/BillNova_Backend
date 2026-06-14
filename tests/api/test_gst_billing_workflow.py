"""GST billing workflow — per-bill billing type, GST-customer details, registers.

Covers: GST-customer validation + invalid GSTIN rejection, WITH_GST vs WITHOUT_GST
billing math, GST show/hide, GST-report exclusion of non-GST sales, the new sales
registers, invoice-register filters, and the auditor export package.

A seeded product priced at exactly ₹100 (purchase 95 + markup 5, GST 5%) makes the
arithmetic obvious: WITH_GST exclusive -> ₹105 (CGST 2.50 + SGST 2.50); WITHOUT_GST -> ₹100.
"""

import io
import zipfile

import pytest

from tests.conftest import auth_headers, register, seed_product

GOOD_GSTIN = "33ABCDE1234F1Z5"
BAD_GSTIN = "33ABCDE1234F1Z"  # 14 chars — fails the format


@pytest.fixture
def owner(client):
    return register(client).json()["access_token"]


@pytest.fixture
def product(client, owner):
    # selling price = 95 + 5 = 100, GST 5%
    return seed_product(client, auth_headers(owner), code="P100", purchase_price=95,
                        markup_amount=5, gst=5, qty=100)


def _bill(client, headers, product_id, *, billing_type, qty=1, extra=None):
    """Preview (to learn the grand total), then create a matching sale. Returns the sale JSON."""
    items = [{"product_id": product_id, "quantity": qty}]
    body = {"items": items, "billing_type": billing_type}
    preview = client.post("/api/sales/preview", headers=headers, json=body)
    assert preview.status_code == 200, preview.text
    total = preview.json()["totals"]["grand_total"]
    payload = {**body, "payments": [{"mode": "Cash", "amount": total}], **(extra or {})}
    sale = client.post("/api/sales", headers=headers, json=payload)
    assert sale.status_code == 201, sale.text
    return sale.json()


# ---- Billing math: WITH_GST vs WITHOUT_GST --------------------------------

def test_with_gst_charges_tax(client, owner, product):
    sale = _bill(client, auth_headers(owner), product["id"], billing_type="WITH_GST")
    assert sale["billing_type"] == "WITH_GST"
    assert sale["grand_total"] == 105.0
    assert sale["total_taxable"] == 100.0
    assert sale["total_gst"] == 5.0
    assert sale["total_cgst"] == 2.5 and sale["total_sgst"] == 2.5


def test_without_gst_is_zero_tax(client, owner, product):
    sale = _bill(client, auth_headers(owner), product["id"], billing_type="WITHOUT_GST")
    assert sale["billing_type"] == "WITHOUT_GST"
    assert sale["grand_total"] == 100.0      # plain selling price, no tax added
    assert sale["total_taxable"] == 100.0
    assert sale["total_gst"] == 0.0
    assert sale["total_cgst"] == 0.0 and sale["total_sgst"] == 0.0
    assert sale["items"][0]["gst_percentage"] == 0.0  # rate hidden on the line


def test_billing_type_defaults_to_with_gst_when_omitted(client, owner, product):
    """Back-compat: a client that never sends billing_type still gets a GST sale."""
    items = [{"product_id": product["id"], "quantity": 1}]
    preview = client.post("/api/sales/preview", headers=auth_headers(owner), json={"items": items})
    assert preview.json()["billing_type"] == "WITH_GST"
    assert preview.json()["totals"]["grand_total"] == 105.0


# ---- GST customer validation ----------------------------------------------

def test_gst_customer_is_saved(client, owner, product):
    sale = _bill(
        client, auth_headers(owner), product["id"], billing_type="WITH_GST",
        extra={"is_gst_customer": True, "customer_name": "ABC Traders",
               "customer_mobile": "9876543210", "customer_gstin": GOOD_GSTIN},
    )
    assert sale["is_gst_customer"] is True
    assert sale["customer_gstin"] == GOOD_GSTIN
    assert sale["customer_name"] == "ABC Traders"


def test_invalid_gstin_is_rejected(client, owner, product):
    items = [{"product_id": product["id"], "quantity": 1}]
    resp = client.post(
        "/api/sales", headers=auth_headers(owner),
        json={"items": items, "billing_type": "WITH_GST",
              "payments": [{"mode": "Cash", "amount": 105.0}],
              "is_gst_customer": True, "customer_name": "ABC", "customer_gstin": BAD_GSTIN},
    )
    assert resp.status_code == 422


def test_gst_customer_requires_gstin(client, owner, product):
    items = [{"product_id": product["id"], "quantity": 1}]
    resp = client.post(
        "/api/sales", headers=auth_headers(owner),
        json={"items": items, "billing_type": "WITH_GST",
              "payments": [{"mode": "Cash", "amount": 105.0}],
              "is_gst_customer": True, "customer_name": "ABC"},  # no GSTIN
    )
    assert resp.status_code == 422


def test_regular_customer_never_carries_gstin(client, owner, product):
    sale = _bill(
        client, auth_headers(owner), product["id"], billing_type="WITH_GST",
        extra={"is_gst_customer": False, "customer_gstin": GOOD_GSTIN},
    )
    assert sale["is_gst_customer"] is False
    assert sale["customer_gstin"] is None


# ---- GST show / hide on the invoice ---------------------------------------

def test_with_gst_can_show_breakdown(client, owner, product):
    sale = _bill(client, auth_headers(owner), product["id"], billing_type="WITH_GST",
                 extra={"show_gst_on_invoice": True})
    assert sale["show_gst_on_invoice"] is True


def test_without_gst_forces_hidden_breakdown(client, owner, product):
    # Even if the client asks to show GST, a non-GST sale has none to show.
    sale = _bill(client, auth_headers(owner), product["id"], billing_type="WITHOUT_GST",
                 extra={"show_gst_on_invoice": True})
    assert sale["show_gst_on_invoice"] is False


# ---- Reports: GST exclusion / non-GST inclusion ---------------------------

def test_gst_reports_exclude_non_gst_sales(client, owner, product):
    h = auth_headers(owner)
    _bill(client, h, product["id"], billing_type="WITH_GST")
    _bill(client, h, product["id"], billing_type="WITHOUT_GST")

    gst = client.get("/api/reports/gst/summary", headers=h).json()
    total_gst = sum(r["total_gst"] for r in gst["rows"])
    assert total_gst == 5.0  # only the WITH_GST bill contributes

    gst_reg = client.get("/api/reports/gst/sales-register", headers=h).json()
    assert len(gst_reg["rows"]) == 1 and gst_reg["totals"]["total"] == 105.0

    non_gst = client.get("/api/reports/non-gst/sales-register", headers=h).json()
    assert len(non_gst["rows"]) == 1 and non_gst["totals"]["total"] == 100.0


def test_gst_customer_register(client, owner, product):
    h = auth_headers(owner)
    _bill(client, h, product["id"], billing_type="WITH_GST",
          extra={"is_gst_customer": True, "customer_name": "ABC Traders", "customer_gstin": GOOD_GSTIN})
    _bill(client, h, product["id"], billing_type="WITHOUT_GST")  # not a GST customer

    reg = client.get("/api/reports/gst/customer-register", headers=h).json()
    assert len(reg["rows"]) == 1
    assert reg["rows"][0]["gstin"] == GOOD_GSTIN
    assert reg["totals"]["customers"] == 1


# ---- Invoice register filters + columns -----------------------------------

def test_invoice_register_filters_by_billing_type(client, owner, product):
    h = auth_headers(owner)
    _bill(client, h, product["id"], billing_type="WITH_GST")
    _bill(client, h, product["id"], billing_type="WITHOUT_GST")

    all_rows = client.get("/api/invoices", headers=h).json()["items"]
    assert {r["billing_type"] for r in all_rows} == {"WITH_GST", "WITHOUT_GST"}
    assert "is_gst_customer" in all_rows[0] and "customer_gstin" in all_rows[0]

    only_non_gst = client.get("/api/invoices?billing_type=WITHOUT_GST", headers=h).json()["items"]
    assert len(only_non_gst) == 1 and only_non_gst[0]["billing_type"] == "WITHOUT_GST"


# ---- Auditor export package -----------------------------------------------

def test_auditor_export_separates_gst_and_non_gst(client, owner, product):
    h = auth_headers(owner)
    _bill(client, h, product["id"], billing_type="WITH_GST",
          extra={"is_gst_customer": True, "customer_name": "ABC Traders", "customer_gstin": GOOD_GSTIN})
    _bill(client, h, product["id"], billing_type="WITHOUT_GST")

    resp = client.get("/api/reports/auditor/export", headers=h)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "GST/GST-Sales-Register.xlsx" in names
    assert "GST/HSN-Summary.xlsx" in names
    assert "GST/GST-Customer-Register.xlsx" in names
    assert "GST/GSTR-Data.xlsx" in names
    assert "Non-GST/Non-GST-Sales-Register.xlsx" in names
    assert "Combined-Summary.xlsx" in names


def test_auditor_export_is_owner_only(client, owner, product):
    """Cashier must not reach the auditor export (Owner-only reports router)."""
    cashier_login = client.post(
        "/api/users", headers=auth_headers(owner),
        json={"name": "Cash", "email": "c@shop.in", "password": "cashier12", "role": "CASHIER"},
    )
    assert cashier_login.status_code == 201
    tok = client.post("/api/auth/login", json={"email": "c@shop.in", "password": "cashier12"}).json()["access_token"]
    assert client.get("/api/reports/auditor/export", headers=auth_headers(tok)).status_code == 403
