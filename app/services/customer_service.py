from fastapi import HTTPException
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.db.mongodb import db_manager
from bson import ObjectId
import re


async def create_customer_service(customer_data: dict) -> dict:
    """
    Create a new customer in the database
    """
    customer_collection = db_manager.db["customers"]
    
    # Check if customer with same email already exists (only if email provided)
    email = customer_data.get("email")
    if email:
        existing_customer = await customer_collection.find_one({"email": email})
        if existing_customer:
            raise HTTPException(
                status_code=400,
                detail="Customer with this email already exists"
            )
    
    # Check if customer with same phone already exists
    phone = customer_data.get("phone")
    if phone:
        existing_phone = await customer_collection.find_one({"phone": phone})
        if existing_phone:
            raise HTTPException(
                status_code=400,
                detail="Customer with this phone number already exists"
            )
    
    # Prepare customer document with default values for optional fields
    customer_doc = {
        **customer_data,
        "address": customer_data.get("address") or None,
        "city": customer_data.get("city") or None, 
        "state": customer_data.get("state") or None,
        "postal_code": customer_data.get("postal_code") or None,
        "country": customer_data.get("country") or None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "total_orders": 0,
        "total_spent": 0.0
    }
    
    # Remove email key if it's None/empty to avoid validation issues
    if not customer_doc.get("email"):
        customer_doc.pop("email", None)
    
    # Insert customer
    result = await customer_collection.insert_one(customer_doc)
    
    # Return the created customer with ID
    customer_doc["id"] = str(result.inserted_id)
    del customer_doc["_id"]
    
    # Ensure email field exists (even if None) for response validation
    if "email" not in customer_doc:
        customer_doc["email"] = None
    
    return customer_doc


async def get_customers_service(page: int = 1, limit: int = 10, is_active: Optional[bool] = None) -> dict:
    """
    Get all customers with pagination
    """
    customer_collection = db_manager.db["customers"]
    
    # Build query filter
    query_filter = {}
    if is_active is not None:
        query_filter["is_active"] = is_active
    
    # Get total count
    total_count = await customer_collection.count_documents(query_filter)
    
    # Calculate pagination
    skip = (page - 1) * limit
    total_pages = (total_count + limit - 1) // limit
    
    # Get customers with pagination
    customers = []
    cursor = customer_collection.find(query_filter).sort("created_at", -1).skip(skip).limit(limit)
    
    async for customer in cursor:
        customer["id"] = str(customer["_id"])
        del customer["_id"]
        customers.append(customer)
    
    return {
        "customers": customers,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


async def get_customer_by_id_service(customer_id: str) -> dict:
    """
    Get customer by ID
    """
    customer_collection = db_manager.db["customers"]
    
    try:
        object_id = ObjectId(customer_id)
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid customer ID format"
        )
    
    customer = await customer_collection.find_one({"_id": object_id})
    
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    
    customer["id"] = str(customer["_id"])
    del customer["_id"]
    
    return customer


async def update_customer_service(customer_id: str, update_data: dict) -> dict:
    """
    Update customer information
    """
    customer_collection = db_manager.db["customers"]
    
    try:
        object_id = ObjectId(customer_id)
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid customer ID format"
        )
    
    # Check if customer exists
    existing_customer = await customer_collection.find_one({"_id": object_id})
    if not existing_customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    
    # Check for duplicate email if updating email
    if "email" in update_data and update_data["email"] != existing_customer["email"]:
        email_exists = await customer_collection.find_one({
            "email": update_data["email"],
            "_id": {"$ne": object_id}
        })
        if email_exists:
            raise HTTPException(
                status_code=400,
                detail="Email already exists for another customer"
            )
    
    # Check for duplicate phone if updating phone
    if "phone" in update_data and update_data["phone"] != existing_customer["phone"]:
        phone_exists = await customer_collection.find_one({
            "phone": update_data["phone"],
            "_id": {"$ne": object_id}
        })
        if phone_exists:
            raise HTTPException(
                status_code=400,
                detail="Phone number already exists for another customer"
            )
    
    # Prepare update data
    update_doc = {
        "$set": {
            **update_data,
            "updated_at": datetime.now(timezone.utc)
        }
    }
    
    # Update customer
    await customer_collection.update_one({"_id": object_id}, update_doc)
    
    # Get updated customer
    updated_customer = await customer_collection.find_one({"_id": object_id})
    updated_customer["id"] = str(updated_customer["_id"])
    del updated_customer["_id"]
    
    return updated_customer


async def delete_customer_service(customer_id: str) -> dict:
    """
    Delete customer (soft delete by setting is_active to False)
    """
    customer_collection = db_manager.db["customers"]
    
    try:
        object_id = ObjectId(customer_id)
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid customer ID format"
        )
    
    # Check if customer exists
    customer = await customer_collection.find_one({"_id": object_id})
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    
    # Soft delete by setting is_active to False
    await customer_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "is_active": False,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {"message": "Customer deleted successfully"}


async def search_customers_service(search_query: str, page: int = 1, limit: int = 10) -> dict:
    """
    Search customers by name, email, or phone
    """
    customer_collection = db_manager.db["customers"]
    
    # Create search regex pattern (case-insensitive)
    search_pattern = re.compile(search_query, re.IGNORECASE)
    
    # Build search query
    query_filter = {
        "$or": [
            {"name": {"$regex": search_pattern}},
            {"email": {"$regex": search_pattern}},
            {"phone": {"$regex": search_pattern}}
        ]
    }
    
    # Get total count
    total_count = await customer_collection.count_documents(query_filter)
    
    # Calculate pagination
    skip = (page - 1) * limit
    
    # Search customers
    customers = []
    cursor = customer_collection.find(query_filter).sort("created_at", -1).skip(skip).limit(limit)
    
    async for customer in cursor:
        customer["id"] = str(customer["_id"])
        del customer["_id"]
        customers.append(customer)
    
    return {
        "customers": customers,
        "total_count": total_count
    }


async def get_customer_orders_service(customer_id: str, page: int = 1, limit: int = 10) -> dict:
    """
    Get customer order history
    """
    customer_collection = db_manager.db["customers"]
    order_collection = db_manager.db["orders"]
    
    try:
        object_id = ObjectId(customer_id)
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid customer ID format"
        )
    
    # Check if customer exists
    customer = await customer_collection.find_one({"_id": object_id})
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    
    # Get customer orders using explicit customer linkage
    query_filter = {
        "$or": [
            {"customer_id": customer_id},
            {"customer_id": object_id}
        ]
    }
    total_count = await order_collection.count_documents(query_filter)
    
    # Calculate pagination
    skip = (page - 1) * limit
    
    # Get orders
    orders = []
    cursor = order_collection.find(query_filter).sort("created_at", -1).skip(skip).limit(limit)
    
    async for order in cursor:
        order["id"] = str(order["_id"])
        del order["_id"]
        order["status"] = order.get("status", "completed")
        order["total_price"] = float(order.get("total_price", 0) or 0)

        normalized_items = []
        for item in order.get("items", []):
            quantity = int(item.get("quantity", 0) or 0)
            price = float(item.get("price", 0) or 0)
            normalized_items.append({
                "product_id": str(item.get("product_id", "")),
                "product_name": item.get("product_name") or item.get("name") or "Product",
                "quantity": quantity,
                "price": price,
                "total": float(item.get("total", item.get("total_price", price * quantity)) or 0)
            })

        order["items"] = normalized_items
        orders.append(order)

    # Calculate total spent across all matched orders (not just paginated result)
    spending_pipeline = [
        {"$match": query_filter},
        {
            "$group": {
                "_id": None,
                "total_spent": {"$sum": {"$ifNull": ["$total_price", 0]}}
            }
        }
    ]
    spending_result = await order_collection.aggregate(spending_pipeline).to_list(length=1)
    total_spent = spending_result[0]["total_spent"] if spending_result else 0.0
    
    # Update customer's total orders and total spent
    await customer_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "total_orders": total_count,
                "total_spent": total_spent,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {
        "customer_id": customer_id,
        "orders": orders,
        "total_orders": total_count,
        "total_spent": total_spent
    }
