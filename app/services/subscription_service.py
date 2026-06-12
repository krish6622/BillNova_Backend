"""Subscription / usage read logic (enforcement lands in M5)."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subscription import STATUS_TRIAL, SubscriptionPlan, TenantSubscription
from app.models.usage import BillUsage

WARN_THRESHOLD = 0.8


def _effective_limit(sub: TenantSubscription | None, plan: SubscriptionPlan | None) -> int:
    """Trial uses the configured trial quota; a paid plan uses its monthly limit."""
    if sub is not None and sub.status == STATUS_TRIAL:
        return settings.trial_bill_quota
    if plan is not None:
        return plan.monthly_bill_limit
    return settings.trial_bill_quota


def current_usage_count(db: Session, tenant_id: uuid.UUID, *, today: date | None = None) -> int:
    today = today or date.today()
    row = db.scalar(
        select(BillUsage).where(
            BillUsage.tenant_id == tenant_id,
            BillUsage.year == today.year,
            BillUsage.month == today.month,
        )
    )
    return row.bills_count if row else 0


def get_subscription_summary(db: Session, tenant_id: uuid.UUID) -> dict:
    sub = db.scalar(
        select(TenantSubscription)
        .where(TenantSubscription.tenant_id == tenant_id)
        .order_by(TenantSubscription.created_at.desc())
    )
    plan = db.get(SubscriptionPlan, sub.plan_id) if sub and sub.plan_id else None
    limit = _effective_limit(sub, plan)
    used = current_usage_count(db, tenant_id)
    percent = round((used / limit) * 100, 1) if limit else 0.0

    warning = None
    if limit and used >= limit:
        warning = "LIMIT_REACHED"
    elif limit and used >= WARN_THRESHOLD * limit:
        warning = "APPROACHING_LIMIT"

    return {
        "plan": plan.name if plan else None,
        "status": sub.status if sub else STATUS_TRIAL,
        "monthly_bill_limit": limit,
        "usage": {"year": date.today().year, "month": date.today().month,
                  "bills_count": used, "percent": percent},
        "warning": warning,
        "period_end": sub.period_end.isoformat() if sub and sub.period_end else None,
    }


def list_plans(db: Session) -> list[SubscriptionPlan]:
    return list(
        db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(
            SubscriptionPlan.monthly_bill_limit))
    )
