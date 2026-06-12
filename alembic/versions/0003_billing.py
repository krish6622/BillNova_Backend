"""M3 — billing: sales, sale_items, payments, inventory_transactions.

Revision ID: 0003_billing
Revises: 0002_products
Create Date: 2026-06-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_billing"
down_revision: str | None = "0002_products"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("gst_mode", sa.String(length=10), nullable=False),
        sa.Column("place_of_supply", sa.String(length=10), nullable=False),
        sa.Column("total_taxable", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_cgst", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_sgst", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_igst", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_gst", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("grand_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "invoice_number", name="uq_sale_invoice_tenant"),
    )
    op.create_index("ix_sales_tenant_id", "sales", ["tenant_id"])
    op.create_index("ix_sales_created_at", "sales", ["created_at"])

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("hsn_code", sa.String(length=20), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("gst_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("taxable_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("cgst", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("sgst", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("igst", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_items_tenant_id", "sale_items", ["tenant_id"])
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])
    op.create_index("ix_payments_sale_id", "payments", ["sale_id"])

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 3), nullable=False),
        sa.Column("ref_type", sa.String(length=20), nullable=True),
        sa.Column("ref_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_transactions_tenant_id", "inventory_transactions", ["tenant_id"])
    op.create_index("ix_inventory_transactions_product_id", "inventory_transactions", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_product_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_tenant_id", table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    op.drop_index("ix_payments_sale_id", table_name="payments")
    op.drop_index("ix_payments_tenant_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_sale_items_sale_id", table_name="sale_items")
    op.drop_index("ix_sale_items_tenant_id", table_name="sale_items")
    op.drop_table("sale_items")
    op.drop_index("ix_sales_created_at", table_name="sales")
    op.drop_index("ix_sales_tenant_id", table_name="sales")
    op.drop_table("sales")
