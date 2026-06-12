"""Product schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    product_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(default="PCS", max_length=20)
    purchase_price: float = Field(default=0, ge=0)
    selling_price: float = Field(default=0, ge=0)
    gst_percentage: float = Field(default=0, ge=0, le=100)
    hsn_code: str | None = Field(default=None, max_length=20)
    current_stock: float = Field(default=0)
    reorder_level: float = Field(default=0, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=20)
    purchase_price: float | None = Field(default=None, ge=0)
    selling_price: float | None = Field(default=None, ge=0)
    gst_percentage: float | None = Field(default=None, ge=0, le=100)
    hsn_code: str | None = Field(default=None, max_length=20)
    current_stock: float | None = None
    reorder_level: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool
