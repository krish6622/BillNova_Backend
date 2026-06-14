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

    # Place of supply still drives the CGST+SGST vs IGST split. (CR-7 removed the
    # gst_mode_default setting — pricing is always exclusive, the CR-4 standard.)
    place_of_supply: Mapped[str] = mapped_column(String(10), default="intra")

    # Invoice header/footer settings.
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    invoice_prefix: Mapped[str] = mapped_column(String(10), default="INV")
    # CR-5: print format for the POS — thermal_80 (default) | thermal_58 | a4.
    invoice_type: Mapped[str] = mapped_column(
        String(12), nullable=False, server_default="thermal_80", default="thermal_80"
    )
    # CR-6: show the "Powered by BillNova" line on receipts (merchants may disable).
    show_branding: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True
    )
    invoice_footer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # CR-7: show_gst_on_invoice moved OFF the tenant — it is now chosen per bill and
    # stored on each sale (sales.show_gst_on_invoice).

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
