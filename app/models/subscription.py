"""Subscription models — reference plans and per-tenant subscription state."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Statuses
STATUS_TRIAL = "Trial"
STATUS_ACTIVE = "Active"
STATUS_EXPIRED = "Expired"
STATUS_SUSPENDED = "Suspended"
ALLOWED_STATUSES = {STATUS_TRIAL, STATUS_ACTIVE, STATUS_EXPIRED, STATUS_SUSPENDED}


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True)  # Starter|Standard|Professional
    monthly_bill_limit: Mapped[int] = mapped_column(Integer)
    price_inr: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    # Null while on a pure trial (no paid plan selected yet).
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("subscription_plans.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default=STATUS_TRIAL)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
