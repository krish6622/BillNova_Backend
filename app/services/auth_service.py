"""Authentication & registration logic."""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthError, DuplicateError, TokenError
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.subscription import STATUS_TRIAL, TenantSubscription
from app.models.tenant import Tenant
from app.models.user import ROLE_OWNER, User
from app.repositories.user_repo import email_exists, get_user_by_email


@dataclass
class AuthResult:
    access_token: str
    refresh_token: str
    user: User
    tenant: Tenant


def _tokens_for(user: User) -> tuple[str, str]:
    access = create_access_token(
        user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role
    )
    refresh = create_refresh_token(
        user_id=str(user.id), tenant_id=str(user.tenant_id), token_version=user.token_version
    )
    return access, refresh


def register(db: Session, *, business_name: str, owner_name: str, mobile: str, email: str,
             password: str, gst_number: str | None) -> AuthResult:
    email = email.lower()
    if email_exists(db, email):
        raise DuplicateError("An account with this email already exists.")

    tenant = Tenant(
        business_name=business_name,
        owner_name=owner_name,
        mobile=mobile,
        email=email,
        gst_number=gst_number,
        subscription_status=STATUS_TRIAL,
    )
    db.add(tenant)
    db.flush()  # assign tenant.id

    user = User(
        tenant_id=tenant.id,
        name=owner_name,
        email=email,
        password_hash=hash_password(password),
        role=ROLE_OWNER,
    )
    db.add(user)

    today = date.today()
    db.add(
        TenantSubscription(
            tenant_id=tenant.id,
            plan_id=None,
            status=STATUS_TRIAL,
            period_start=today,
            period_end=today + timedelta(days=settings.trial_days),
        )
    )

    db.commit()
    db.refresh(user)
    db.refresh(tenant)

    access, refresh = _tokens_for(user)
    return AuthResult(access, refresh, user, tenant)


def authenticate(db: Session, *, email: str, password: str) -> AuthResult:
    user = get_user_by_email(db, email.lower())
    # Constant-ish path: always run a generic failure for missing/invalid/inactive.
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.")

    tenant = db.get(Tenant, user.tenant_id)
    access, refresh = _tokens_for(user)
    return AuthResult(access, refresh, user, tenant)


def refresh_access_token(db: Session, *, refresh_token: str) -> str:
    payload = decode_token(refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenError("Malformed token subject.") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active or payload.get("tv") != user.token_version:
        raise TokenError("Refresh token is no longer valid.")

    return create_access_token(
        user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role
    )


def logout(db: Session, *, user: User) -> None:
    """Invalidate outstanding refresh tokens by bumping the token version."""
    user.token_version += 1
    db.add(user)
    db.commit()
