"""CR-3 — rename products.profit_amount -> markup_amount (data-preserving).

Revision ID: 0008_cr3_markup_rename
Revises: 0007_cr2_pricing_invoice_gst
Create Date: 2026-06-13

"Markup" is the term small retailers understand. The selling-price rule is unchanged:
selling_price = purchase_price + markup_amount. A column RENAME carries all existing
values as-is (no data transformation). No other schema change — purchase GST/payable are
already persisted as purchase_items.gst_amount / line_total.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0008_cr3_markup_rename"
down_revision: str | None = "0007_cr2_pricing_invoice_gst"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("products", "profit_amount", new_column_name="markup_amount")


def downgrade() -> None:
    op.alter_column("products", "markup_amount", new_column_name="profit_amount")
