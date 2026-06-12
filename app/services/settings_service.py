"""Business settings (Owner-only)."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.tenant import Tenant
from app.schemas.settings import SettingsUpdate


def get_settings(db: Session, tenant_id: uuid.UUID) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found.")
    return tenant


def update_settings(db: Session, tenant_id: uuid.UUID, payload: SettingsUpdate) -> Tenant:
    tenant = get_settings(db, tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    db.commit()
    db.refresh(tenant)
    return tenant
