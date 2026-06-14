"""Access audit log — one row per blocked (or otherwise audited) access attempt.

Written whenever an RBAC guard denies a request (HTTP 403). Retained for security
review: who tried to reach what, from where, and when. Tenant-scoped where the user
is known; ``user_id``/``tenant_id`` are nullable so we can still record a denial even
if the subject cannot be resolved.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

RESULT_ACCESS_DENIED = "ACCESS_DENIED"


class AccessAuditLog(Base):
    __tablename__ = "access_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # The page / endpoint the subject attempted to reach.
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(255))
    # The permission (or role) that was required but missing — the reason for denial.
    action: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[str] = mapped_column(String(32), default=RESULT_ACCESS_DENIED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
