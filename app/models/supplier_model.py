from datetime import datetime

from pydantic import BaseModel,Field,EmailStr
from typing import Optional
from bson import ObjectId

class SupplierData(BaseModel):
    id: Optional[str] = Field(alias="_id")
    name: str
    phone: str
    email: EmailStr
    address: str
    created_at: datetime
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

