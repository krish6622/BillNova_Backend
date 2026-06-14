"""CR-6 — tenants.show_branding (footer "Powered by BillNova" toggle).

Revision ID: 0012_cr6_show_branding
Revises: 0011_cr5_invoice_register
Create Date: 2026-06-13

Additive boolean, default true (branding shown). Merchants may turn it off in Settings.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_cr6_show_branding"
down_revision: str | None = "0011_cr5_invoice_register"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("show_branding", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "show_branding")
