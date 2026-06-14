"""Dashboard router — role-scoped KPIs.

Owner (Admin) sees full business analytics; a cashier sees only their own billing
activity for today (no revenue/profit/GST/stock insights).
"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession, TenantId
from app.models.user import ROLE_OWNER
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: DbSession, tenant_id: TenantId, user: CurrentUser) -> dict:
    if user.role == ROLE_OWNER:
        return dashboard_service.kpis(db, tenant_id)
    return dashboard_service.cashier_kpis(db, tenant_id, user.id)
