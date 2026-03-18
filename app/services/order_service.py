from fastapi import HTTPException
from datetime import datetime, timezone
from app.db.mongodb import db_manager
from uuid import uuid4


async def create_order_service(order,user:dict):

    product_collection = db_manager.db["products"]
    order_collection = db_manager.db["orders"]
    user_collection = db_manager.db["users"]

    order_items = []
    total_price = 0

    for item in order.items:

        # Look up product by barcode or productId
        if item.barcode:
            product = await product_collection.find_one({"barcode": item.barcode})
            product_identifier = item.barcode
        elif item.productId:
            product = await product_collection.find_one({"_id": item.productId})
            product_identifier = item.productId
        else:
            raise HTTPException(
                status_code=400,
                detail="Either barcode or productId must be provided for each item"
            )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_identifier} not found"
            )

        if product["stock"] < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for {product['name']}"
            )

        item_total = product["price"] * item.quantity
        total_price += item_total

        order_items.append({
                "product_id": str(product["_id"]),
                "barcode": product["barcode"],
                "name": product["name"],
                "price": product["price"],
                "quantity": item.quantity
                
        })

        await product_collection.update_one(
            {"_id": product["_id"]},
            {"$inc": {"stock": -item.quantity}}
        )

    order_data = {
        "items": order_items,
        "total_price": total_price,
        "user_id": str(user["_id"]),
        "created_at": datetime.now(timezone.utc)
    }

    result = await order_collection.insert_one(order_data)

    order_data["id"] = str(result.inserted_id)

    return order_data


async def get_orders_service(page: int = 1, limit: int = 10):

    order_collection = db_manager.db["orders"]
    
    skip_value = (page - 1) * limit

    orders = []
    
    cursor = order_collection.find().sort("created_at", -1).skip(skip_value).limit(limit)

    async for order in cursor:

        order["id"] = str(order["_id"])
        
        # Handle both user_id and employee_id fields
        if "user_id" not in order and "employee_id" in order:
            order["user_id"] = order["employee_id"]
        elif "user_id" not in order and "employee_id" not in order:
            # For legacy orders that don't have either field, provide a default
            order["user_id"] = "legacy_user"
        
        # Remove the MongoDB _id field
        del order["_id"]

        orders.append(order)
    
    return orders

# async def create_purchase_orders():
#     pass