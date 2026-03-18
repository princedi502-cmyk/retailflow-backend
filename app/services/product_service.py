from bson import ObjectId
from fastapi import HTTPException

from app.db.mongodb import db_manager
from app.schemas.product_schema import ProductCreate, ProductUpdate


collection = "products"


async def create_product(product: ProductCreate):
    product_dict = product.model_dump()

    existing = await db_manager.db[collection].find_one({"barcode": product.barcode})
    if existing:
        raise HTTPException(status_code=400, detail="Product with this barcode already exists")

    result = await db_manager.db[collection].insert_one(product_dict)

    product_dict["_id"] = str(result.inserted_id)
    return product_dict


async def get_all_products():
    products = []
    cursor = db_manager.db[collection].find()

    async for product in cursor:
        product["_id"] = str(product["_id"])
        products.append(product)

    return products


async def get_product_by_id(product_id: str):
    product = await db_manager.db[collection].find_one({"_id": ObjectId(product_id)})

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product["_id"] = str(product["_id"])
    return product


async def find_product_by_barcode(barcode: str):
    product = await db_manager.db[collection].find_one({"barcode": barcode})

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product["_id"] = str(product["_id"])
    return product


async def update_product(product_id: str, product: ProductUpdate):

    update_data = {k: v for k, v in product.model_dump().items() if v is not None}

    result = await db_manager.db[collection].update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Product not updated")

    return {"message": "Product updated successfully"}


async def delete_product(product_id: str):

    result = await db_manager.db[collection].delete_one(
        {"_id": ObjectId(product_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted successfully"}