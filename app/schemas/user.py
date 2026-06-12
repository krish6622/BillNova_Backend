"""User management schemas (Owner-only operations)."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import ROLE_CASHIER, ROLE_OWNER


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = ROLE_CASHIER

    def normalized_role(self) -> str:
        return self.role if self.role in {ROLE_OWNER, ROLE_CASHIER} else ROLE_CASHIER


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    is_active: bool
