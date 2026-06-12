"""Profit-margin → selling-price computation (pure, fully testable)."""

from decimal import ROUND_HALF_UP, Decimal

TWO = Decimal("0.01")
MARGIN_PERCENTAGE = "percentage"
MARGIN_AMOUNT = "amount"


def compute_selling_price(purchase_price, margin_type: str, margin_value) -> Decimal:
    pp = Decimal(str(purchase_price))
    mv = Decimal(str(margin_value))
    if margin_type == MARGIN_AMOUNT:
        selling = pp + mv
    else:  # percentage (default)
        selling = pp * (1 + mv / 100)
    return selling.quantize(TWO, rounding=ROUND_HALF_UP)
