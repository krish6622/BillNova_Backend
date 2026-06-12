"""CR-1 — products: drop category, add profit margin, tenant_created index.

Revision ID: 0006_cr1_products
Revises: 0005_tenant_settings
Create Date: 2026-06-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_cr1_products"
down_revision: str | None = "0005_tenant_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) Add profit-margin columns (with server defaults so existing rows are valid).
    op.add_column(
        "products",
        sa.Column("margin_type", sa.String(length=10), nullable=False, server_default="percentage"),
    )
    op.add_column(
        "products",
        sa.Column("margin_value", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    # 2) Backfill margin for existing rows as a fixed amount (selling - purchase, floored at 0).
    op.execute(
        "UPDATE products SET margin_type = 'amount', "
        "margin_value = GREATEST(COALESCE(selling_price, 0) - COALESCE(purchase_price, 0), 0)"
    )

    # 3) Recent-products / fast tenant-scoped listing index.
    op.create_index("ix_products_tenant_created", "products", ["tenant_id", "created_at"])

    # 4) Drop the now-unused category column (data preserved everywhere else).
    op.drop_column("products", "category")


def downgrade() -> None:
    op.add_column("products", sa.Column("category", sa.String(length=100), nullable=True))
    op.drop_index("ix_products_tenant_created", table_name="products")
    op.drop_column("products", "margin_value")
    op.drop_column("products", "margin_type")
