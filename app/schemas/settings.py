"""Business settings schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_name: str
    owner_name: str
    mobile: str
    email: str
    gst_number: str | None
    address: str | None
    place_of_supply: str
    invoice_prefix: str
    invoice_footer: str | None
    # CR-5: POS print format.
    invoice_type: str
    # CR-6: footer branding toggle.
    show_branding: bool
    # CR-7: gst_mode_default and show_gst_on_invoice are GONE — pricing is always
    # exclusive and GST display is chosen per bill at checkout.


class SettingsUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=255)
    owner_name: str | None = Field(default=None, min_length=1, max_length=255)
    mobile: str | None = Field(default=None, max_length=20)
    gst_number: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    place_of_supply: Literal["intra", "inter"] | None = None
    invoice_prefix: str | None = Field(default=None, min_length=1, max_length=10)
    invoice_footer: str | None = Field(default=None, max_length=500)
    # CR-5: POS print format.
    invoice_type: Literal["thermal_80", "thermal_58", "a4"] | None = None
    # CR-6: footer branding toggle.
    show_branding: bool | None = None
