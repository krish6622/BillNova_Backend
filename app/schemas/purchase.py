"""Purchase schemas. A purchase line is either an existing product (product_id)
or a new product created inline (product_name + pricing)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MarginType = Literal["percentage", "amount"]


class PurchaseItemInput(BaseModel):
    # Existing product:
    product_id: uuid.UUID | None = None
    # New product (created inline) — product_name required when product_id is absent:
    product_code: str | None = Field(default=None, max_length=50)
    product_name: str | None = Field(default=None, max_length=255)
    hsn_code: str | None = Field(default=None, max_length=20)
    gst_percentage: float = Field(default=0, ge=0, le=100)
    unit: str = Field(default="NOS", max_length=20)
    # Pricing (drives the derived selling price):
    purchase_price: float = Field(gt=0)
    margin_type: MarginType = "percentage"
    margin_value: float = Field(default=0, ge=0)
    quantity: float = Field(gt=0)

    @model_validator(mode="after")
    def _require_name_for_new(self):
        if self.product_id is None and not (self.product_name and self.product_name.strip()):
            raise ValueError("product_name is required when creating a new product")
        return self


class PurchaseCreate(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_id: uuid.UUID | None = None
    purchase_date: date
    items: list[PurchaseItemInput] = Field(min_length=1)


class PurchaseItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: uuid.UUID
    product_name: str
    quantity: float
    purchase_price: float
    gst_percentage: float
    gst_amount: float
    line_total: float


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supplier_name: str
    purchase_date: date
    total_amount: float
    total_gst: float
    status: str
    created_at: datetime
    items: list[PurchaseItemOut]


class PurchaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supplier_name: str
    purchase_date: date
    total_amount: float
    status: str
