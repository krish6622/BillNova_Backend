"""Product model — tenant-scoped catalog item."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_code", name="uq_product_code_tenant"),
        Index("ix_products_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    product_code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255), index=True)
    unit: Mapped[str] = mapped_column(String(20), default="NOS")
    purchase_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    # selling_price is stored but DERIVED from purchase_price + margin (never client-set).
    margin_type: Mapped[str] = mapped_column(String(10), default="percentage")  # percentage | amount
    margin_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    gst_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    hsn_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    current_stock: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    reorder_level: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
