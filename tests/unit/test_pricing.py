"""Unit tests for the markup → selling-price engine (CR-3 renamed profit→markup).

Selling Price = Purchase Price + Markup Amount. There is exactly one formula.
"""

from decimal import Decimal

from app.services.pricing import compute_selling_price


def test_selling_price_is_purchase_plus_markup():
    assert compute_selling_price(100, 25) == Decimal("125.00")


def test_zero_markup_equals_purchase_price():
    assert compute_selling_price(105, 0) == Decimal("105.00")


def test_decimal_string_inputs():
    assert compute_selling_price("33.33", "6.00") == Decimal("39.33")


def test_rounding_half_up():
    # 100.001 -> 100.00 (rounds down); 10.005 -> 10.01 (half-up rounds up)
    assert compute_selling_price("99.99", "0.011") == Decimal("100.00")
    assert compute_selling_price("10.00", "0.005") == Decimal("10.01")


def test_result_is_two_decimal_places():
    assert str(compute_selling_price(100, 0)) == "100.00"
