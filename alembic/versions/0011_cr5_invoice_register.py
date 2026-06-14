"""CR-5 — invoice register: sale status/void, customer name, tenant invoice_type.

Revision ID: 0011_cr5_invoice_register
Revises: 0010_cr4_default_gst_exclusive
Create Date: 2026-06-13

Adds the columns the Invoice Register needs:
  - sales.status        active | void   (voided sales reverse stock and stop counting)
  - sales.voided_at     when the sale was voided
  - sales.customer_name optional walk-in customer captured at the POS
  - tenants.invoice_type thermal_80 (default) | thermal_58 | a4 print format

All additive and backfilled with safe defaults — existing invoices become 'active' and
existing tenants default to thermal_80. No data is rewritten.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_cr5_invoice_register"
down_revision: str | None = "0010_cr4_default_gst_exclusive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("status", sa.String(length=10), nullable=False, server_default="active"),
    )
    op.add_column("sales", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales", sa.Column("customer_name", sa.String(length=255), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("invoice_type", sa.String(length=12), nullable=False, server_default="thermal_80"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "invoice_type")
    op.drop_column("sales", "customer_name")
    op.drop_column("sales", "voided_at")
    op.drop_column("sales", "status")
