import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 300  # 5 minutes default
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _serialize(self, data: Any) -> bytes:
        """Serialize data for storage"""
        return pickle.dumps(data)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize data from storage"""
        return pickle.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        if not self.redis_client:
            return None
        
        try:
            data = await self.redis_client.get(key)
            if data:
                return self._deserialize(data)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        return None
    
    async def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set data in cache"""
        if not self.redis_client:
            return False
        
        try:
            serialized_data = self._serialize(data)
            cache_ttl = ttl or self.default_ttl
            await self.redis_client.setex(key, cache_ttl, serialized_data)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete data from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear_all_cache(self) -> int:
        """Clear all cache keys - for debugging purposes"""
        if not self.redis_client:
            return 0
        
        try:
            # Get all keys
            keys = await self.redis_client.keys("*")
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Clear all cache error: {e}")
            return 0

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

# Global cache manager instance
cache_manager = CacheManager()

# Cache key generators
def product_cache_key(product_id: str = None, page: int = None, limit: int = None, search: str = None) -> str:
    """Generate cache key for product-related data"""
    if product_id:
        return f"product:{product_id}"
    elif search:
        return f"products:search:{search}:{page}:{limit}"
    else:
        return f"products:list:{page}:{limit}"

def analytics_cache_key(endpoint: str, **params) -> str:
    """Generate cache key for analytics data"""
    param_str = ":".join(f"{k}:{v}" for k, v in sorted(params.items()) if v is not None)
    return f"analytics:{endpoint}:{param_str}" if param_str else f"analytics:{endpoint}"

def supplier_cache_key(supplier_id: str = None, page: int = None, limit: int = None) -> str:
    """Generate cache key for supplier data"""
    if supplier_id:
        return f"supplier:{supplier_id}"
    else:
        return f"suppliers:list:{page}:{limit}"

# Cache TTL constants
class CacheTTL:
    VERY_SHORT = 60      # 1 minute - for real-time data
    SHORT = 300          # 5 minutes - default
    MEDIUM = 900         # 15 minutes - for moderately changing data
    LONG = 3600          # 1 hour - for relatively static data
    VERY_LONG = 86400    # 24 hours - for very static data
