"""Subscription / usage router (read-only in M1; enforcement + activate in M5)."""

from fastapi import APIRouter

from app.core.deps import DbSession, TenantId
from app.schemas.subscription import PlanOut, SubscriptionOut
from app.services import subscription_service

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("", response_model=SubscriptionOut)
def get_subscription(db: DbSession, tenant_id: TenantId) -> SubscriptionOut:
    return SubscriptionOut(**subscription_service.get_subscription_summary(db, tenant_id))


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: DbSession) -> list[PlanOut]:
    return [PlanOut.model_validate(p) for p in subscription_service.list_plans(db)]
