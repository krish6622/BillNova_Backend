"""Unit tests for the pure GST engine."""

from decimal import Decimal

from app.services.gst_service import LineInput, compute_bill


def D(x):
    return Decimal(str(x))


def test_inclusive_single_line_intra():
    comp = compute_bill(
        [LineInput(unit_price=105, quantity=1, gst_percentage=5)],
        gst_mode="inclusive",
        place_of_supply="intra",
    )
    line = comp.lines[0]
    assert line.taxable_value == D("100.00")
    assert line.gst_amount == D("5.00")
    assert line.cgst == D("2.50")
    assert line.sgst == D("2.50")
    assert line.igst == D("0.00")
    assert line.line_total == D("105.00")
    assert comp.grand_total == D("105.00")


def test_exclusive_single_line():
    comp = compute_bill(
        [LineInput(unit_price=100, quantity=1, gst_percentage=5)],
        gst_mode="exclusive",
        place_of_supply="intra",
    )
    line = comp.lines[0]
    assert line.taxable_value == D("100.00")
    assert line.gst_amount == D("5.00")
    assert line.line_total == D("105.00")


def test_inter_state_uses_igst():
    comp = compute_bill(
        [LineInput(unit_price=100, quantity=1, gst_percentage=18)],
        gst_mode="exclusive",
        place_of_supply="inter",
    )
    line = comp.lines[0]
    assert line.igst == D("18.00")
    assert line.cgst == D("0.00")
    assert line.sgst == D("0.00")
    assert line.line_total == D("118.00")


def test_multi_line_totals():
    comp = compute_bill(
        [
            LineInput(unit_price=100, quantity=2, gst_percentage=5),
            LineInput(unit_price=50, quantity=1, gst_percentage=12),
        ],
        gst_mode="exclusive",
        place_of_supply="intra",
    )
    # line1: taxable 200, gst 10 ; line2: taxable 50, gst 6
    assert comp.total_taxable == D("250.00")
    assert comp.total_gst == D("16.00")
    assert comp.grand_total == D("266.00")
    assert comp.total_cgst == D("8.00")
    assert comp.total_sgst == D("8.00")


def test_line_discount_applied_before_gst():
    comp = compute_bill(
        [LineInput(unit_price=100, quantity=1, gst_percentage=10, discount=20)],
        gst_mode="exclusive",
    )
    line = comp.lines[0]
    assert line.taxable_value == D("80.00")
    assert line.gst_amount == D("8.00")
    assert line.line_total == D("88.00")


def test_bill_discount_distributed_proportionally():
    comp = compute_bill(
        [
            LineInput(unit_price=100, quantity=1, gst_percentage=0),
            LineInput(unit_price=100, quantity=1, gst_percentage=0),
        ],
        gst_mode="exclusive",
        bill_discount=20,
    )
    # 20 split evenly across two equal lines -> 10 each
    assert comp.lines[0].discount == D("10.00")
    assert comp.lines[1].discount == D("10.00")
    assert comp.total_discount == D("20.00")
    assert comp.grand_total == D("180.00")


def test_half_up_rounding():
    comp = compute_bill(
        [LineInput(unit_price="33.33", quantity=1, gst_percentage=18)],
        gst_mode="exclusive",
    )
    # 33.33 * 0.18 = 5.9994 -> rounds half-up to 6.00
    assert comp.lines[0].gst_amount == D("6.00")
