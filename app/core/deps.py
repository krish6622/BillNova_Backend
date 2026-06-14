"""FastAPI dependencies: DB session, current user, tenant context, RBAC.

RBAC is enforced by two dependency factories — ``require_role`` (role membership) and
``require_permission`` (the permission matrix in ``app.core.permissions``). Both funnel
denials through ``_deny`` so every blocked request is recorded in the access audit log.
"""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ForbiddenError, TokenError
from app.core.permissions import has_permission
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.user import ROLE_OWNER, User
from app.services import audit_service

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if creds is None:
        raise TokenError("Missing bearer token.")
    payload = decode_token(creds.credentials, expected_type=TOKEN_TYPE_ACCESS)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenError("Malformed token subject.") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise TokenError("User not found or inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_tenant_id(user: CurrentUser) -> uuid.UUID:
    return user.tenant_id


TenantId = Annotated[uuid.UUID, Depends(get_current_tenant_id)]


def _deny(db: Session, request: Request, user: User, action: str) -> None:
    """Record the denial and raise 403. Single chokepoint for every RBAC guard."""
    audit_service.log_access_denied(db, user=user, request=request, action=action)
    raise ForbiddenError("You do not have permission to perform this action.")


def require_role(*roles: str) -> Callable[..., User]:
    """Dependency factory enforcing that the current user has one of `roles`."""

    def _checker(request: Request, db: DbSession, user: CurrentUser) -> User:
        if user.role not in roles:
            _deny(db, request, user, action="role:" + "|".join(roles))
        return user

    return _checker


def require_permission(*permissions: str) -> Callable[..., User]:
    """Dependency factory enforcing that the current user's role grants ALL of
    `permissions` per the central matrix. Denials are audited."""

    def _checker(request: Request, db: DbSession, user: CurrentUser) -> User:
        missing = [p for p in permissions if not has_permission(user.role, p)]
        if missing:
            _deny(db, request, user, action=",".join(missing))
        return user

    return _checker


# Convenience: Owner-only guard (Owner == Admin).
require_owner = require_role(ROLE_OWNER)


def require_admin_key(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    """Gate platform-ops endpoints (e.g. manual subscription activation) behind a
    configured admin API key. Disabled (always 403) when no key is configured."""
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise ForbiddenError("Admin credentials required.")
