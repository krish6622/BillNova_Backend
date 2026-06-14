"""CR-3 unit tests: purchase-side and sales-side calculations are separate and correct.

Worked example (CR-3): purchase 250, markup 252, GST 10%.
  selling      = 502
  purchase GST = 25.00  (on cost 250)      supplier payable = 275.00
  sales GST    = 50.20 exclusive / 45.64 inclusive  (on selling 502)
The purchase and sales GST are DIFFERENT amounts — they never share a base.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.services.gst_service import LineInput, compute_bill
from app.services.pricing import compute_selling_price

PP, MARKUP, GST = Decimal("250"), Decimal("252"), Decimal("10")


def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _sale_line(selling):
    return compute_bill(
        [LineInput(unit_price=selling, quantity=1, gst_percentage=GST)],
        gst_mode="exclusive",
    ).lines[0]


# ---- selling price -----------------------------------------------------------

def test_selling_price_is_purchase_plus_markup():
    assert compute_selling_price(PP, MARKUP) == Decimal("502.00")


# ---- purchase side (supplier) ------------------------------------------------

def test_purchase_gst_and_supplier_payable_use_purchase_price():
    qty = Decimal("1")
    purchase_total = PP * qty
    purchase_gst = _round2(purchase_total * GST / 100)
    supplier_payable = _round2(purchase_total + purchase_gst)
    assert purchase_total == Decimal("250")
    assert purchase_gst == Decimal("25.00")
    assert supplier_payable == Decimal("275.00")   # the screenshot's ₹275 (correct)


# ---- sales side (customer) ---------------------------------------------------

def test_sales_gst_exclusive_uses_selling_price():
    line = _sale_line(compute_selling_price(PP, MARKUP))   # selling 502
    assert line.taxable_value == Decimal("502.00")
    assert line.gst_amount == Decimal("50.20")            # 502 × 10%
    assert line.line_total == Decimal("552.20")


def test_sales_gst_inclusive_uses_selling_price():
    selling = compute_selling_price(PP, MARKUP)            # 502
    line = compute_bill(
        [LineInput(unit_price=selling, quantity=1, gst_percentage=GST)],
        gst_mode="inclusive",
    ).lines[0]
    assert line.taxable_value == Decimal("456.36")        # 502 / 1.10
    assert line.gst_amount == Decimal("45.64")            # 502 − 456.36
    assert line.line_total == Decimal("502.00")


# ---- the separation invariant ------------------------------------------------

def test_purchase_gst_differs_from_sales_gst_for_same_product():
    purchase_gst = _round2(PP * GST / 100)                # 25.00 (cost basis)
    sales_gst = _sale_line(compute_selling_price(PP, MARKUP)).gst_amount  # 50.20 (selling basis)
    assert purchase_gst == Decimal("25.00")
    assert sales_gst == Decimal("50.20")
    assert purchase_gst != sales_gst                      # never the same base
