"""Unit tests for the profit-margin → selling-price engine."""

from decimal import Decimal

from app.services.pricing import compute_selling_price


def test_percentage_margin():
    assert compute_selling_price(100, "percentage", 25) == Decimal("125.00")


def test_amount_margin():
    assert compute_selling_price(100, "amount", 20) == Decimal("120.00")


def test_zero_margin():
    assert compute_selling_price(105, "amount", 0) == Decimal("105.00")


def test_rounding_half_up():
    # 33.33 * 1.18 = 39.3294 -> 39.33
    assert compute_selling_price("33.33", "percentage", 18) == Decimal("39.33")
