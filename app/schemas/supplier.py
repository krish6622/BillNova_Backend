"""Supplier schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mobile: str | None = Field(default=None, max_length=20)
    gst_number: str | None = Field(default=None, max_length=20)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    mobile: str | None = Field(default=None, max_length=20)
    gst_number: str | None = Field(default=None, max_length=20)


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    mobile: str | None
    gst_number: str | None
