"""
Optimized aggregation utilities for RetailFlow
Provides high-performance aggregation pipelines with caching and optimization
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Union
from functools import wraps
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from pymongo import MongoClient
from pymongo.collection import Collection
from app.core.cache import cache_manager
from app.db.mongodb import db_manager

logger = logging.getLogger(__name__)

class AggregationOptimizer:
    """Optimized aggregation pipeline manager"""
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        self.slow_query_threshold = 1000.0  # milliseconds
        
    async def optimized_aggregate(
        self, 
        collection_name: str, 
        pipeline: List[Dict],
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict]:
        """Execute optimized aggregation with caching"""
        
        # Generate cache key if not provided
        if cache_key is None:
            cache_key = f"agg_{collection_name}_{hash(str(pipeline))}"
        
        # Check cache first
        if use_cache:
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for aggregation: {cache_key}")
                return cached_result
        
        # Execute aggregation with performance monitoring
        start_time = time.time()
        collection = db_manager.db[collection_name]
        
        try:
            result = await collection.aggregate(pipeline).to_list(length=1000)
            execution_time = (time.time() - start_time) * 1000
            
            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning(
                    f"Slow aggregation detected: {collection_name} "
                    f"took {execution_time:.2f}ms"
                )
            
            # Cache result if enabled
            if use_cache and result:
                await cache_manager.set(
                    cache_key, 
                    result, 
                    ttl=cache_ttl or self.cache_ttl
                )
            
            logger.debug(f"Aggregation completed in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Aggregation failed after {execution_time:.2f}ms: {str(e)}")
            raise

# Global optimizer instance
aggregation_optimizer = AggregationOptimizer()

def optimized_aggregation(
    collection_name: str,
    cache_ttl: int = 300,
    use_cache: bool = True
):
    """Decorator for optimized aggregation operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract pipeline from function result
            pipeline = await func(*args, **kwargs)
            
            # Generate cache key from function name and parameters
            cache_key = f"{func.__name__}_{hash(str(args))}_{hash(str(sorted(kwargs.items())))}"
            
            return await aggregation_optimizer.optimized_aggregate(
                collection_name=collection_name,
                pipeline=pipeline,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
                use_cache=use_cache
            )
        return wrapper
    return decorator

# Pre-built optimized pipelines
class OptimizedPipelines:
    """Collection of pre-optimized aggregation pipelines"""
    
    @staticmethod
    def top_products_pipeline(
        limit: int = 10,
        days_back: int = 365,
        min_sales: int = 1
    ) -> List[Dict]:
        """Optimized pipeline for top products analysis"""
        return [
            {
                "$match": {
                    "created_at": {
                        "$gte": datetime.now(timezone.utc) - timedelta(days=days_back)
                    }
                }
            },
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": "$items.name",
                    "total_sold": {"$sum": "$items.quantity"},
                    "total_revenue": {
                        "$sum": {
                            "$multiply": [
                                {"$ifNull": ["$items.quantity", 0]},
                                {"$ifNull": ["$items.price", 0]}
                            ]
                        }
                    },
                    "order_count": {"$sum": 1},
                    "avg_price": {"$avg": "$items.price"}
                }
            },
            {
                "$match": {
                    "total_sold": {"$gte": min_sales}
                }
            },
            {"$sort": {"total_sold": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "products",
                    "localField": "_id",
                    "foreignField": "name",
                    "as": "product_info"
                }
            },
            {"$unwind": {"path": "$product_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "name": "$_id",
                    "unitsSold": "$total_sold",
                    "revenue": "$total_revenue",
                    "orderCount": "$order_count",
                    "avgPrice": "$avg_price",
                    "category": {"$ifNull": ["$product_info.category", "N/A"]},
                    "stock": {"$ifNull": ["$product_info.stock", 0]},
                    "_id": 0
                }
            }
        ]
    
    @staticmethod
    def category_sales_pipeline(
        limit: int = 20,
        days_back: int = 365
    ) -> List[Dict]:
        """Optimized pipeline for category sales analysis"""
        return [
            {
                "$match": {
                    "created_at": {
                        "$gte": datetime.now(timezone.utc) - timedelta(days=days_back)
                    }
                }
            },
            {"$unwind": "$items"},
            {
                "$lookup": {
                    "from": "products",
                    "localField": "items.name",
                    "foreignField": "name",
                    "as": "product_info"
                }
            },
            {"$unwind": {"path": "$product_info", "preserveNullAndEmptyArrays": True}},
            {
                "$group": {
                    "_id": {
                        "$ifNull": ["$product_info.category", "Uncategorized"]
                    },
                    "revenue": {
                        "$sum": {
                            "$multiply": [
                                {"$ifNull": ["$items.quantity", 0]},
                                {"$ifNull": ["$items.price", 0]}
                            ]
                        }
                    },
                    "items_sold": {"$sum": {"$ifNull": ["$items.quantity", 0]}},
                    "order_count": {"$sum": 1},
                    "unique_products": {"$addToSet": "$items.name"}
                }
            },
            {
                "$addFields": {
                    "unique_product_count": {"$size": "$unique_products"}
                }
            },
            {"$sort": {"revenue": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "category": "$_id",
                    "revenue": 1,
                    "itemsSold": "$items_sold",
                    "orderCount": "$order_count",
                    "uniqueProductCount": "$unique_product_count",
                    "_id": 0
                }
            }
        ]
    
    @staticmethod
    def sales_trend_pipeline(
        days_back: int = 30,
        group_by: str = "day"
    ) -> List[Dict]:
        """Optimized pipeline for sales trend analysis"""
        # Determine grouping format
        if group_by == "hour":
            date_format = "%Y-%m-%d-%H"
        elif group_by == "week":
            date_format = "%Y-%U"
        else:  # day
            date_format = "%Y-%m-%d"
        
        return [
            {
                "$match": {
                    "created_at": {
                        "$gte": datetime.now(timezone.utc) - timedelta(days=days_back)
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": date_format,
                            "date": {"$toDate": "$created_at"}
                        }
                    },
                    "revenue": {"$sum": "$total_price"},
                    "order_count": {"$sum": 1},
                    "items_sold": {
                        "$sum": {
                            "$reduce": {
                                "input": "$items",
                                "initialValue": 0,
                                "in": {"$add": ["$$value", {"$ifNull": ["$$this.quantity", 0]}]}
                            }
                        }
                    }
                }
            },
            {"$sort": {"_id": 1}},
            {
                "$project": {
                    "date": "$_id",
                    "revenue": 1,
                    "orderCount": "$order_count",
                    "itemsSold": "$items_sold",
                    "_id": 0
                }
            }
        ]
    
    @staticmethod
    def employee_performance_pipeline(
        limit: int = 50,
        days_back: int = 365
    ) -> List[Dict]:
        """Optimized pipeline for employee performance analysis"""
        return [
            {
                "$match": {
                    "created_at": {
                        "$gte": datetime.now(timezone.utc) - timedelta(days=days_back)
                    }
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "total_revenue": {"$sum": "$total_price"},
                    "order_count": {"$sum": 1},
                    "items_sold": {
                        "$sum": {
                            "$reduce": {
                                "input": "$items",
                                "initialValue": 0,
                                "in": {"$add": ["$$value", {"$ifNull": ["$$this.quantity", 0]}]}
                            }
                        }
                    },
                    "avg_order_value": {"$avg": "$total_price"},
                    "first_order": {"$min": "$created_at"},
                    "last_order": {"$max": "$created_at"}
                }
            },
            {
                "$addFields": {
                    "user_object_id": {"$toObjectId": "$_id"}
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_object_id",
                    "foreignField": "_id",
                    "as": "user_info"
                }
            },
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "userId": "$_id",
                    "username": {"$ifNull": ["$user_info.username", "Unknown"]},
                    "email": {"$ifNull": ["$user_info.email", "N/A"]},
                    "totalRevenue": "$total_revenue",
                    "orderCount": "$order_count",
                    "itemsSold": "$items_sold",
                    "avgOrderValue": "$avg_order_value",
                    "firstOrder": "$first_order",
                    "lastOrder": "$last_order",
                    "_id": 0
                }
            },
            {"$sort": {"totalRevenue": -1}},
            {"$limit": limit}
        ]
