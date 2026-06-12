"""Business settings router (Owner-only)."""

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, TenantId, require_owner
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_owner)])


@router.get("", response_model=SettingsOut)
def get_settings(db: DbSession, tenant_id: TenantId) -> SettingsOut:
    return SettingsOut.model_validate(settings_service.get_settings(db, tenant_id))


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: DbSession, tenant_id: TenantId) -> SettingsOut:
    return SettingsOut.model_validate(settings_service.update_settings(db, tenant_id, payload))
