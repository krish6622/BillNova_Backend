"""Billing / POS schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.gstin import is_valid_gstin, normalize_gstin

BillingType = Literal["WITH_GST", "WITHOUT_GST"]


class SaleItemInput(BaseModel):
    product_id: uuid.UUID
    quantity: float = Field(gt=0)
    discount: float = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class PaymentInput(BaseModel):
    mode: Literal["Cash", "UPI", "Card"]
    amount: float = Field(gt=0)
    reference: str | None = Field(default=None, max_length=100)


class SalePreviewRequest(BaseModel):
    gst_mode: Literal["inclusive", "exclusive"] | None = None
    place_of_supply: Literal["intra", "inter"] | None = None
    items: list[SaleItemInput] = Field(min_length=1)
    bill_discount: float = Field(default=0, ge=0)
    # GST billing workflow: WITH_GST applies product GST; WITHOUT_GST is a non-GST sale.
    # Backend default is WITH_GST so pre-existing/omitting clients keep GST behaviour
    # (the POS UI defaults its radio to WITHOUT_GST and always sends an explicit value).
    billing_type: BillingType = "WITH_GST"


class SaleCreate(SalePreviewRequest):
    notes: str | None = Field(default=None, max_length=500)
    customer_name: str | None = Field(default=None, max_length=255)
    # GST billing workflow: B2B GST-customer details (GSTIN mandatory when flagged).
    is_gst_customer: bool = False
    customer_mobile: str | None = Field(default=None, max_length=20)
    customer_gstin: str | None = Field(default=None, max_length=15)
    # CR-7: GST display chosen for THIS bill (default Hide). Frozen on the sale.
    show_gst_on_invoice: bool = False
    payments: list[PaymentInput] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_gst_customer(self) -> "SaleCreate":
        if self.is_gst_customer:
            if not (self.customer_name and self.customer_name.strip()):
                raise ValueError("Customer name is required for a GST customer.")
            if not self.customer_gstin or not is_valid_gstin(self.customer_gstin):
                raise ValueError("A valid 15-character GSTIN is required for a GST customer.")
            self.customer_gstin = normalize_gstin(self.customer_gstin)
        else:
            # A non-GST (regular) customer never carries a GSTIN.
            self.customer_gstin = None
        return self


class LineComputedOut(BaseModel):
    product_id: uuid.UUID
    product_name: str
    hsn_code: str | None
    quantity: float
    unit_price: float
    gst_percentage: float
    discount: float
    taxable_value: float
    cgst: float
    sgst: float
    igst: float
    line_total: float


class TotalsOut(BaseModel):
    total_taxable: float
    total_discount: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    total_gst: float
    grand_total: float


class SalePreviewOut(BaseModel):
    gst_mode: str
    place_of_supply: str
    billing_type: str
    items: list[LineComputedOut]
    totals: TotalsOut


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mode: str
    amount: float
    reference: str | None


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: uuid.UUID
    product_name: str
    hsn_code: str | None
    unit: str
    quantity: float
    unit_price: float
    discount: float
    gst_percentage: float
    taxable_value: float
    cgst: float
    sgst: float
    igst: float
    line_total: float
    notes: str | None


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_number: str
    gst_mode: str
    place_of_supply: str
    status: str
    customer_name: str | None
    is_gst_customer: bool
    customer_mobile: str | None
    customer_gstin: str | None
    billing_type: str
    cashier_name: str | None = None
    show_gst_on_invoice: bool
    total_taxable: float
    total_discount: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    total_gst: float
    grand_total: float
    notes: str | None
    created_at: datetime
    voided_at: datetime | None
    items: list[SaleItemOut]
    payments: list[PaymentOut]


class SaleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_number: str
    grand_total: float
    created_at: datetime


class InvoiceListItem(BaseModel):
    """One row in the Invoice Register — enriched with cashier + payment + status."""
    id: uuid.UUID
    invoice_number: str
    created_at: datetime
    customer_name: str | None
    is_gst_customer: bool
    customer_gstin: str | None
    billing_type: str
    grand_total: float
    payment_modes: list[str]
    cashier_name: str | None
    show_gst_on_invoice: bool
    status: str


class InvoiceBusiness(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_name: str
    gst_number: str | None
    mobile: str
    email: str
    address: str | None
    invoice_footer: str | None
    # CR-5: thermal_80 | thermal_58 | a4 — selects the print format on the POS.
    invoice_type: str
    # CR-6: footer "Powered by BillNova" toggle.
    show_branding: bool
    # CR-7: show_gst_on_invoice moved to the SALE (per bill), not the business.


class InvoiceOut(BaseModel):
    business: InvoiceBusiness
    sale: SaleOut
