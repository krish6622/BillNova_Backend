"""Audit logging for access-control decisions.

Centralised so every RBAC guard records denials the same way. Logging is best-effort:
a failure here must never mask the original 403 or break the request, so the writer
swallows its own errors (after rolling back) and lets the guard raise as normal.
"""

import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import RESULT_ACCESS_DENIED, AccessAuditLog
from app.models.user import User


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    # Honour the first hop in X-Forwarded-For when behind nginx/proxy, else peer IP.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def log_access_denied(
    db: Session,
    *,
    user: User | None,
    request: Request | None,
    action: str | None,
) -> None:
    """Persist an ACCESS_DENIED audit row for a blocked request."""
    try:
        entry = AccessAuditLog(
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            role=user.role if user else None,
            method=request.method if request else "",
            path=request.url.path if request else "",
            action=action,
            ip_address=_client_ip(request),
            result=RESULT_ACCESS_DENIED,
        )
        db.add(entry)
        db.commit()
    except Exception:  # never let audit failure surface to the client
        db.rollback()


def list_access_logs(
    db: Session, tenant_id: uuid.UUID, *, limit: int = 100
) -> list[AccessAuditLog]:
    """Most recent access-denied entries for a tenant (Owner audit view)."""
    from sqlalchemy import select

    return list(
        db.scalars(
            select(AccessAuditLog)
            .where(AccessAuditLog.tenant_id == tenant_id)
            .order_by(AccessAuditLog.created_at.desc())
            .limit(limit)
        )
    )
