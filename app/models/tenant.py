"""Tenant model — one row per business (top of the multi-tenant hierarchy)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str] = mapped_column(String(255))
    owner_name: Mapped[str] = mapped_column(String(255))
    mobile: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    gst_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Mirrors the active subscription's status for cheap reads.
    subscription_status: Mapped[str] = mapped_column(String(20), default="Trial")

    # GST defaults used by the POS (overridable per sale).
    place_of_supply: Mapped[str] = mapped_column(String(10), default="intra")
    gst_mode_default: Mapped[str] = mapped_column(String(10), default="inclusive")

    # Invoice header/footer settings.
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    invoice_prefix: Mapped[str] = mapped_column(String(10), default="INV")
    invoice_footer: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
