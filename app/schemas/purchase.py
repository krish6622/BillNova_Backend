"""Purchase schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PurchaseItemInput(BaseModel):
    product_id: uuid.UUID
    quantity: float = Field(gt=0)
    purchase_price: float = Field(ge=0)
    gst_percentage: float = Field(default=0, ge=0, le=100)


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
