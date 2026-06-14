"""CR-4 — default GST mode exclusive (POS mirrors the Purchase Pricing Preview).

Revision ID: 0010_cr4_default_gst_exclusive
Revises: 0009_cr3_saleitem_unit
Create Date: 2026-06-13

Root cause of the POS/profit defect: tenants defaulted to gst_mode_default="inclusive",
so the POS carved GST OUT of the selling price (selling 100 -> grand 100, taxable 95.24)
instead of adding it ON TOP (selling 100 + 5% -> grand 105). That silently absorbed the
markup into GST and understated profit.

This migration:
  1. Sets the column server_default to 'exclusive' for all NEW tenants.
  2. One-time correction of existing tenants still carrying the defective 'inclusive'
     default, flipping them to 'exclusive'.

Historical sales are NOT touched: every `sales` row stores its own `gst_mode` and frozen
taxable/gst/grand_total, so past invoices keep the exact figures they were issued with.
A tenant who genuinely wants inclusive billing can re-select it in Settings afterwards.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0010_cr4_default_gst_exclusive"
down_revision: str | None = "0009_cr3_saleitem_unit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) New rows default to exclusive.
    op.alter_column("tenants", "gst_mode_default", server_default="exclusive")
    # 2) Correct existing tenants left on the defective default. (Settings rows only —
    #    issued invoices are immutable and keep their own per-sale gst_mode.)
    op.execute(
        "UPDATE tenants SET gst_mode_default = 'exclusive' "
        "WHERE gst_mode_default = 'inclusive'"
    )


def downgrade() -> None:
    op.alter_column("tenants", "gst_mode_default", server_default="inclusive")
