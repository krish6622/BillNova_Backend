"""CR-4 — shared pricing-engine guarantees (pure, no DB).

Locks the standard pricing formula and proves the POS engine preserves the full markup
in the default (exclusive) mode, where the legacy inclusive default silently absorbed it.

Canonical worked example (from the CR-4 brief):
    purchase 80 + markup 20 -> selling 100 ; GST 5%
    exclusive: customer 105 (GST 5)   ; merchant keeps 100  -> margin 20 (full markup)
    inclusive: customer 100 (GST 4.76); merchant keeps 95.24 -> margin 15.24 (markup eroded)
"""

from decimal import Decimal as D

from app.services.gst_service import LineInput, compute_bill
from app.services.pricing import compute_selling_price

COST = D("80")
MARKUP = D("20")
RATE = D("5")


def _line(qty):
    selling = compute_selling_price(COST, MARKUP)  # 100.00
    return LineInput(unit_price=selling, quantity=D(qty), gst_percentage=RATE)


def test_selling_price_is_purchase_plus_markup():
    assert compute_selling_price(COST, MARKUP) == D("100.00")


def test_exclusive_qty1_adds_gst_on_top():
    comp = compute_bill([_line(1)], gst_mode="exclusive")
    line = comp.lines[0]
    assert line.taxable_value == D("100.00")
    assert line.gst_amount == D("5.00")
    assert line.line_total == D("105.00")
    assert comp.grand_total == D("105.00")


def test_exclusive_qty3_scales_linearly():
    comp = compute_bill([_line(3)], gst_mode="exclusive")
    assert comp.total_taxable == D("300.00")
    assert comp.total_gst == D("15.00")
    assert comp.grand_total == D("315.00")


def test_inclusive_qty1_carves_gst_out():
    comp = compute_bill([_line(1)], gst_mode="inclusive")
    line = comp.lines[0]
    assert line.taxable_value == D("95.24")
    assert line.gst_amount == D("4.76")
    assert line.line_total == D("100.00")
    assert comp.grand_total == D("100.00")


def test_exclusive_preserves_full_markup_inclusive_erodes_it():
    # Merchant's retained value = taxable (the GST is remitted to the government).
    excl = compute_bill([_line(1)], gst_mode="exclusive")
    incl = compute_bill([_line(1)], gst_mode="inclusive")
    assert excl.total_taxable - COST == MARKUP            # margin 20.00 — full markup
    assert incl.total_taxable - COST < MARKUP             # margin 15.24 — markup eroded
    assert incl.total_taxable - COST == D("15.24")


def test_intra_state_split_sums_to_total_gst():
    comp = compute_bill([_line(1)], gst_mode="exclusive", place_of_supply="intra")
    line = comp.lines[0]
    assert line.cgst + line.sgst == line.gst_amount == D("5.00")
    assert line.igst == D("0.00")
