"""Subscription / usage read logic (enforcement lands in M5)."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import SubscriptionInactiveError, SubscriptionLimitError
from app.models.subscription import (
    STATUS_ACTIVE,
    STATUS_TRIAL,
    SubscriptionPlan,
    TenantSubscription,
)
from app.models.usage import BillUsage

WARN_THRESHOLD = 0.8
BILLABLE_STATUSES = {STATUS_TRIAL, STATUS_ACTIVE}


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


def _current_subscription(db: Session, tenant_id: uuid.UUID) -> TenantSubscription | None:
    return db.scalar(
        select(TenantSubscription)
        .where(TenantSubscription.tenant_id == tenant_id)
        .order_by(TenantSubscription.created_at.desc())
    )


def effective_limit(db: Session, tenant_id: uuid.UUID) -> int:
    sub = _current_subscription(db, tenant_id)
    plan = db.get(SubscriptionPlan, sub.plan_id) if sub and sub.plan_id else None
    return _effective_limit(sub, plan)


def assert_can_bill(db: Session, tenant_id: uuid.UUID) -> None:
    """Guard run before saving a bill — blocks inactive/expired or over-limit tenants."""
    sub = _current_subscription(db, tenant_id)
    status = sub.status if sub else STATUS_TRIAL
    if status not in BILLABLE_STATUSES:
        raise SubscriptionInactiveError(f"Subscription is {status}. Billing is disabled.")
    limit = effective_limit(db, tenant_id)
    if limit and current_usage_count(db, tenant_id) >= limit:
        raise SubscriptionLimitError("Monthly bill limit reached. Upgrade your plan to continue.")


def increment_usage(db: Session, tenant_id: uuid.UUID, *, today: date | None = None) -> None:
    """Increment the current month's bill counter (get-or-create the row)."""
    today = today or date.today()
    row = db.scalar(
        select(BillUsage).where(
            BillUsage.tenant_id == tenant_id,
            BillUsage.year == today.year,
            BillUsage.month == today.month,
        )
    )
    if row is None:
        row = BillUsage(tenant_id=tenant_id, year=today.year, month=today.month, bills_count=0)
        db.add(row)
    row.bills_count += 1


def activate(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID | None,
    status: str,
    period_start: date | None,
    period_end: date | None,
) -> TenantSubscription:
    """Manual activation/upgrade (platform ops). Writes a new subscription row
    (history preserved) and mirrors the status onto the tenant."""
    from app.core.errors import NotFoundError
    from app.models.tenant import Tenant

    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found.")
    if plan_id is not None and db.get(SubscriptionPlan, plan_id) is None:
        raise NotFoundError("Plan not found.")

    sub = TenantSubscription(
        tenant_id=tenant_id,
        plan_id=plan_id,
        status=status,
        period_start=period_start or date.today(),
        period_end=period_end,
    )
    db.add(sub)
    tenant.subscription_status = status
    db.commit()
    db.refresh(sub)
    return sub


def list_plans(db: Session) -> list[SubscriptionPlan]:
    return list(
        db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(
            SubscriptionPlan.monthly_bill_limit))
    )
