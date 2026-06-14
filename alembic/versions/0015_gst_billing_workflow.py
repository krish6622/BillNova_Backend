"""GST billing workflow — per-bill billing type + GST-customer details on sales.

Revision ID: 0015_gst_billing_workflow
Revises: 0014_access_audit_log
Create Date: 2026-06-14

Purely additive. Adds to `sales`:
  - is_gst_customer  (bool, default false)   — B2B customer flag
  - customer_mobile  (varchar 20, nullable)  — optional GST-customer contact
  - customer_gstin   (varchar 15, nullable)  — GST-customer GSTIN
  - billing_type     (varchar 20, WITH_GST)  — WITH_GST | WITHOUT_GST, frozen per bill

Existing invoices were all GST-taxed, so `billing_type` backfills to WITH_GST via the
server_default — their reports/totals are unchanged. (show_gst_on_invoice and total_gst
already exist from CR-7, so they are not re-added here.)
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_gst_billing_workflow"
down_revision: str | None = "0014_access_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("is_gst_customer", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("sales", sa.Column("customer_mobile", sa.String(length=20), nullable=True))
    op.add_column("sales", sa.Column("customer_gstin", sa.String(length=15), nullable=True))
    op.add_column(
        "sales",
        sa.Column("billing_type", sa.String(length=20), nullable=False, server_default="WITH_GST"),
    )


def downgrade() -> None:
    op.drop_column("sales", "billing_type")
    op.drop_column("sales", "customer_gstin")
    op.drop_column("sales", "customer_mobile")
    op.drop_column("sales", "is_gst_customer")
