"""Subscription / usage router (read-only in M1; enforcement + activate in M5)."""

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, TenantId, require_admin_key
from app.schemas.subscription import ActivateRequest, PlanOut, SubscriptionOut
from app.services import subscription_service

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("", response_model=SubscriptionOut)
def get_subscription(db: DbSession, tenant_id: TenantId) -> SubscriptionOut:
    return SubscriptionOut(**subscription_service.get_subscription_summary(db, tenant_id))


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: DbSession) -> list[PlanOut]:
    return [PlanOut.model_validate(p) for p in subscription_service.list_plans(db)]


@router.post("/activate", response_model=SubscriptionOut, dependencies=[Depends(require_admin_key)])
def activate(payload: ActivateRequest, db: DbSession) -> SubscriptionOut:
    """Manual activation/upgrade — platform ops only (X-Admin-Key header)."""
    subscription_service.activate(
        db,
        tenant_id=payload.tenant_id,
        plan_id=payload.plan_id,
        status=payload.status,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return SubscriptionOut(**subscription_service.get_subscription_summary(db, payload.tenant_id))
