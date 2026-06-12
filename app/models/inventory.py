"""InventoryTransaction model — append-only stock ledger (IN/OUT/ADJUST)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

TXN_IN = "IN"
TXN_OUT = "OUT"
TXN_ADJUST = "ADJUST"

REF_SALE = "SALE"
REF_PURCHASE = "PURCHASE"
REF_ADJUSTMENT = "ADJUSTMENT"


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(10))  # IN | OUT | ADJUST
    quantity: Mapped[float] = mapped_column(Numeric(12, 3))  # signed: +in / -out
    balance_after: Mapped[float] = mapped_column(Numeric(12, 3))
    ref_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
