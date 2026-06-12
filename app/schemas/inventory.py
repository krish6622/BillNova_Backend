"""Inventory schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StockItem(BaseModel):
    product_id: uuid.UUID
    product_code: str
    name: str
    unit: str
    current_stock: float
    reorder_level: float
    purchase_price: float
    stock_value: float


class LedgerEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: str
    quantity: float
    balance_after: float
    ref_type: str | None
    ref_id: uuid.UUID | None
    reason: str | None
    created_at: datetime


class AdjustmentRequest(BaseModel):
    product_id: uuid.UUID
    delta: float = Field(description="Signed quantity change; may be negative.")
    reason: str = Field(min_length=1, max_length=255)
