"""
Employee management router for workforce analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from app.db.mongodb import db_manager
from app.api.router.dependency import get_current_user, require_owner
from app.core.rate_limit import limiter
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/")
@limiter.limit("100/minute")
async def get_all_employees(
    request: Request,
    user=Depends(require_owner)
):
    """Get all employees (excluding owners)."""
    try:
        users_collection = db_manager.db["users"]
        
        # Get all users with role != 'owner'
        pipeline = [
            {
                "$match": {
                    "role": {"$ne": "owner"}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "email": 1,
                    "role": 1,
                    "is_active": 1,
                    "created_at": 1
                }
            }
        ]
        
        employees = []
        async for employee in users_collection.aggregate(pipeline):
            # Convert ObjectId to string for JSON serialization
            if "_id" in employee:
                employee["_id"] = str(employee["_id"])
            employees.append(employee)
        
        return employees
        
    except Exception as e:
        print(f"Error getting all employees: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch employees")


@router.get("/{employee_id}/performance")
@limiter.limit("50/minute")
async def get_employee_performance(
    request: Request,
    employee_id: str = Path(..., description="Employee ID"),
    user=Depends(require_owner)
):
    """Get performance metrics for a specific employee."""
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(employee_id):
            raise HTTPException(status_code=400, detail="Invalid employee ID")
        
        orders_collection = db_manager.db["orders"]
        users_collection = db_manager.db["users"]
        
        # Check if employee exists and is not an owner
        employee_obj = await users_collection.find_one({
            "_id": ObjectId(employee_id),
            "role": {"$ne": "owner"}
        })
        
        if not employee_obj:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Get performance metrics with comprehensive calculations
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        
        # Current period (last 30 days)
        current_pipeline = [
            {
                "$match": {
                    "$or": [
                        {"user_id": ObjectId(employee_id)},
                        {"user_id": employee_id}
                    ],
                    "created_at": {"$gte": thirty_days_ago}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sales": {"$sum": "$total_price"},
                    "total_orders": {"$sum": 1},
                    "total_items": {"$sum": {"$size": {"$ifNull": ["$items", []]}}},
                    "order_dates": {"$push": "$created_at"}
                }
            }
        ]
        
        # Previous period (30-60 days ago) for trend calculation
        previous_pipeline = [
            {
                "$match": {
                    "$or": [
                        {"user_id": ObjectId(employee_id)},
                        {"user_id": employee_id}
                    ],
                    "created_at": {
                        "$gte": sixty_days_ago,
                        "$lt": thirty_days_ago
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sales": {"$sum": "$total_price"},
                    "total_orders": {"$sum": 1}
                }
            }
        ]
        
        # All time metrics
        all_time_pipeline = [
            {
                "$match": {
                    "$or": [
                        {"user_id": ObjectId(employee_id)},
                        {"user_id": employee_id}
                    ]
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sales": {"$sum": "$total_price"},
                    "total_orders": {"$sum": 1},
                    "total_items": {"$sum": {"$size": {"$ifNull": ["$items", []]}}},
                    "avg_order_value": {"$avg": "$total_price"},
                    "max_order_value": {"$max": "$total_price"},
                    "min_order_value": {"$min": "$total_price"}
                }
            }
        ]
        
        # Execute all pipelines
        current_result = await orders_collection.aggregate(current_pipeline).to_list(length=1)
        previous_result = await orders_collection.aggregate(previous_pipeline).to_list(length=1)
        all_time_result = await orders_collection.aggregate(all_time_pipeline).to_list(length=1)
        
        if all_time_result:
            all_time_data = all_time_result[0]
            current_data = current_result[0] if current_result else {
                "total_sales": 0, "total_orders": 0, "total_items": 0, "order_dates": []
            }
            previous_data = previous_result[0] if previous_result else {
                "total_sales": 0, "total_orders": 0
            }
            
            # Calculate average order value
            average_order_value = (
                all_time_data["total_sales"] / all_time_data["total_orders"]
                if all_time_data["total_orders"] > 0 else 0
            )
            
            # Calculate trend based on sales comparison
            sales_change = current_data["total_sales"] - previous_data["total_sales"]
            sales_change_percent = (
                (sales_change / previous_data["total_sales"] * 100)
                if previous_data["total_sales"] > 0 else 0
            )
            
            # Determine trend
            if sales_change_percent > 10:
                trend = "up"
            elif sales_change_percent < -10:
                trend = "down"
            else:
                trend = "stable"
            
            # Calculate performance score (0-100) with multiple factors
            # Base score from sales volume
            sales_score = min(50, (all_time_data["total_sales"] / 5000) * 50)
            
            # Score from order frequency
            orders_score = min(30, (all_time_data["total_orders"] / 50) * 30)
            
            # Score from average order value
            avg_order_score = min(20, (average_order_value / 100) * 20)
            
            performance_score = min(100, sales_score + orders_score + avg_order_score)
            
            # Calculate daily average orders
            days_active = len(set(current_data["order_dates"])) if current_data["order_dates"] else 1
            daily_avg_orders = current_data["total_orders"] / max(days_active, 1)
            
            return {
                "total_sales": all_time_data["total_sales"],
                "total_orders": all_time_data["total_orders"],
                "total_items": all_time_data["total_items"],
                "average_order_value": average_order_value,
                "max_order_value": all_time_data.get("max_order_value", 0),
                "min_order_value": all_time_data.get("min_order_value", 0),
                "performance_score": round(performance_score, 1),
                "trend": trend,
                "sales_change_percent": round(sales_change_percent, 1),
                "current_period_sales": current_data["total_sales"],
                "previous_period_sales": previous_data["total_sales"],
                "daily_avg_orders": round(daily_avg_orders, 1),
                "days_active": days_active
            }
        else:
            # Return default performance for employees with no orders
            return {
                "total_sales": 0,
                "total_orders": 0,
                "total_items": 0,
                "average_order_value": 0,
                "max_order_value": 0,
                "min_order_value": 0,
                "performance_score": 0,
                "trend": "stable",
                "sales_change_percent": 0,
                "current_period_sales": 0,
                "previous_period_sales": 0,
                "daily_avg_orders": 0,
                "days_active": 0
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting employee performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch employee performance")


@router.get("/debug")
@limiter.limit("50/minute")
async def debug_orders(
    request: Request,
    user=Depends(require_owner)
):
    """Debug endpoint to check order data structure."""
    try:
        orders_collection = db_manager.db["orders"]
        users_collection = db_manager.db["users"]
        
        # Get a few sample orders to check structure
        sample_orders = await orders_collection.find({}).to_list(length=5)
        
        # Get sample users to check structure
        sample_users = await users_collection.find({"role": {"$ne": "owner"}}).to_list(length=5)
        
        # Count total orders
        total_orders = await orders_collection.count_documents({})
        
        # Count orders with user_id field
        orders_with_user_id = await orders_collection.count_documents({"user_id": {"$exists": True}})
        
        # Try to find orders for each user
        user_order_matches = []
        for user in sample_users:
            user_id_str = str(user.get("_id", ""))
            # Try both string and ObjectId matching
            orders_by_string = await orders_collection.count_documents({"user_id": user_id_str})
            orders_by_objectid = await orders_collection.count_documents({"user_id": user.get("_id")})
            user_order_matches.append({
                "user_id": user_id_str,
                "user_name": user.get("name", ""),
                "orders_by_string": orders_by_string,
                "orders_by_objectid": orders_by_objectid
            })
        
        return {
            "total_orders": total_orders,
            "orders_with_user_id": orders_with_user_id,
            "user_order_matches": user_order_matches,
            "sample_orders": [
                {
                    "_id": str(order.get("_id", "")),
                    "user_id": order.get("user_id", "MISSING"),
                    "user_id_type": type(order.get("user_id")).__name__ if "user_id" in order else "MISSING",
                    "total_price": order.get("total_price", 0),
                    "created_at": order.get("created_at", "")
                }
                for order in sample_orders
            ],
            "sample_users": [
                {
                    "_id": str(user.get("_id", "")),
                    "name": user.get("name", ""),
                    "role": user.get("role", ""),
                    "email": user.get("email", "")
                }
                for user in sample_users
            ]
        }
        
    except Exception as e:
        print(f"Debug error: {e}")
        return {"error": str(e)}


@router.get("/stats")
@limiter.limit("50/minute")
async def get_employee_stats(
    request: Request,
    user=Depends(require_owner)
):
    """Get overall employee statistics."""
    try:
        users_collection = db_manager.db["users"]
        orders_collection = db_manager.db["orders"]
        
        # Total employees (excluding owners)
        total_employees = await users_collection.count_documents({"role": {"$ne": "owner"}})
        
        # Active employees (with orders in last 30 days)
        from datetime import datetime, timezone, timedelta
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        active_pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": thirty_days_ago}
                }
            },
            {
                "$group": {
                    "_id": "$user_id"
                }
            },
            {
                "$count": "active_count"
            }
        ]
        
        active_result = await orders_collection.aggregate(active_pipeline).to_list(length=1)
        active_employees = active_result[0]["active_count"] if active_result else 0
        
        return {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "inactive_employees": total_employees - active_employees
        }
        
    except Exception as e:
        print(f"Error getting employee stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch employee statistics")
