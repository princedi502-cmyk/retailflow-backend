from app.db.mongodb import db_manager
from app.models.shop_settings_model import ShopSettings
from bson import ObjectId
from datetime import datetime
from typing import Optional


async def get_shop_settings_by_owner(owner_id: str) -> Optional[ShopSettings]:
    """Get shop settings by owner ID."""
    collection = db_manager.db["shop_settings"]
    
    # Handle both string and ObjectId owner_id
    query = {"owner_id": owner_id}
    try:
        object_id = ObjectId(owner_id)
        query = {"$or": [{"owner_id": owner_id}, {"owner_id": str(object_id)}]}
    except:
        pass
    
    doc = await collection.find_one(query)
    
    if doc:
        return ShopSettings.from_dict(doc)
    return None


async def create_default_shop_settings(owner_id: str) -> ShopSettings:
    """Create default shop settings for owner."""
    collection = db_manager.db["shop_settings"]
    
    now = datetime.utcnow()
    settings_data = {
        "owner_id": owner_id,
        "business_name": "My Shop",
        "address": None,
        "gst_number": None,
        "terms_conditions": "Thank you for your business!",
        "greeting_message": "Welcome!",
        "created_at": now,
        "updated_at": now
    }
    
    result = await collection.insert_one(settings_data)
    settings_data["_id"] = result.inserted_id
    
    return ShopSettings.from_dict(settings_data)


async def update_shop_settings(data: dict, owner_id: str) -> ShopSettings:
    """Update shop settings for owner. Creates default if doesn't exist."""
    collection = db_manager.db["shop_settings"]
    
    # Check if settings exist
    existing = await get_shop_settings_by_owner(owner_id)
    if not existing:
        # Create default settings first
        existing = await create_default_shop_settings(owner_id)
    
    # Build update data (exclude None values)
    update_data = {}
    for field in ["business_name", "address", "gst_number", "terms_conditions", "greeting_message"]:
        if field in data and data[field] is not None:
            update_data[field] = data[field]
    
    update_data["updated_at"] = datetime.utcnow()
    
    # Handle both string and ObjectId owner_id
    query = {"owner_id": owner_id}
    try:
        object_id = ObjectId(owner_id)
        query = {"$or": [{"owner_id": owner_id}, {"owner_id": str(object_id)}]}
    except:
        pass
    
    await collection.update_one(query, {"$set": update_data})
    
    # Return updated settings
    return await get_shop_settings_by_owner(owner_id)


async def get_or_create_shop_settings(owner_id: str) -> ShopSettings:
    """Get existing settings or create default ones."""
    existing = await get_shop_settings_by_owner(owner_id)
    if existing:
        return existing
    return await create_default_shop_settings(owner_id)
