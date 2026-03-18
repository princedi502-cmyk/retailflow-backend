"""
Complete optimized analytics router with proper caching and query optimization
This replaces the current analytics.py with all aggregation calls properly cached
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from app.db.mongodb import db_manager
from app.api.router.dependency import get_current_user, require_employee, require_owner
from app.core.rate_limit import limiter
from app.core.optimized_aggregations import aggregation_optimizer, OptimizedPipelines
from datetime import datetime, timezone, timedelta
import re

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/revenue")
@limiter.limit("100/minute")
async def total_revenue(
    request: Request,
    user=Depends(require_owner)
):
    """Total all-time revenue with caching."""
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_price"}
            }
        }
    ]

    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key="total_revenue",
        cache_ttl=600  # 10 minutes for revenue data
    )

    if result:
        return {"total_revenue": result[0]["total_revenue"]}

    return {"total_revenue": 0}


@router.get("/orders-count")
async def total_orders(
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of orders to count"),
    user=Depends(get_current_user)
):
    """Total orders count with caching."""
    order_collection = db_manager.db["orders"]
    
    # Use optimized aggregation for counting with caching
    pipeline = [
        {"$count": "total_orders"}
    ]
    
    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key="total_orders",
        cache_ttl=300  # 5 minutes
    )
    
    return {"total_orders": result[0]["total_orders"] if result else 0}


@router.get("/top-products")
async def top_products(
    limit: int = Query(5, ge=1, le=50, description="Number of top products to return"),
    user=Depends(get_current_user)
):
    """Top products with optimized aggregation and caching."""
    
    # Use pre-built optimized pipeline
    pipeline = OptimizedPipelines.top_products_pipeline(limit=limit, days_back=365)
    
    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"top_products_{limit}",
        cache_ttl=300  # 5 minutes cache
    )
    
    return result


@router.get("/worst-products")
async def worst_products(
    limit: int = Query(5, ge=1, le=50, description="Number of worst products to return"),
    user=Depends(get_current_user)
):
    """Worst products with optimized aggregation and caching."""
    
    # Modified top products pipeline with ascending sort
    pipeline = OptimizedPipelines.top_products_pipeline(limit=limit, days_back=365)
    
    # Change sort to ascending for worst products
    for stage in pipeline:
        if "$sort" in stage and "total_sold" in stage["$sort"]:
            stage["$sort"]["total_sold"] = 1  # Ascending for worst products
    
    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"worst_products_{limit}",
        cache_ttl=300  # 5 minutes cache
    )
    
    return result


@router.get("/sales-summary")
async def sales_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to look back for weekly summary"),
    user=Depends(get_current_user)
):
    """Returns items sold today and this week with caching."""
    
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    week_start = today_start - timedelta(days=min(days, today_start.weekday()))

    pipeline = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "today": {
                    "$sum": {
                        "$cond": [
                            {"$gte": ["$created_at", today_start]},
                            "$items.quantity",
                            0
                        ]
                    }
                },
                "week": {
                    "$sum": {
                        "$cond": [
                            {"$gte": ["$created_at", week_start]},
                            "$items.quantity",
                            0
                        ]
                    }
                }
            }
        }
    ]

    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"sales_summary_{days}",
        cache_ttl=180  # 3 minutes for current data
    )

    if result:
        return {
            "items_sold_today": result[0]["today"],
            "items_sold_week": result[0]["week"]
        }

    return {
        "items_sold_today": 0,
        "items_sold_week": 0
    }


@router.get("/low-stock-products")
async def low_stock_products(
    threshold: int = Query(10, ge=0, le=1000, description="Low stock threshold"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of products to return"),
    user=Depends(get_current_user)
):
    """Low stock products with caching."""
    
    pipeline = [
        {
            "$match": {"stock": {"$lt": threshold}}
        },
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "stock": 1,
                "category": {"$ifNull": ["$category", "N/A"]}
            }
        }
    ]

    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="products",
        pipeline=pipeline,
        cache_key=f"low_stock_{threshold}_{limit}",
        cache_ttl=600  # 10 minutes
    )
    
    return result


@router.get("/monthly-revenue")
async def monthly_revenue(
    year: int = Query(None, ge=2020, le=2030, description="Year to filter revenue data"),
    user=Depends(get_current_user)
):
    """Returns array of 12 revenue values indexed by month (0=Jan) with caching."""
    
    # Default to current year if not provided
    if year is None:
        year = datetime.now().year
    
    # Validate year format
    if not re.match(r'^\d{4}$', str(year)):
        raise HTTPException(
            status_code=400,
            detail="Invalid year format"
        )

    pipeline = [
        {
            "$match": {
                "$expr": {
                    "$eq": [{"$year": {"$toDate": "$created_at"}}, year]
                }
            }
        },
        {
            "$project": {
                "month": {"$month": {"$toDate": "$created_at"}},
                "total": "$total_price"
            }
        },
        {
            "$group": {
                "_id": "$month",
                "revenue": {"$sum": "$total"}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"monthly_revenue_{year}",
        cache_ttl=3600  # 1 hour for historical data
    )

    months_revenue = [0] * 12

    for item in result:
        if item["_id"] is not None:
            month_index = item["_id"] - 1
            months_revenue[month_index] = item["revenue"]

    return {"values": months_revenue}


@router.get("/category-sales")
async def category_sales(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of categories to return"),
    user=Depends(get_current_user)
):
    """Category sales with optimized aggregation and caching."""
    
    # Use pre-built optimized pipeline
    pipeline = OptimizedPipelines.category_sales_pipeline(limit=limit, days_back=365)
    
    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"category_sales_{limit}",
        cache_ttl=300  # 5 minutes cache
    )
    
    # Transform result for compatibility
    labels = [r["category"] for r in result]
    values = [r["revenue"] for r in result]
    items_sold = [r.get("itemsSold", 0) for r in result]

    return {
        "labels": labels, 
        "values": values,
        "itemsSold": items_sold
    }


@router.get("/items-sold")
async def items_sold(
    months: int = Query(1, ge=1, le=24, description="Number of months to look back"),
    user=Depends(get_current_user)
):
    """Items sold in the current calendar months with caching."""
    
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    # Adjust start date based on months parameter
    if months > 1:
        start = start - timedelta(days=30 * (months - 1))

    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "itemsSold": {"$sum": {"$ifNull": ["$items.quantity", 0]}}
            }
        }
    ]

    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"items_sold_{months}",
        cache_ttl=300
    )
    
    return {"itemsSold": result[0]["itemsSold"] if result else 0}


@router.get("/this-month")
async def this_month(
    user=Depends(get_current_user)
):
    """This month's revenue and items sold with caching."""
    
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": month_start}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_price"},
                "items_sold": {"$sum": {"$ifNull": ["$items.quantity", 0]}}
            }
        }
    ]

    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key="this_month_stats",
        cache_ttl=180  # 3 minutes for current month data
    )

    if result:
        return {
            "total_revenue": result[0]["total_revenue"],
            "items_sold": result[0]["items_sold"]
        }

    return {
        "total_revenue": 0,
        "items_sold": 0
    }


@router.get("/sales-by-employee")
@limiter.limit("50/minute")
async def sales_by_employee(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of employees to return"),
    user=Depends(require_owner)
):
    """Sales by employee with optimized aggregation and caching."""
    
    # Use pre-built optimized pipeline
    pipeline = OptimizedPipelines.employee_performance_pipeline(limit=limit, days_back=365)
    
    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"sales_by_employee_{limit}",
        cache_ttl=300  # 5 minutes cache
    )
    
    return result


@router.get("/top-product")
@limiter.limit("80/minute")
async def get_top_product(
    request: Request,
    limit: int = Query(1, ge=1, le=10, description="Number of top products to return"),
    user=Depends(require_owner)
):
    """Top product with optimized aggregation and caching."""
    
    # Use optimized pipeline with product_id grouping
    pipeline = [
        {"$unwind": "$items"},
        { 
           "$group":{
                "_id": "$items.product_id",
                "item_sold":{"$sum":"$items.quantity"},
                "total_revenue": {
                    "$sum": {
                        "$multiply": ["$items.price","$items.quantity"]
                    }
                },
                "order_count": {"$sum": 1},
            }
        },
        
        {
            "$addFields": {
                "product_object_id": {"$toObjectId": "$_id"}
            }
        },
        {
            "$lookup": {
                "from": "products",
                "localField": "product_object_id",
                "foreignField": "_id",
                "as": "product_info"
            }
        },
        {"$unwind": "$product_info"},
        {
            "$project": {
                "_id": 0,
                "product_id": "$_id",
                "product_name": "$product_info.name",
                "barcode": "$product_info.barcode",
                "total_revenue": 1,
                "order_count": 1,
                "items_sold": 1
            }
        },
        {"$sort": {"total_revenue": -1}},
        {"$limit": limit}
    ]
    
    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="orders",
        pipeline=pipeline,
        cache_key=f"top_product_{limit}",
        cache_ttl=300
    )
    
    return result


@router.get("/unsold-products")
@limiter.limit("40/minute")
async def unsold_products(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of products to return"),
    user=Depends(require_owner)
):
    """Unsold products with optimized aggregation and caching."""
    
    days_ago = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {
            "$lookup":{
                "from":"orders",
                "let":{"product_id":{"$toString":"$_id"}},
                "pipeline":[
                    {"$unwind":"$items"},
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq":["$items.product_id","$$product_id"]},
                                    {"$gte":["$created_at",days_ago]}
                                ]
                            }
                        }
                    }
                ],
                "as":"recent_orders"
            }
        },

        {
            "$match":{
                "recent_orders":{"$size":0}
            }
        },
        {
            "$project":{
                "_id": 0,
                "product_id":{"$toString":"$_id"},
                "name":1,
                "barcode":1,
                "price":1,
                "stock":1,
                "category":1,
            }
        }
    ]

    result = await aggregation_optimizer.optimized_aggregate(
        collection_name="products",
        pipeline=pipeline,
        cache_key=f"unsold_products_{days}_{limit}",
        cache_ttl=600  # 10 minutes
    )
    
    return result
