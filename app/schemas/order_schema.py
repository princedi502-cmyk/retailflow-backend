from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OrderItem(BaseModel):
    barcode: Optional[str] = None
    productId: Optional[str] = None
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItem]
    discount: Optional[float] = None  # Discount percentage (0-100), None means no discount
    payment_method: str  # Payment method: "cash", "card", or "upi"
    customer_id: Optional[str] = None  # Optional linked customer (MongoDB ObjectId string)

class OrderItemResponse(BaseModel):
    product_id: str
    barcode: Optional[str] = None
    name: str
    price: float
    quantity: int


class OrderResponse(BaseModel):
    id: str
    user_id: str  
    customer_id: Optional[str] = None
    items: List[OrderItemResponse]
    total_price: float
    discount: Optional[float] = None  # Discount percentage applied
    payment_method: Optional[str] = None  # Payment method used
    created_at: datetime
    # Bill generation fields
    bill_sent: Optional[bool] = None
    bill_sent_at: Optional[datetime] = None
    bill_pdf_path: Optional[str] = None
    whatsapp_status: Optional[str] = None  # Success/failure message

    class Config:
        from_attributes = True
