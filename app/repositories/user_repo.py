"""User repository — tenant-scoped listing plus a global email lookup for login."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import TenantRepository


class UserRepository(TenantRepository[User]):
    model = User

    def list(self) -> list[User]:
        return list(self.db.scalars(self._scoped(select(User)).order_by(User.created_at)))


def get_user_by_email(db: Session, email: str) -> User | None:
    """Global lookup used at login (email is globally unique)."""
    return db.scalar(select(User).where(User.email == email.lower()))


def email_exists(db: Session, email: str) -> bool:
    return get_user_by_email(db, email) is not None


def get_user_in_tenant(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        return None
    return user
