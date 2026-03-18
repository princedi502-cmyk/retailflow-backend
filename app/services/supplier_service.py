from fastapi import HTTPException
from datetime import datetime, timezone
from app.db.mongodb import db_manager
from app.schemas.supplier_schema import CreateSupplier,SupplierResponse
from uuid import uuid4
from bson import ObjectId
from bson.errors import InvalidId


collection = "suppliers"

async def create_supplier_service(supplier):
    supplier_dict = supplier.model_dump()

    existing = await db_manager.db[collection].find_one({"$or": [
        {"name": supplier.name},
        {"phone": supplier.phone},
        {"email": supplier.email}  # Fixed: was supplier.phone in your snippet
    ]})
    if existing:
        raise HTTPException(status_code=400, detail="supplier already exists")
    supplier_dict["created_at"] = datetime.now(timezone.utc)
    result = await db_manager.db[collection].insert_one(supplier_dict)

    supplier_dict["id"] = str(result.inserted_id)
    return supplier_dict

async def get_supplier_service(page: int = 1, limit: int = 10):
    supplier_collection = db_manager.db["suppliers"]
    
    skip_value = (page - 1) * limit

    suppliers = []
    
    cursor = supplier_collection.find().skip(skip_value).limit(limit)

    async for supplier in cursor:
        supplier["id"] = str(supplier.pop("_id"))

        suppliers.append(supplier)

    return suppliers

async def update_supplier_service(supplier_id,supplier):
    supplier_collection = db_manager.db["suppliers"]
    try:
        oid = ObjectId(supplier_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    updated = await supplier_collection.find_one_and_update(
        {"_id": ObjectId(supplier_id)},
        {"$set": supplier.model_dump(exclude_unset=True)},
        return_document=True
    )


    if not updated:
        raise HTTPException(status_code=404, detail="supplier  not found")

    updated["id"] = str(updated.pop("_id"))
    return updated


async def delete_supplier_service(supplier_id):
    supplier_collection = db_manager.db["suppliers"]

    result = await supplier_collection.delete_one({"_id": ObjectId(supplier_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="supplier not found")

    return {"message": "supplier deleted"}