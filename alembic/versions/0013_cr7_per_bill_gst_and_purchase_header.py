"""CR-7 — per-bill GST display, drop global GST settings, purchase header fields.

Revision ID: 0013_cr7_per_bill_gst_and_purchase_header
Revises: 0012_cr6_show_branding
Create Date: 2026-06-13

Part 2 — remove the global Default GST Mode setting (pricing is now always exclusive,
         the CR-4 standard): drop tenants.gst_mode_default.
Part 3 — GST display moves from a global tenant setting to PER BILL:
         add sales.show_gst_on_invoice, backfill it from the tenant's current value so
         historical invoices keep their look, then drop tenants.show_gst_on_invoice.
Part 1 — purchase header: add purchases.invoice_number and purchases.notes.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_cr7_per_bill_gst"
down_revision: str | None = "0012_cr6_show_branding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Part 3 — per-bill GST display.
    op.add_column(
        "sales",
        sa.Column("show_gst_on_invoice", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Preserve each existing invoice's look by copying the tenant's current setting.
    op.execute(
        "UPDATE sales SET show_gst_on_invoice = COALESCE("
        "  (SELECT t.show_gst_on_invoice FROM tenants t WHERE t.id = sales.tenant_id), false)"
    )

    # Part 1 — purchase header.
    op.add_column("purchases", sa.Column("invoice_number", sa.String(length=50), nullable=True))
    op.add_column("purchases", sa.Column("notes", sa.String(length=500), nullable=True))

    # Parts 2 & 3 — remove the now-unused global GST settings.
    op.drop_column("tenants", "show_gst_on_invoice")
    op.drop_column("tenants", "gst_mode_default")


def downgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("gst_mode_default", sa.String(length=10), nullable=False, server_default="exclusive"),
    )
    op.add_column(
        "tenants",
        sa.Column("show_gst_on_invoice", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute(
        "UPDATE tenants SET show_gst_on_invoice = COALESCE("
        "  (SELECT bool_or(s.show_gst_on_invoice) FROM sales s WHERE s.tenant_id = tenants.id), false)"
    )
    op.drop_column("purchases", "notes")
    op.drop_column("purchases", "invoice_number")
    op.drop_column("sales", "show_gst_on_invoice")
