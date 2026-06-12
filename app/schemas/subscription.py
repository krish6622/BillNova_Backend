"""Subscription / usage schemas."""

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    monthly_bill_limit: int
    price_inr: float


class UsageOut(BaseModel):
    year: int
    month: int
    bills_count: int
    percent: float


class SubscriptionOut(BaseModel):
    plan: str | None
    status: str
    monthly_bill_limit: int
    usage: UsageOut
    warning: str | None  # None | "APPROACHING_LIMIT" | "LIMIT_REACHED"
    period_end: str | None


class ActivateRequest(BaseModel):
    tenant_id: uuid.UUID
    plan_id: uuid.UUID | None = None
    status: Literal["Trial", "Active", "Expired", "Suspended"]
    period_start: date | None = None
    period_end: date | None = None
