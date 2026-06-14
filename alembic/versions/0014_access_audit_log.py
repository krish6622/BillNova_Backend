"""RBAC — access audit log table.

Revision ID: 0014_access_audit_log
Revises: 0013_cr7_per_bill_gst
Create Date: 2026-06-14

Adds `access_audit_log`: one row per blocked access attempt (HTTP 403) written by the
RBAC guards. Purely additive — no existing data is touched.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_access_audit_log"
down_revision: str | None = "0013_cr7_per_bill_gst"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False, server_default="ACCESS_DENIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_access_audit_log_tenant_id", "access_audit_log", ["tenant_id"])
    op.create_index("ix_access_audit_log_user_id", "access_audit_log", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_access_audit_log_user_id", table_name="access_audit_log")
    op.drop_index("ix_access_audit_log_tenant_id", table_name="access_audit_log")
    op.drop_table("access_audit_log")
