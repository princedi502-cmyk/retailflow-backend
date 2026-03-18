from pydantic import BaseModel
from typing import Optional


class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None 
    price: float
    stock: int
    barcode: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    barcode: Optional[str] = None
    
class LowStockProductResponse(BaseModel):
    name: str
    stock: int
    low_stock_threshold: Optional[int] = None


class ProductResponse(ProductBase):
    id: str 

    class Config:
        # This allows the model to work with MongoDB dictionaries
        from_attributes = True 
        populate_by_name = True