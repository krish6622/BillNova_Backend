"""User management router (Owner-only)."""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import DbSession, TenantId, require_owner
from app.repositories.user_repo import UserRepository
from app.schemas.user import PasswordReset, UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_owner)])


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, tenant_id: TenantId) -> list[UserOut]:
    users = UserRepository(db, tenant_id).list()
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, tenant_id: TenantId) -> UserOut:
    user = user_service.create_user(db, tenant_id=tenant_id, payload=payload)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: DbSession, tenant_id: TenantId) -> UserOut:
    user = user_service.update_user(db, tenant_id=tenant_id, user_id=user_id, payload=payload)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(user_id: uuid.UUID, payload: PasswordReset, db: DbSession, tenant_id: TenantId) -> UserOut:
    user = user_service.reset_password(db, tenant_id=tenant_id, user_id=user_id, password=payload.password)
    return UserOut.model_validate(user)
