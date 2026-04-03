from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Customer full name")
    email: Optional[str] = Field(default=None, description="Valid email address (optional)")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number with country code")
    address: Optional[str] = Field(default=None, max_length=200, description="Street address")
    city: Optional[str] = Field(default=None, max_length=50, description="City name")
    state: Optional[str] = Field(default=None, max_length=50, description="State or province")
    postal_code: Optional[str] = Field(default=None, max_length=20, description="Postal or ZIP code")
    country: Optional[str] = Field(default=None, max_length=50, description="Country name")
    is_active: bool = Field(default=True, description="Whether the customer account is active")


class CustomerCreate(BaseModel):
    """
    Schema for creating a new customer - simplified version matching frontend
    """
    name: str = Field(..., min_length=1, max_length=100, description="Customer full name")
    email: Optional[EmailStr] = Field(None, description="Valid email address (optional)")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number with country code")

    class Config:
        extra = 'allow'
class CustomerUpdate(BaseModel):
    """
    Schema for updating customer information
    All fields are optional
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = Field(None, description="Valid email address")
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    address: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """
    Schema for customer response with additional fields
    """
    id: str
    created_at: datetime
    updated_at: datetime
    total_orders: int = 0
    total_spent: float = 0.0

    @validator('email', pre=True, always=True)
    def validate_email(cls, v):
        if v is None or v == "":
            return None
        return v

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """
    Schema for paginated customer list response
    """
    customers: List[CustomerResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int


class CustomerSearchResponse(BaseModel):
    """
    Schema for customer search response
    """
    customers: List[CustomerResponse]
    total_count: int


class CustomerOrderItem(BaseModel):
    """
    Schema for items in customer order history
    """
    product_id: str
    product_name: str
    quantity: int
    price: float
    total: float


class CustomerOrder(BaseModel):
    """
    Schema for customer order in order history
    """
    id: str
    created_at: datetime
    total_price: float
    status: str
    items: List[CustomerOrderItem]


class CustomerOrderHistoryResponse(BaseModel):
    """
    Schema for customer order history response
    """
    customer_id: str
    orders: List[CustomerOrder]
    total_orders: int
    total_spent: float
