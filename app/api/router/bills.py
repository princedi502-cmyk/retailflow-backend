from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from app.api.router.dependency import get_current_user
from app.services.order_service import generate_and_send_bill
from app.db.mongodb import db_manager
from bson import ObjectId
from app.core.rate_limit import limiter
from fastapi import Request

router = APIRouter()


@router.get("/orders/{order_id}/bill")
@limiter.limit("60/minute")
async def download_bill(
    request: Request,
    order_id: str = Path(..., description="Order ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Download PDF bill for an order.
    """
    try:
        order_obj_id = ObjectId(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    # Get order from database
    order_collection = db_manager.db["orders"]
    order = await order_collection.find_one({"_id": order_obj_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions - user should own the order or be admin
    order_user_id = str(order.get("user_id", ""))
    current_user_id = str(current_user.get("_id") or current_user.get("id"))
    user_role = current_user.get("role", "")
    
    if order_user_id != current_user_id and user_role != "owner":
        raise HTTPException(status_code=403, detail="Not authorized to access this bill")
    
    # Check if bill PDF exists
    pdf_path = order.get("bill_pdf_path")
    
    if not pdf_path:
        # Bill hasn't been generated yet - generate it now
        from app.services.bill_generator_service import generate_pdf_bill
        import os
        
        # Get shop settings from database (single shop system - get first available)
        settings_collection = db_manager.db["shop_settings"]
        settings_doc = await settings_collection.find_one()
        
        if settings_doc:
            shop_info = {
                "business_name": settings_doc.get("business_name", "My Shop"),
                "address": settings_doc.get("address", ""),
                "gst_number": settings_doc.get("gst_number", ""),
                "terms_conditions": settings_doc.get("terms_conditions", ""),
                "greeting_message": settings_doc.get("greeting_message", "")
            }
        else:
            shop_info = {
                "business_name": "My Shop",
                "address": "",
                "gst_number": "",
                "terms_conditions": "",
                "greeting_message": ""
            }
        
        # Get customer data
        customer_data = None
        customer_id = order.get("customer_id")
        if customer_id:
            customer_collection = db_manager.db["customers"]
            try:
                customer_doc = await customer_collection.find_one({"_id": ObjectId(customer_id)})
                if customer_doc:
                    customer_data = {
                        "name": customer_doc.get("name", "Customer"),
                        "phone": customer_doc.get("phone"),
                        "email": customer_doc.get("email")
                    }
            except:
                pass
        
        # Generate PDF
        order["id"] = order_id
        storage_path = os.getenv("BILL_STORAGE_PATH", "/tmp/bills")
        pdf_path = generate_pdf_bill(order, shop_info, customer_data, storage_path)
        
        # Save path to order
        await order_collection.update_one(
            {"_id": order_obj_id},
            {"$set": {"bill_pdf_path": pdf_path}}
        )
    
    # Check if file exists
    import os
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Bill PDF not found. It may have been deleted.")
    
    # Return file with CORS headers using StreamingResponse
    from fastapi.responses import StreamingResponse
    
    def iterfile():
        with open(pdf_path, "rb") as f:
            yield from f
    
    response = StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=bill_{order_id}.pdf"
        }
    )
    
    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    
    return response


@router.post("/orders/{order_id}/resend-bill")
@limiter.limit("10/minute")
async def resend_bill_whatsapp(
    request: Request,
    order_id: str = Path(..., description="Order ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Resend bill via WhatsApp.
    """
    try:
        order_obj_id = ObjectId(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    # Get order from database
    order_collection = db_manager.db["orders"]
    order = await order_collection.find_one({"_id": order_obj_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions
    order_user_id = str(order.get("user_id", ""))
    current_user_id = str(current_user.get("_id") or current_user.get("id"))
    
    if order_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to resend this bill")
    
    # Get customer data
    customer_id = order.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="Order has no customer linked")
    
    customer_collection = db_manager.db["customers"]
    try:
        customer_doc = await customer_collection.find_one({"_id": ObjectId(customer_id)})
        if not customer_doc:
            raise HTTPException(status_code=404, detail="Customer not found")
    except:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if not customer_doc.get("phone"):
        raise HTTPException(status_code=400, detail="Customer has no phone number")
    
    # Resend bill
    order["id"] = order_id
    result = await generate_and_send_bill(order, current_user, customer_id)
    
    return {
        "success": True,
        "message": "Bill resent via WhatsApp",
        "order_id": order_id
    }
