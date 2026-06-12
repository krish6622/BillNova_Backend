"""User management logic (Owner-only)."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import DuplicateError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repo import email_exists, get_user_in_tenant
from app.schemas.user import UserCreate, UserUpdate


def create_user(db: Session, *, tenant_id: uuid.UUID, payload: UserCreate) -> User:
    email = payload.email.lower()
    if email_exists(db, email):
        raise DuplicateError("An account with this email already exists.")
    user = User(
        tenant_id=tenant_id,
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.normalized_role(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _require_user(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = get_user_in_tenant(db, tenant_id, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def update_user(db: Session, *, tenant_id: uuid.UUID, user_id: uuid.UUID, payload: UserUpdate) -> User:
    user = _require_user(db, tenant_id, user_id)
    if payload.name is not None:
        user.name = payload.name
    if payload.is_active is not None:
        user.is_active = payload.is_active
        if payload.is_active is False:
            user.token_version += 1  # force logout of a deactivated user
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, *, tenant_id: uuid.UUID, user_id: uuid.UUID, password: str) -> User:
    user = _require_user(db, tenant_id, user_id)
    user.password_hash = hash_password(password)
    user.token_version += 1  # invalidate existing sessions
    db.commit()
    db.refresh(user)
    return user
