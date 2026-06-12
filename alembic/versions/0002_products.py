"""M2 — products table.

Revision ID: 0002_products
Revises: 0001_m1_initial
Create Date: 2026-06-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_products"
down_revision: str | None = "0001_m1_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("purchase_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("selling_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("gst_percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("hsn_code", sa.String(length=20), nullable=True),
        sa.Column("current_stock", sa.Numeric(precision=12, scale=3), nullable=False, server_default="0"),
        sa.Column("reorder_level", sa.Numeric(precision=12, scale=3), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "product_code", name="uq_product_code_tenant"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_hsn_code", "products", ["hsn_code"])
    op.create_index("ix_products_is_active", "products", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_products_is_active", table_name="products")
    op.drop_index("ix_products_hsn_code", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_table("products")
