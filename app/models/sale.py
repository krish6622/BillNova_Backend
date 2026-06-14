"""Sale and SaleItem models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# CR-5: invoice lifecycle. A voided invoice is retained (audit) but reverses its stock
# and is excluded from sales reports/dashboard/usage.
STATUS_ACTIVE = "active"
STATUS_VOID = "void"

# GST billing workflow: billing type is chosen PER BILL at checkout.
#   WITH_GST    — product GST applied normally (counts toward GSTR/HSN).
#   WITHOUT_GST — a non-GST sale: GST forced to 0, excluded from GST reports.
BILLING_WITH_GST = "WITH_GST"
BILLING_WITHOUT_GST = "WITHOUT_GST"


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_sale_invoice_tenant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(40))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    # CR-5: optional walk-in customer name captured at the POS (defaults to "Walk-in").
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # GST billing workflow: B2B "GST customer" details captured at the POS.
    is_gst_customer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    customer_mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    # GST billing workflow: WITH_GST | WITHOUT_GST, frozen per bill. Existing rows
    # (created before this column) backfill to WITH_GST so history stays GST-taxed.
    billing_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=BILLING_WITH_GST, default=BILLING_WITH_GST
    )

    gst_mode: Mapped[str] = mapped_column(String(10))  # inclusive | exclusive
    place_of_supply: Mapped[str] = mapped_column(String(10))  # intra | inter
    # CR-5: active | void. Voided sales keep their rows but stop counting everywhere.
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=STATUS_ACTIVE, default=STATUS_ACTIVE
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # CR-7: GST display is chosen PER BILL at checkout (default Hide) and frozen here, so
    # reprints always match the original — never the live application settings.
    show_gst_on_invoice: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )

    total_taxable: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_cgst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_sgst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_igst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_gst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    grand_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["SaleItem"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821 — resolved via registry
        cascade="all, delete-orphan", lazy="selectin"
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    sale_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sales.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"))

    product_name: Mapped[str] = mapped_column(String(255))  # snapshot
    hsn_code: Mapped[str | None] = mapped_column(String(20), nullable=True)  # snapshot
    unit: Mapped[str] = mapped_column(String(20), nullable=False, server_default="NOS")  # snapshot (CR-3)

    quantity: Mapped[float] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    gst_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    taxable_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    cgst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    sgst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    igst: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
