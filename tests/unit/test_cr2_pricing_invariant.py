"""CR-2 unit tests: the locked GST-on-selling-price invariant + validation rules.

- Sales (output) GST must derive from the SELLING price, never the purchase price.
- Profit Amount >= 0, Purchase Price > 0, GST 0..100 are enforced at the schema layer.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.product import ProductUpdate
from app.schemas.purchase import PurchaseItemInput
from app.services.billing_service import _line_inputs
from app.services.gst_service import compute_bill


# ---- CR-2.1 invariant: GST input = selling price, never purchase price -------

def test_line_inputs_use_selling_price_not_purchase_price():
    pid = "00000000-0000-0000-0000-000000000001"
    # purchase 100, selling 125 — deliberately different so we can tell them apart.
    product = SimpleNamespace(
        id=pid, selling_price=Decimal("125.00"), purchase_price=Decimal("100.00"),
        gst_percentage=Decimal("5"),
    )
    item = SimpleNamespace(product_id=pid, quantity=1, discount=0)

    lines = _line_inputs([item], {pid: product})

    assert lines[0].unit_price == Decimal("125.00")          # selling price
    assert lines[0].unit_price != product.purchase_price     # NOT purchase price


def test_gst_computed_from_selling_price_inclusive():
    # selling 125 inclusive @5% -> taxable 119.05, gst 5.95 (driven by 125, not 100).
    pid = "00000000-0000-0000-0000-000000000002"
    product = SimpleNamespace(
        id=pid, selling_price=Decimal("125.00"), purchase_price=Decimal("100.00"),
        gst_percentage=Decimal("5"),
    )
    item = SimpleNamespace(product_id=pid, quantity=1, discount=0)
    comp = compute_bill(_line_inputs([item], {pid: product}), gst_mode="inclusive")
    line = comp.lines[0]
    assert line.taxable_value == Decimal("119.05")
    assert line.gst_amount == Decimal("5.95")
    # Sanity: if GST had (wrongly) used purchase 100 inclusive, gst would be 4.76.
    assert line.gst_amount != Decimal("4.76")


# ---- CR-2.10 validation rules ------------------------------------------------

def test_product_update_rejects_negative_markup():
    with pytest.raises(ValidationError):
        ProductUpdate(markup_amount=-1)


def test_product_update_allows_zero_markup():
    assert ProductUpdate(markup_amount=0).markup_amount == 0


def test_product_update_gst_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        ProductUpdate(gst_percentage=101)
    with pytest.raises(ValidationError):
        ProductUpdate(gst_percentage=-1)


def _purchase_item(**over):
    base = dict(product_name="Widget", purchase_price=100, markup_amount=10,
                quantity=1, gst_percentage=5)
    base.update(over)
    return PurchaseItemInput(**base)


def test_purchase_item_rejects_negative_markup():
    with pytest.raises(ValidationError):
        _purchase_item(markup_amount=-5)


def test_purchase_item_requires_purchase_price_gt_zero():
    with pytest.raises(ValidationError):
        _purchase_item(purchase_price=0)


def test_purchase_item_gst_bounds():
    with pytest.raises(ValidationError):
        _purchase_item(gst_percentage=101)
    with pytest.raises(ValidationError):
        _purchase_item(gst_percentage=-1)


def test_purchase_item_valid_passes():
    item = _purchase_item(purchase_price=100, markup_amount=25)
    assert item.purchase_price == 100
    assert item.markup_amount == 25
