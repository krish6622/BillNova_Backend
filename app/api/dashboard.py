"""Dashboard router — KPIs for any authenticated user."""

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession, TenantId
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: DbSession, tenant_id: TenantId, _u: CurrentUser) -> dict:
    return dashboard_service.kpis(db, tenant_id)
