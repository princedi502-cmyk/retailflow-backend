"""
Database query optimization module for RetailFlow
Provides query performance monitoring, caching, and optimization utilities
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.operations import IndexModel
from app.core.db_config import DatabaseConfig

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Metrics for tracking query performance"""
    query_type: str
    collection: str
    execution_time: float
    result_count: int
    timestamp: datetime
    slow_query_threshold: float = 1000.0  # milliseconds

class QueryOptimizer:
    """Main query optimization class"""
    
    def __init__(self, db: MongoClient):
        self.db = db
        self.query_cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutes
        self.slow_query_threshold = 1000.0  # milliseconds
        self.query_metrics: List[QueryMetrics] = []
        self.max_metrics_history = 1000
        
    def monitor_query_performance(self, func):
        """Decorator to monitor query performance"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            collection_name = kwargs.get('collection', 'unknown')
            query_type = func.__name__
            
            try:
                result = await func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                result_count = len(result) if isinstance(result, list) else 1
                
                # Log slow queries
                if execution_time > self.slow_query_threshold:
                    logger.warning(
                        f"Slow query detected: {query_type} on {collection_name} "
                        f"took {execution_time:.2f}ms"
                    )
                
                # Store metrics
                self._store_query_metrics(
                    query_type, collection_name, execution_time, result_count
                )
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Query failed after {execution_time:.2f}ms: {str(e)}")
                raise
                
        return wrapper
    
    def _store_query_metrics(self, query_type: str, collection: str, 
                           execution_time: float, result_count: int):
        """Store query performance metrics"""
        metric = QueryMetrics(
            query_type=query_type,
            collection=collection,
            execution_time=execution_time,
            result_count=result_count,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.query_metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.query_metrics) > self.max_metrics_history:
            self.query_metrics = self.query_metrics[-self.max_metrics_history:]
    
    def get_cache_key(self, collection: str, query: Dict, **kwargs) -> str:
        """Generate cache key for query"""
        import hashlib
        import json
        
        cache_data = {
            'collection': collection,
            'query': query,
            **kwargs
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    async def cached_find(self, collection_name: str, query: Dict, 
                         projection: Optional[Dict] = None, limit: Optional[int] = None,
                         sort: Optional[List] = None, cache_ttl: Optional[int] = None) -> List[Dict]:
        """Cached version of find operation"""
        cache_key = self.get_cache_key(
            collection_name, query, projection=projection, 
            limit=limit, sort=sort
        )
        
        # Check cache
        if cache_key in self.query_cache:
            cached_data = self.query_cache[cache_key]
            if datetime.now(timezone.utc) - cached_data['timestamp'] < timedelta(seconds=cache_ttl or self.cache_ttl):
                logger.debug(f"Cache hit for query on {collection_name}")
                return cached_data['data']
        
        # Execute query
        collection = self.db[collection_name]
        cursor = collection.find(query, projection)
        
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        
        result = await cursor.to_list(length=limit or 1000)
        
        # Cache result
        self.query_cache[cache_key] = {
            'data': result,
            'timestamp': datetime.now(timezone.utc)
        }
        
        return result
    
    async def cached_aggregate(self, collection_name: str, pipeline: List[Dict],
                             cache_ttl: Optional[int] = None) -> List[Dict]:
        """Cached version of aggregate operation"""
        cache_key = self.get_cache_key(collection_name, pipeline=pipeline)
        
        # Check cache
        if cache_key in self.query_cache:
            cached_data = self.query_cache[cache_key]
            if datetime.now(timezone.utc) - cached_data['timestamp'] < timedelta(seconds=cache_ttl or self.cache_ttl):
                logger.debug(f"Cache hit for aggregation on {collection_name}")
                return cached_data['data']
        
        # Execute aggregation
        collection = self.db[collection_name]
        result = await collection.aggregate(pipeline).to_list(length=1000)
        
        # Cache result
        self.query_cache[cache_key] = {
            'data': result,
            'timestamp': datetime.now(timezone.utc)
        }
        
        return result
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear query cache"""
        if pattern:
            keys_to_remove = [k for k in self.query_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.query_cache[key]
        else:
            self.query_cache.clear()
        
        logger.info(f"Cache cleared. Pattern: {pattern or 'all'}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics"""
        if not self.query_metrics:
            return {}
        
        recent_metrics = self.query_metrics[-100:]  # Last 100 queries
        
        # Calculate statistics
        total_queries = len(recent_metrics)
        slow_queries = sum(1 for m in recent_metrics if m.execution_time > self.slow_query_threshold)
        avg_execution_time = sum(m.execution_time for m in recent_metrics) / total_queries
        
        # Group by collection
        collection_stats = {}
        for metric in recent_metrics:
            if metric.collection not in collection_stats:
                collection_stats[metric.collection] = {
                    'count': 0,
                    'avg_time': 0,
                    'slow_queries': 0
                }
            
            collection_stats[metric.collection]['count'] += 1
            collection_stats[metric.collection]['avg_time'] += metric.execution_time
            if metric.execution_time > self.slow_query_threshold:
                collection_stats[metric.collection]['slow_queries'] += 1
        
        # Calculate averages per collection
        for stats in collection_stats.values():
            stats['avg_time'] /= stats['count']
        
        return {
            'total_queries': total_queries,
            'slow_queries': slow_queries,
            'slow_query_percentage': (slow_queries / total_queries) * 100,
            'avg_execution_time': avg_execution_time,
            'collection_stats': collection_stats,
            'cache_size': len(self.query_cache)
        }
    
    async def create_optimized_indexes(self):
        """Create optimized database indexes"""
        db = self.db
        
        # Products collection - compound indexes for common queries
        await db.products.create_indexes([
            IndexModel([("category", 1), ("stock", -1)]),  # Category with stock sorting
            IndexModel([("stock", 1), ("low_stock_threshold", 1)], 
                      partialFilterExpression={"stock": {"$lt": 100}}),  # Low stock products
            IndexModel([("name", "text"), ("category", "text")]),  # Text search
            IndexModel([("price", 1), ("category", 1)])  # Price range by category
        ])
        
        # Orders collection - optimized for analytics
        await db.orders.create_indexes([
            IndexModel([("user_id", 1), ("created_at", -1)]),  # User order history
            IndexModel([("created_at", -1), ("total_price", -1)]),  # Recent high-value orders
            IndexModel([("items.product_id", 1), ("created_at", -1)]),  # Product sales over time
            IndexModel([("status", 1), ("created_at", -1)])  # Status tracking
        ])
        
        # Users collection - authentication and role-based queries
        await db.users.create_indexes([
            IndexModel([("role", 1), ("created_at", -1)]),  # Users by role
            IndexModel([("last_login", -1)]),  # Recently active users
            IndexModel([("email", 1)], unique=True)  # Email lookup (already exists but ensuring)
        ])
        
        # Suppliers collection - purchase order optimization
        await db.suppliers.create_indexes([
            IndexModel([("name", 1), ("status", 1)]),  # Active suppliers
            IndexModel([("email", 1)], unique=True)  # Email lookup
        ])
        
        # Purchase orders collection - supplier and status tracking
        await db.purchase_orders.create_indexes([
            IndexModel([("supplier_id", 1), ("status", 1), ("created_at", -1)]),
            IndexModel([("status", 1), ("expected_delivery", 1)]),
            IndexModel([("created_at", -1)])
        ])
        
        logger.info("Optimized database indexes created successfully")
    
    def suggest_query_improvements(self) -> List[str]:
        """Analyze query patterns and suggest improvements"""
        suggestions = []
        stats = self.get_performance_stats()
        
        if not stats:
            return ["No query data available for analysis"]
        
        # Check for high slow query percentage
        if stats.get('slow_query_percentage', 0) > 10:
            suggestions.append(
                f"High slow query rate ({stats['slow_query_percentage']:.1f}%). "
                "Consider adding indexes or optimizing queries."
            )
        
        # Check cache efficiency
        if stats.get('cache_size', 0) > 1000:
            suggestions.append(
                "Large cache size detected. Consider implementing cache eviction policies."
            )
        
        # Analyze collection-specific performance
        collection_stats = stats.get('collection_stats', {})
        for collection, col_stats in collection_stats.items():
            if col_stats['avg_time'] > 500:  # 500ms threshold
                suggestions.append(
                    f"Collection '{collection}' has high average query time "
                    f"({col_stats['avg_time']:.1f}ms). Review query patterns."
                )
            
            if col_stats['slow_queries'] > col_stats['count'] * 0.2:  # 20% threshold
                suggestions.append(
                    f"Collection '{collection}' has high slow query rate. "
                    "Consider adding compound indexes."
                )
        
        if not suggestions:
            suggestions.append("Query performance looks good!")
        
        return suggestions

# Global query optimizer instance
query_optimizer: Optional[QueryOptimizer] = None

def get_query_optimizer(db: MongoClient) -> QueryOptimizer:
    """Get or create query optimizer instance"""
    global query_optimizer
    if query_optimizer is None:
        query_optimizer = QueryOptimizer(db)
    return query_optimizer

# Decorators for easy use
def optimized_find(collection_name: str, cache_ttl: int = 300):
    """Decorator for optimized find operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            optimizer = get_query_optimizer(kwargs.get('db'))
            query = kwargs.get('query', {})
            projection = kwargs.get('projection')
            limit = kwargs.get('limit')
            sort = kwargs.get('sort')
            
            return await optimizer.cached_find(
                collection_name, query, projection, limit, sort, cache_ttl
            )
        return wrapper
    return decorator

def optimized_aggregate(collection_name: str, cache_ttl: int = 300):
    """Decorator for optimized aggregation operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            optimizer = get_query_optimizer(kwargs.get('db'))
            pipeline = kwargs.get('pipeline', [])
            
            return await optimizer.cached_aggregate(collection_name, pipeline, cache_ttl)
        return wrapper
    return decorator
