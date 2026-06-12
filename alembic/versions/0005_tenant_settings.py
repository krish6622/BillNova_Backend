"""M7 — tenant settings columns (address, invoice prefix/footer).

Revision ID: 0005_tenant_settings
Revises: 0004_purchases
Create Date: 2026-06-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_tenant_settings"
down_revision: str | None = "0004_purchases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("invoice_prefix", sa.String(length=10), nullable=False, server_default="INV"),
    )
    op.add_column("tenants", sa.Column("invoice_footer", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "invoice_footer")
    op.drop_column("tenants", "invoice_prefix")
    op.drop_column("tenants", "address")
