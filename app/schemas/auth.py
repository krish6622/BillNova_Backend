"""Auth request/response schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    owner_name: str = Field(min_length=1, max_length=255)
    mobile: str = Field(min_length=5, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    gst_number: str | None = Field(default=None, max_length=20)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str


class TenantPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    business_name: str
    subscription_status: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenPair):
    user: UserPublic
    tenant: TenantPublic


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user: UserPublic
    tenant: TenantPublic
