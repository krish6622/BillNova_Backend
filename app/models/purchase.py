"""Purchase and PurchaseItem models."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

STATUS_ACTIVE = "active"
STATUS_CANCELLED = "cancelled"


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("suppliers.id"), nullable=True
    )
    supplier_name: Mapped[str] = mapped_column(String(255))
    # CR-7: supplier's invoice/bill number and free-text notes for the purchase header.
    invoice_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    purchase_date: Mapped[date] = mapped_column(Date)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_gst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(10), default=STATUS_ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["PurchaseItem"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("purchases.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(12, 3))
    purchase_price: Mapped[float] = mapped_column(Numeric(12, 2))
    gst_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    gst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
