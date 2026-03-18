from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

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

