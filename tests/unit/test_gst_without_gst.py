"""Unit tests for the WITHOUT_GST path of the pure GST engine (compute_bill)."""

from decimal import Decimal

from app.services.gst_service import LineInput, compute_bill


def _line(price, qty=1, rate=5, disc=0):
    return LineInput(
        unit_price=Decimal(str(price)), quantity=Decimal(str(qty)),
        gst_percentage=Decimal(str(rate)), discount=Decimal(str(disc)),
    )


def test_charge_gst_false_zeros_all_tax():
    comp = compute_bill([_line(100, rate=5)], gst_mode="exclusive", charge_gst=False)
    line = comp.lines[0]
    assert line.taxable_value == Decimal("100.00")
    assert line.gst_amount == Decimal("0.00")
    assert line.cgst == Decimal("0.00") and line.sgst == Decimal("0.00")
    assert line.line_total == Decimal("100.00")
    assert comp.total_gst == Decimal("0.00")
    assert comp.grand_total == Decimal("100.00")


def test_charge_gst_true_is_unchanged():
    comp = compute_bill([_line(100, rate=5)], gst_mode="exclusive", charge_gst=True)
    assert comp.total_gst == Decimal("5.00")
    assert comp.grand_total == Decimal("105.00")


def test_without_gst_ignores_mode():
    """With GST off, inclusive vs exclusive make no difference — both charge the base."""
    inc = compute_bill([_line(105, rate=5)], gst_mode="inclusive", charge_gst=False)
    exc = compute_bill([_line(105, rate=5)], gst_mode="exclusive", charge_gst=False)
    assert inc.grand_total == exc.grand_total == Decimal("105.00")
    assert inc.total_gst == exc.total_gst == Decimal("0.00")


def test_without_gst_still_applies_discounts():
    comp = compute_bill([_line(100, qty=2, rate=5, disc=20)], gst_mode="exclusive", charge_gst=False)
    # base = 200 - 20 = 180, no tax
    assert comp.total_discount == Decimal("20.00")
    assert comp.grand_total == Decimal("180.00")
    assert comp.total_gst == Decimal("0.00")
