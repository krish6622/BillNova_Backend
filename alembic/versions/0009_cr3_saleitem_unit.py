"""CR-3 — snapshot unit on sale_items (so invoices can print "2 NOS").

Revision ID: 0009_cr3_saleitem_unit
Revises: 0008_cr3_markup_rename
Create Date: 2026-06-13

Adds sale_items.unit (NOT NULL DEFAULT 'NOS'). Existing rows backfill to 'NOS' via the
server default (the app standard). Future sales snapshot the product's unit at sale time,
consistent with the existing product_name / hsn_code snapshots.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_cr3_saleitem_unit"
down_revision: str | None = "0008_cr3_markup_rename"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sale_items",
        sa.Column("unit", sa.String(length=20), nullable=False, server_default="NOS"),
    )


def downgrade() -> None:
    op.drop_column("sale_items", "unit")
