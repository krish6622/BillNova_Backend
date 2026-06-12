"""FastAPI dependencies: DB session, current user, tenant context, RBAC."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ForbiddenError, TokenError
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.user import ROLE_OWNER, User

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


def require_role(*roles: str) -> Callable[[User], User]:
    """Dependency factory enforcing that the current user has one of `roles`."""

    def _checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action.")
        return user

    return _checker


# Convenience: Owner-only guard.
require_owner = require_role(ROLE_OWNER)


def require_admin_key(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    """Gate platform-ops endpoints (e.g. manual subscription activation) behind a
    configured admin API key. Disabled (always 403) when no key is configured."""
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise ForbiddenError("Admin credentials required.")
