"""CR-2 — pricing + invoice GST: profit_amount replaces margin_type/value, add show_gst_on_invoice.

Revision ID: 0007_cr2_pricing_invoice_gst
Revises: 0006_cr1_products
Create Date: 2026-06-13

Data-preserving:
- tenants.show_gst_on_invoice added NOT NULL DEFAULT false (customer-invoice tax privacy).
- products.profit_amount added, backfilled from (selling_price - purchase_price) floored at 0,
  so SP = purchase_price + profit_amount holds for every existing row WITHOUT changing selling_price.
- margin_type / margin_value dropped (percentage pricing removed in CR-2).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_cr2_pricing_invoice_gst"
down_revision: str | None = "0006_cr1_products"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) Customer-invoice GST privacy toggle. Default Hide (false) for ALL tenants (new + existing).
    op.add_column(
        "tenants",
        sa.Column("show_gst_on_invoice", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # 2) Single profit driver. Server default keeps existing rows valid before backfill.
    op.add_column(
        "products",
        sa.Column("profit_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    # 3) Backfill: record the equivalent fixed profit so SP = PP + profit_amount stays exact.
    #    selling_price is NOT modified. Floored at 0 to honour the >= 0 rule.
    op.execute(
        "UPDATE products SET profit_amount = "
        "GREATEST(COALESCE(selling_price, 0) - COALESCE(purchase_price, 0), 0)"
    )

    # 4) Drop the now-removed percentage-pricing columns (after profit_amount is populated).
    op.drop_column("products", "margin_value")
    op.drop_column("products", "margin_type")


def downgrade() -> None:
    # Restore margin columns as fixed-amount (the only semantics CR-2 retained), so selling
    # prices stay consistent: margin_type='amount', margin_value=profit_amount.
    op.add_column(
        "products",
        sa.Column("margin_type", sa.String(length=10), nullable=False, server_default="amount"),
    )
    op.add_column(
        "products",
        sa.Column("margin_value", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.execute("UPDATE products SET margin_type = 'amount', margin_value = profit_amount")

    op.drop_column("products", "profit_amount")
    op.drop_column("tenants", "show_gst_on_invoice")
