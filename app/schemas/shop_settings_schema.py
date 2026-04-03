from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ShopSettingsBase(BaseModel):
    """Base schema for shop settings."""
    business_name: str = Field(default="My Shop", min_length=1, max_length=100, description="Business/Shop name")
    address: Optional[str] = Field(default=None, max_length=300, description="Shop address for bills")
    gst_number: Optional[str] = Field(default=None, max_length=50, description="GST/Tax registration number")
    terms_conditions: Optional[str] = Field(default=None, max_length=500, description="Terms and conditions for bills")
    greeting_message: Optional[str] = Field(default=None, max_length=200, description="Seasonal greeting message for bills")


class ShopSettingsUpdate(BaseModel):
    """Schema for updating shop settings (all fields optional)."""
    model_config = ConfigDict(extra='allow')
    
    business_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    address: Optional[str] = Field(default=None, max_length=300)
    gst_number: Optional[str] = Field(default=None, max_length=50)
    terms_conditions: Optional[str] = Field(default=None, max_length=500)
    greeting_message: Optional[str] = Field(default=None, max_length=200)


class ShopSettingsResponse(ShopSettingsBase):
    """Schema for shop settings response."""
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
