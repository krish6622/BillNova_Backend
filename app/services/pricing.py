"""Markup → selling-price computation (pure, fully testable).

CR-3: selling price is the purchase price plus a fixed markup amount. (The field was
renamed from profit_amount to markup_amount — retailers think in "markup".)
"""

from decimal import ROUND_HALF_UP, Decimal

TWO = Decimal("0.01")


def compute_selling_price(purchase_price, markup_amount) -> Decimal:
    """Selling Price = Purchase Price + Markup Amount (rounded to 2dp).

    e.g. purchase 250 + markup 252 -> 502.00. Always read-only/derived; never
    accepted from the client.
    """
    pp = Decimal(str(purchase_price))
    markup = Decimal(str(markup_amount))
    return (pp + markup).quantize(TWO, rounding=ROUND_HALF_UP)


# --- CR-6: per-unit DISPLAY rates for invoices (shared by thermal + A4 + frontend) -------
# A printed line must always satisfy: quantity × displayed_rate == displayed_amount.
# These derive the per-unit rate from the authoritative stored line value so the identity
# holds regardless of GST mode. The frontend mirrors these in src/lib/pricing.ts.

def _per_unit(total, quantity) -> Decimal:
    q = Decimal(str(quantity))
    if q == 0:
        return Decimal("0.00")
    return (Decimal(str(total)) / q).quantize(TWO, rounding=ROUND_HALF_UP)


def customer_unit_rate(line_total, quantity) -> Decimal:
    """GST-HIDDEN display rate: the all-inclusive per-unit price the customer pays.
    e.g. line_total 630 / qty 3 -> 210.00 (displayed amount stays 630)."""
    return _per_unit(line_total, quantity)


def net_unit_rate(taxable_value, quantity) -> Decimal:
    """GST-VISIBLE display rate: the per-unit taxable (pre-GST) price — equals the selling
    price in exclusive mode. e.g. taxable 600 / qty 3 -> 200.00 (amount 600, GST shown separately)."""
    return _per_unit(taxable_value, quantity)
