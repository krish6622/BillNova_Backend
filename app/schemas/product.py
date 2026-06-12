"""Product schemas. Products are created via purchases (no direct create);
selling price is derived from the profit margin and is read-only."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MarginType = Literal["percentage", "amount"]


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_code: str
    name: str
    unit: str
    purchase_price: float
    margin_type: str
    margin_value: float
    selling_price: float
    gst_percentage: float
    hsn_code: str | None
    current_stock: float
    reorder_level: float
    is_active: bool


class ProductUpdate(BaseModel):
    """Editable fields only. selling_price is derived (recomputed from margin),
    product_code is immutable, stock changes go through inventory."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    unit: str | None = Field(default=None, max_length=20)
    gst_percentage: float | None = Field(default=None, ge=0, le=100)
    hsn_code: str | None = Field(default=None, max_length=20)
    reorder_level: float | None = Field(default=None, ge=0)
    margin_type: MarginType | None = None
    margin_value: float | None = Field(default=None, ge=0)
    is_active: bool | None = None
