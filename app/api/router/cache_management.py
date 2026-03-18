from fastapi import APIRouter, Depends, HTTPException
from app.api.router.dependency import require_owner
from app.core.cache import cache_manager
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache-management"])

@router.delete("/clear")
async def clear_all_cache(user=Depends(require_owner)):
    """Clear all cached data - owner only"""
    try:
        # First try to clear all cache using the new method
        total_deleted = await cache_manager.clear_all_cache()
        
        # If that doesn't work, fall back to pattern clearing
        if total_deleted == 0:
            patterns = [
                "products:*",
                "analytics:*", 
                "suppliers:*",
                "sales_summary:*",
                "agg_*"
            ]
            
            total_deleted = 0
            for pattern in patterns:
                deleted = await cache_manager.delete_pattern(pattern)
                total_deleted += deleted
            
        return {
            "message": "Cache cleared successfully",
            "total_keys_deleted": total_deleted,
            "patterns_cleared": patterns
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@router.delete("/clear/{cache_type}")
async def clear_cache_type(cache_type: str, user=Depends(require_owner)):
    """Clear specific type of cache - owner only"""
    valid_types = ["products", "analytics", "suppliers"]
    
    if cache_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cache type. Must be one of: {valid_types}"
        )
    
    try:
        pattern = f"{cache_type}:*"
        deleted = await cache_manager.delete_pattern(pattern)
        
        return {
            "message": f"{cache_type.capitalize()} cache cleared successfully",
            "keys_deleted": deleted
        }
    except Exception as e:
        logger.error(f"Error clearing {cache_type} cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear {cache_type} cache")

@router.delete("/pattern/{pattern}")
async def delete_cache_pattern(pattern: str, user=Depends(require_owner)):
    """Delete cache keys matching pattern"""
    try:
        deleted_count = await cache_manager.delete_pattern(pattern)
        return {
            "message": f"Deleted {deleted_count} cache keys matching pattern: {pattern}",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete cache pattern: {str(e)}"
        )

@router.get("/stats")
async def get_cache_stats(user=Depends(require_owner)):
    """Get cache statistics - owner only"""
    try:
        # This would require Redis INFO command or similar
        # For now, return basic info
        return {
            "status": "connected" if cache_manager.redis_client else "disconnected",
            "message": "Cache statistics available",
            "note": "Detailed statistics require Redis INFO command implementation"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")

@router.post("/warmup")
async def warmup_cache(user=Depends(require_owner)):
    """Warm up cache with frequently accessed data - owner only"""
    try:
        # This would require implementing specific warmup logic
        # For now, just return a message
        return {
            "message": "Cache warmup initiated",
            "note": "Specific warmup logic needs to be implemented based on usage patterns"
        }
    except Exception as e:
        logger.error(f"Error during cache warmup: {e}")
        raise HTTPException(status_code=500, detail="Failed to warmup cache")
