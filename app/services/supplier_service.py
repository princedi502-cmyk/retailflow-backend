from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from app.db.mongodb import db_manager
from app.schemas.supplier_schema import (
    CreateSupplier, SupplierResponse, LowStockSupplier, ProductInfo,
    CreatePurchaseOrder, PurchaseOrderResponse, PurchaseOrderItem,
    SupplierPerformance, SupplierProductCatalog, PurchaseOrderWithSupplierResponse
)
from uuid import uuid4
from bson import ObjectId
from bson.errors import InvalidId
from typing import List, Dict, Any
from pymongo import ReturnDocument

collection = "suppliers"
purchase_orders_collection = "purchase_orders"
products_collection = "products"
inventory_collection = "inventory"

async def create_supplier_service(supplier):
    supplier_dict = supplier.model_dump()

    existing = await db_manager.db[collection].find_one({"$or": [
        {"name": supplier.name},
        {"phone": supplier.phone},
        {"email": supplier.email}
    ]})
    if existing:
        raise HTTPException(status_code=400, detail="supplier already exists")
    supplier_dict["created_at"] = datetime.now(timezone.utc)
    result = await db_manager.db[collection].insert_one(supplier_dict)

    supplier_dict["id"] = str(result.inserted_id)
    return supplier_dict

async def get_supplier_service(page: int = 1, limit: int = 10):
    supplier_collection = db_manager.db["suppliers"]
    total_count = await supplier_collection.count_documents({})
    skip_value = (page - 1) * limit

    suppliers = []

    cursor = supplier_collection.find().sort("created_at", -1).skip(skip_value).limit(limit)

    async for supplier in cursor:
        supplier["id"] = str(supplier.pop("_id"))
        suppliers.append(supplier)

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return {
        "suppliers": suppliers,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

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

async def get_low_stock_suppliers_service():
    """
    Get suppliers with products that need restocking
    """
    pipeline = [
        {
            "$lookup": {
                "from": "inventory",
                "localField": "_id",
                "foreignField": "supplier_id",
                "as": "inventory_items"
            }
        },
        {"$unwind": "$inventory_items"},
        {
            "$lookup": {
                "from": "products",
                "localField": "inventory_items.product_id",
                "foreignField": "_id",
                "as": "product"
            }
        },
        {"$unwind": "$product"},
        {
            "$match": {
                "$expr": {
                    "$and": [
                        {"$ne": ["$inventory_items.reorder_level", None]},
                        {"$lte": ["$inventory_items.current_stock", "$inventory_items.reorder_level"]}
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "name": {"$first": "$name"},
                "email": {"$first": "$email"},
                "phone": {"$first": "$phone"},
                "low_stock_products": {
                    "$push": {
                        "product_id": {"$toString": "$product._id"},
                        "product_name": "$product.name",
                        "current_stock": "$inventory_items.current_stock",
                        "reorder_level": "$inventory_items.reorder_level",
                        "unit_price": "$inventory_items.unit_price"
                    }
                }
            }
        },
        {"$match": {"low_stock_products.0": {"$exists": True}}}
    ]
    
    low_stock_suppliers = []
    cursor = db_manager.db[collection].aggregate(pipeline)
    
    async for supplier in cursor:
        supplier["id"] = str(supplier.pop("_id"))
        low_stock_suppliers.append(LowStockSupplier(**supplier))
    
    return low_stock_suppliers

async def create_purchase_order_service(supplier_id: str, purchase_order: CreatePurchaseOrder):
    """
    Create a purchase order for a supplier
    """
    try:
        ObjectId(supplier_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid supplier ID format")
    
    # Check if supplier exists
    supplier = await db_manager.db[collection].find_one({"_id": ObjectId(supplier_id)})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Calculate total amount
    total_amount = sum(item.total_price for item in purchase_order.items)
    
    # Generate order number
    order_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    order_dict = {
        "supplier_id": supplier_id,
        "order_number": order_number,
        "items": [item.model_dump() for item in purchase_order.items],
        "total_amount": total_amount,
        "status": "pending",
        "order_date": datetime.now(timezone.utc),
        "expected_delivery_date": purchase_order.expected_delivery_date,
        "notes": purchase_order.notes
    }
    
    result = await db_manager.db[purchase_orders_collection].insert_one(order_dict)
    order_dict["id"] = str(result.inserted_id)
    
    return PurchaseOrderResponse(**order_dict)

async def get_purchase_orders_service(
    page: int = 1,
    limit: int = 10,
    status: str = None,
    supplier_id: str = None
):
    """
    List purchase orders with pagination and optional filtering.
    """
    query_filter = {}

    if status:
        query_filter["status"] = status.lower()

    if supplier_id:
        try:
            ObjectId(supplier_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid supplier ID format")
        query_filter["supplier_id"] = supplier_id

    total_count = await db_manager.db[purchase_orders_collection].count_documents(query_filter)
    skip_value = (page - 1) * limit

    purchase_orders = []
    supplier_ids = set()
    cursor = (
        db_manager.db[purchase_orders_collection]
        .find(query_filter)
        .sort("order_date", -1)
        .skip(skip_value)
        .limit(limit)
    )

    async for order in cursor:
        supplier_ref = order.get("supplier_id")
        if supplier_ref:
            supplier_ids.add(supplier_ref)

        order["id"] = str(order.pop("_id"))
        order.setdefault("delivered_date", None)
        purchase_orders.append(order)

    supplier_map = {}
    valid_supplier_object_ids = [ObjectId(value) for value in supplier_ids if ObjectId.is_valid(value)]
    if valid_supplier_object_ids:
        supplier_cursor = db_manager.db[collection].find(
            {"_id": {"$in": valid_supplier_object_ids}},
            {"name": 1}
        )
        async for supplier in supplier_cursor:
            supplier_map[str(supplier["_id"])] = supplier.get("name", "Unknown Supplier")

    normalized_orders = []
    for order in purchase_orders:
        normalized_orders.append(
            PurchaseOrderWithSupplierResponse(
                **order,
                supplier_name=supplier_map.get(order.get("supplier_id"), "Unknown Supplier")
            )
        )

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return {
        "purchase_orders": normalized_orders,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

async def update_purchase_order_status_service(purchase_order_id: str, status: str):
    """
    Update purchase-order lifecycle status.
    """
    try:
        order_object_id = ObjectId(purchase_order_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid purchase order ID format")

    normalized_status = status.lower().strip()
    valid_statuses = {"pending", "processing", "shipped", "delivered", "cancelled"}
    if normalized_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}"
        )

    update_fields = {"status": normalized_status}
    if normalized_status == "delivered":
        update_fields["delivered_date"] = datetime.now(timezone.utc)

    updated = await db_manager.db[purchase_orders_collection].find_one_and_update(
        {"_id": order_object_id},
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    supplier_name = "Unknown Supplier"
    supplier_ref = updated.get("supplier_id")
    if supplier_ref and ObjectId.is_valid(supplier_ref):
        supplier = await db_manager.db[collection].find_one(
            {"_id": ObjectId(supplier_ref)},
            {"name": 1}
        )
        if supplier:
            supplier_name = supplier.get("name", supplier_name)

    updated["id"] = str(updated.pop("_id"))
    updated.setdefault("delivered_date", None)

    return PurchaseOrderWithSupplierResponse(**updated, supplier_name=supplier_name)

async def get_supplier_performance_service(supplier_id: str):
    """
    Get supplier performance metrics
    """
    try:
        ObjectId(supplier_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid supplier ID format")
    
    # Check if supplier exists
    supplier = await db_manager.db[collection].find_one({"_id": ObjectId(supplier_id)})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Get purchase orders for this supplier
    orders = []
    cursor = db_manager.db[purchase_orders_collection].find({"supplier_id": supplier_id})
    async for order in cursor:
        orders.append(order)
    
    if not orders:
        return SupplierPerformance(
            supplier_id=supplier_id,
            supplier_name=supplier["name"],
            total_orders=0,
            on_time_delivery_rate=0.0,
            average_fulfillment_time=0.0,
            product_quality_score=0.0,
            total_purchase_value=0.0,
            last_order_date=None,
            performance_trend="stable"
        )
    
    # Calculate metrics
    total_orders = len(orders)
    delivered_orders = [o for o in orders if o.get("status") == "delivered"]
    on_time_orders = [o for o in delivered_orders if 
                     o.get("delivered_date") and o.get("delivered_date") <= o.get("expected_delivery_date")]
    
    on_time_delivery_rate = len(on_time_orders) / len(delivered_orders) * 100 if delivered_orders else 0
    
    # Calculate average fulfillment time
    fulfillment_times = []
    for order in delivered_orders:
        if order.get("order_date") and order.get("delivered_date"):
            days = (order["delivered_date"] - order["order_date"]).days
            fulfillment_times.append(days)
    
    avg_fulfillment_time = sum(fulfillment_times) / len(fulfillment_times) if fulfillment_times else 0
    
    # Total purchase value
    total_purchase_value = sum(order.get("total_amount", 0) for order in orders)
    
    # Last order date
    order_dates = [o.get("order_date", datetime.min) for o in orders if o.get("order_date")]
    last_order_date = max(order_dates) if order_dates else None
    
    # Performance trend (simplified calculation)
    now_utc = datetime.now(timezone.utc)
    recent_orders = [o for o in orders if o.get("order_date") and o.get("order_date").replace(tzinfo=timezone.utc) > now_utc - timedelta(days=90)]
    older_orders = [o for o in orders if o.get("order_date") and now_utc - timedelta(days=180) <= o.get("order_date").replace(tzinfo=timezone.utc) <= now_utc - timedelta(days=90)]
    
    if len(recent_orders) > len(older_orders):
        trend = "improving"
    elif len(recent_orders) < len(older_orders):
        trend = "declining"
    else:
        trend = "stable"
    
    return SupplierPerformance(
        supplier_id=supplier_id,
        supplier_name=supplier["name"],
        total_orders=total_orders,
        on_time_delivery_rate=on_time_delivery_rate,
        average_fulfillment_time=avg_fulfillment_time,
        product_quality_score=4.0,  # Placeholder - would need quality ratings system
        total_purchase_value=total_purchase_value,
        last_order_date=last_order_date,
        performance_trend=trend
    )

async def update_supplier_product_catalog_service(supplier_id: str, products: List[SupplierProductCatalog]):
    """
    Update supplier product catalog
    """
    try:
        ObjectId(supplier_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid supplier ID format")
    
    # Check if supplier exists
    supplier = await db_manager.db[collection].find_one({"_id": ObjectId(supplier_id)})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Update supplier's product catalog
    product_updates = []
    for product in products:
        product_dict = product.model_dump()
        product_dict["supplier_id"] = supplier_id
        product_dict["updated_at"] = datetime.now(timezone.utc)
        
        # Upsert product in supplier catalog
        await db_manager.db["supplier_products"].update_one(
            {"supplier_id": supplier_id, "product_id": product.product_id},
            {"$set": product_dict},
            upsert=True
        )
        product_updates.append(product_dict)
    
    return {"message": f"Updated {len(product_updates)} products in supplier catalog", "products": product_updates}
