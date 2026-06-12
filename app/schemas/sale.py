"""Billing / POS schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class SaleCreate(SalePreviewRequest):
    notes: str | None = Field(default=None, max_length=500)
    payments: list[PaymentInput] = Field(min_length=1)


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
    total_taxable: float
    total_discount: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    total_gst: float
    grand_total: float
    notes: str | None
    created_at: datetime
    items: list[SaleItemOut]
    payments: list[PaymentOut]


class SaleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_number: str
    grand_total: float
    created_at: datetime


class InvoiceBusiness(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_name: str
    gst_number: str | None
    mobile: str
    email: str


class InvoiceOut(BaseModel):
    business: InvoiceBusiness
    sale: SaleOut
