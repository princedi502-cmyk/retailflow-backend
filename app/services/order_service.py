from fastapi import HTTPException
from datetime import datetime, timezone
from typing import Optional
from app.db.mongodb import db_manager
from uuid import uuid4
from bson import ObjectId
from app.services.bill_generator_service import generate_pdf_bill
from app.services.whatsapp_service import send_bill_whatsapp
import os


async def create_order_service(order,user:dict):

    product_collection = db_manager.db["products"]
    order_collection = db_manager.db["orders"]
    user_collection = db_manager.db["users"]
    customer_collection = db_manager.db["customers"]

    # Ensure items is a list
    items = order.items if hasattr(order, 'items') else order.get('items', [])
    
    # Get discount and payment method
    discount = order.discount if hasattr(order, 'discount') else order.get('discount', 0)
    payment_method = order.payment_method if hasattr(order, 'payment_method') else order.get('payment_method', 'cash')
    customer_id = order.customer_id if hasattr(order, 'customer_id') else order.get('customer_id')
    
    # Validate discount
    if discount is None:
        discount = 0
    elif discount < 0 or discount > 100:
        raise HTTPException(
            status_code=400,
            detail="Discount must be between 0 and 100"
        )
    
    # Validate payment method
    valid_payment_methods = ['cash', 'card', 'upi']
    if payment_method not in valid_payment_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Payment method must be one of: {', '.join(valid_payment_methods)}"
        )

    # Validate linked customer if provided
    if customer_id:
        try:
            customer_object_id = ObjectId(customer_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid customer ID format"
            )

        customer = await customer_collection.find_one({"_id": customer_object_id, "is_active": True})
        if not customer:
            raise HTTPException(
                status_code=404,
                detail="Customer not found"
            )
    
    order_items = []
    total_price = 0

    for item in items:

        # Look up product by barcode or productId
        if item.barcode:
            product = await product_collection.find_one({"barcode": item.barcode})
            product_identifier = item.barcode
        elif item.productId:
            try:
                object_id = ObjectId(item.productId)
                product = await product_collection.find_one({"_id": object_id})
            except:
                # If ObjectId conversion fails, try as string (for backward compatibility)
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

    # Apply discount to total price
    discounted_total = total_price
    if discount > 0:
        discounted_total = total_price * (1 - discount / 100)

    order_data = {
        "items": order_items,
        "total_price": discounted_total,
        "discount": discount if discount > 0 else None,
        "payment_method": payment_method,
        "user_id": str(user["_id"]),
        "customer_id": customer_id if customer_id else None,
        "created_at": datetime.now(timezone.utc),
        # Bill fields (will be updated after creation)
        "bill_sent": False,
        "bill_sent_at": None,
        "bill_pdf_path": None,
        "whatsapp_status": None
    }

    result = await order_collection.insert_one(order_data)

    order_data["id"] = str(result.inserted_id)

    # Generate bill and send WhatsApp (async background task)
    try:
        await generate_and_send_bill(order_data, user, customer_id)
    except Exception as e:
        print(f"Bill generation/ WhatsApp failed (non-blocking): {e}")
        # Don't fail the order creation if bill/ WhatsApp fails

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

        # Ensure response shape is consistent for optional linked customer
        if "customer_id" not in order:
            order["customer_id"] = None
        
        # ADD THIS:
        if "payment_method" not in order:
            order["payment_method"] = None

        # Remove the MongoDB _id field
        del order["_id"]

        orders.append(order)
    
    return orders

# async def create_purchase_orders():
#     pass


async def generate_and_send_bill(order_data: dict, user: dict, customer_id: Optional[str] = None):
    """
    Generate PDF bill and send WhatsApp message.
    This runs after order is created and doesn't block the response.
    """
    try:
        owner_id = str(user.get("_id") or user.get("id"))
        order_id = order_data.get("id")
        
        # Import db_manager at function start
        from app.db.mongodb import db_manager
        
        # Get shop settings from database (single shop system - get first available)
        from app.services.shop_settings_service import get_or_create_shop_settings
        from app.db.mongodb import db_manager
        
        # Try to get any existing shop settings (single shop system)
        settings_collection = db_manager.db["shop_settings"]
        settings_doc = await settings_collection.find_one()
        
        if settings_doc:
            # Use existing settings
            shop_info = {
                "business_name": settings_doc.get("business_name", "My Shop"),
                "address": settings_doc.get("address", ""),
                "gst_number": settings_doc.get("gst_number", ""),
                "terms_conditions": settings_doc.get("terms_conditions", ""),
                "greeting_message": settings_doc.get("greeting_message", "")
            }
        else:
            # Fallback to default
            shop_info = {
                "business_name": "My Shop",
                "address": "",
                "gst_number": "",
                "terms_conditions": "",
                "greeting_message": ""
            }
        
        # Get customer data if available
        customer_data = None
        if customer_id:
            try:
                customer_collection = db_manager.db["customers"]
                customer_obj_id = ObjectId(customer_id)
                customer_doc = await customer_collection.find_one({"_id": customer_obj_id})
                if customer_doc:
                    customer_data = {
                        "name": customer_doc.get("name", "Customer"),
                        "phone": customer_doc.get("phone"),
                        "email": customer_doc.get("email")
                    }
            except Exception as e:
                print(f"Failed to fetch customer data: {e}")
        
        # Generate PDF bill
        storage_path = os.getenv("BILL_STORAGE_PATH", "/tmp/bills")
        pdf_path = generate_pdf_bill(order_data, shop_info, customer_data, storage_path)
        print(f"PDF bill generated: {pdf_path}")
        
        # Send WhatsApp if customer has phone number
        whatsapp_result = {"success": False, "message": "No customer phone number"}
        
        if customer_data and customer_data.get("phone"):
            # Build bill URL
            bill_url = f"/api/orders/{order_id}/bill"
            
            whatsapp_result = await send_bill_whatsapp(
                phone_number=customer_data["phone"],
                order_data=order_data,
                shop_name=shop_settings.business_name,
                bill_url=bill_url,
                total=order_data.get("total_price", 0)
            )
            print(f"WhatsApp result: {whatsapp_result}")
        
        # Update order with bill info
        order_collection = db_manager.db["orders"]
        update_data = {
            "bill_pdf_path": pdf_path,
            "whatsapp_status": whatsapp_result.get("message", "Unknown")
        }
        
        if whatsapp_result.get("success"):
            update_data["bill_sent"] = True
            update_data["bill_sent_at"] = datetime.now(timezone.utc)
        
        await order_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_data}
        )
        
        print(f"Order {order_id} updated with bill info")
        
    except Exception as e:
        print(f"Error in generate_and_send_bill: {e}")
        # Don't raise - this should not fail the order creation
