from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    email: EmailStr  
    address: Optional[str] = None

class CreateSupplier(SupplierBase):
    pass

class SupplierResponse(SupplierBase):
    id: str  
    created_at: datetime 

    class Config:
        from_attributes = True 

class ProductInfo(BaseModel):
    product_id: str
    product_name: str
    current_stock: int
    reorder_level: int
    unit_price: float

class LowStockSupplier(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str]
    low_stock_products: List[ProductInfo]

class PurchaseOrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class CreatePurchaseOrder(BaseModel):
    items: List[PurchaseOrderItem]
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None

class PurchaseOrderResponse(BaseModel):
    id: str
    supplier_id: Optional[str] = None
    order_number: Optional[str] = None
    items: List[PurchaseOrderItem] = []
    total_amount: Optional[float] = 0.0
    status: Optional[str] = "pending"
    order_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None
    delivered_date: Optional[datetime] = None

class PurchaseOrderWithSupplierResponse(PurchaseOrderResponse):
    supplier_name: Optional[str] = None

class PurchaseOrderStatusUpdate(BaseModel):
    status: str

class PurchaseOrderListResponse(BaseModel):
    purchase_orders: List[PurchaseOrderWithSupplierResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int

class SupplierPerformance(BaseModel):
    supplier_id: str
    supplier_name: str
    total_orders: int
    on_time_delivery_rate: float
    average_fulfillment_time: float  # in days
    product_quality_score: float  # 1-5 rating
    total_purchase_value: float
    last_order_date: Optional[datetime]
    performance_trend: str  # "improving", "declining", "stable"

class SupplierProductCatalog(BaseModel):
    product_id: str
    product_name: str
    description: Optional[str]
    unit_price: float
    min_order_quantity: int
    lead_time_days: int
    is_active: bool = True 
