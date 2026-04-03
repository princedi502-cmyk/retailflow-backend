from typing import Optional
from datetime import datetime


class ShopSettings:
    """
    Model representing shop/business settings configurable by owner.
    Used for bill generation branding.
    """
    def __init__(
        self,
        owner_id: str,
        business_name: str = "My Shop",
        address: Optional[str] = None,
        gst_number: Optional[str] = None,
        terms_conditions: Optional[str] = None,
        greeting_message: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self.id = str(_id) if _id else None
        self.owner_id = owner_id
        self.business_name = business_name
        self.address = address
        self.gst_number = gst_number
        self.terms_conditions = terms_conditions
        self.greeting_message = greeting_message
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage."""
        return {
            "owner_id": self.owner_id,
            "business_name": self.business_name,
            "address": self.address,
            "gst_number": self.gst_number,
            "terms_conditions": self.terms_conditions,
            "greeting_message": self.greeting_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShopSettings":
        """Create ShopSettings from MongoDB document."""
        return cls(
            _id=data.get("_id"),
            owner_id=data.get("owner_id"),
            business_name=data.get("business_name", "My Shop"),
            address=data.get("address"),
            gst_number=data.get("gst_number"),
            terms_conditions=data.get("terms_conditions"),
            greeting_message=data.get("greeting_message"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
