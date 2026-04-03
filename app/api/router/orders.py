from fastapi import APIRouter, Depends, HTTPException, Path, Request, Query
from app.schemas.order_schema import OrderCreate, OrderResponse
from app.api.router.dependency import get_current_user, require_employee, require_owner
from app.services.order_service import create_order_service, get_orders_service
from app.core.rate_limit import limiter
from app.core.cache import cache_manager
from app.core.websocket_manager import websocket_manager
from app.api.router.analytics import sales_summary
import re

router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@router.post("/", response_model=OrderResponse)
@limiter.limit("60/minute")
async def create_order(
    request: Request,
    order: OrderCreate, 
    current_user: dict = Depends(get_current_user)
):
    # Validate order data
    if not order.items or len(order.items) == 0:
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one item"
        )
    
    # Validate each item
    for item in order.items:
        # Check that either barcode or productId is provided
        if not item.barcode and not item.productId:
            raise HTTPException(
                status_code=400,
                detail="Either barcode or productId must be provided for each item"
            )
        
        if item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Item quantity must be greater than 0"
            )

    result = await create_order_service(order, current_user)
    
    print(f"Order created: {result}")
    
    # Invalidate analytics caches when new order is created
    print("Invalidating caches...")
    deleted_count = await cache_manager.delete_pattern("analytics:*")
    print(f"Deleted {deleted_count} analytics cache keys")
    
    deleted_count2 = await cache_manager.delete_pattern("sales_summary:*")
    print(f"Deleted {deleted_count2} sales_summary cache keys")
    
    # Also try to delete the specific cache key
    specific_key = "sales_summary_7"
    deleted_specific = await cache_manager.delete(specific_key)
    print(f"Deleted specific cache key {specific_key}: {deleted_specific}")
    
    # Get updated sales metrics for WebSocket broadcast
    try:
        sales_data = await sales_summary(days=7, user=current_user)
        
        print(f"Fresh sales data after order creation: {sales_data}")
        
        # Get additional analytics data for owner dashboard
        try:
            from app.api.router.analytics import this_month, monthly_revenue, category_sales

            # Get this month's analytics
            this_month_data = await this_month(user=current_user)

            # Get monthly revenue data
            monthly_rev_data = await monthly_revenue(user=current_user)

            # Get category sales data
            category_sales_data = await category_sales(limit=20, user=current_user)
            
            # Broadcast comprehensive update to all connected users
            await websocket_manager.broadcast_sales_update({
                "items_sold_today": sales_data.get("items_sold_today", 0),
                "items_sold_week": sales_data.get("items_sold_week", 0),
                "this_month_revenue": this_month_data.get("total_revenue", 0),
                "this_month_items_sold": this_month_data.get("items_sold", 0),
                "monthly_revenue": monthly_rev_data.get("values", []),
                "category_sales": {
                    "labels": category_sales_data.get("labels", []),
                    "values": category_sales_data.get("values", []),
                    "itemsSold": category_sales_data.get("itemsSold", [])
                }
            })
            
        except Exception as e:
            print(f"Error getting additional analytics for WebSocket: {e}")
            # Fallback to basic sales update
            await websocket_manager.broadcast_sales_update({
                "items_sold_today": sales_data.get("items_sold_today", 0),
                "items_sold_week": sales_data.get("items_sold_week", 0)
            })
        
        # Send order notification to the user who created the order
        await websocket_manager.send_order_notification(
            str(current_user["_id"]), 
            {
                "order_id": result.get("id"),
                "total_price": result.get("total_price"),
                "items_count": len(result.get("items", [])),
                "message": "Order created successfully"
            }
        )
        
        print(f"Order created and WebSocket broadcast sent: {sales_data}")
        
    except Exception as e:
        print(f"Error broadcasting WebSocket update: {e}")
    
    return result


@router.get("/", response_model=list[OrderResponse])
async def get_orders(
    page: int = Query(1, ge=1, le=1000, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
):

    return await get_orders_service(page, limit)
