"""CR-6 — thermal/invoice DISPLAY rate rules (pure).

Guarantees the counter-facing identities for both GST modes, using the canonical example:
    selling 200, GST 5%, qty 3  ->  line_total 630, taxable 600, gst 30
"""

from decimal import Decimal as D

from app.services.gst_service import LineInput, compute_bill
from app.services.pricing import customer_unit_rate, net_unit_rate


def _line():
    return compute_bill(
        [LineInput(unit_price=D("200"), quantity=D("3"), gst_percentage=D("5"))],
        gst_mode="exclusive",
    ).lines[0]


def test_canonical_line_values():
    line = _line()
    assert line.taxable_value == D("600.00")
    assert line.gst_amount == D("30.00")
    assert line.line_total == D("630.00")


def test_hidden_mode_rate_is_customer_price():
    line = _line()
    rate = customer_unit_rate(line.line_total, 3)   # 630 / 3
    amount = line.line_total
    assert rate == D("210.00")
    assert amount == D("630.00")
    # Counter identity: qty × displayed rate == displayed amount.
    assert D("3") * rate == amount


def test_visible_mode_rate_is_selling_price():
    line = _line()
    rate = net_unit_rate(line.taxable_value, 3)      # 600 / 3
    amount = line.taxable_value
    assert rate == D("200.00")
    assert amount == D("600.00")
    # Counter identity: (qty × displayed rate) + GST == grand total.
    assert D("3") * rate == amount
    assert amount + line.gst_amount == D("630.00")


def test_zero_quantity_is_safe():
    assert customer_unit_rate(0, 0) == D("0.00")
    assert net_unit_rate(0, 0) == D("0.00")
