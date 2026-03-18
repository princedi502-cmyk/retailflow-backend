"""
Database performance monitoring API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.router.dependency import get_current_user, require_owner
from app.core.rate_limit import limiter
from app.core.db_monitor import get_database_monitor, AlertLevel
from app.core.query_optimizer import get_query_optimizer
from app.db.mongodb import db_manager
from typing import Dict, Any, Optional
import asyncio

router = APIRouter(prefix="/database", tags=["database-monitoring"])

# Global monitor instance
db_monitor = get_database_monitor(db_manager.client)

@router.get("/performance")
@limiter.limit("100/minute")
async def get_performance_report(
    request: Request,
    user=Depends(require_owner)
):
    """Get comprehensive database performance report"""
    try:
        report = await db_monitor.get_performance_report()
        return {
            "success": True,
            "data": report
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate performance report: {str(e)}"
        )

@router.get("/performance/stats")
@limiter.limit("200/minute")
async def get_performance_stats(
    request: Request,
    user=Depends(require_owner)
):
    """Get query performance statistics"""
    try:
        optimizer = get_query_optimizer(client)
        stats = optimizer.get_performance_stats()
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance stats: {str(e)}"
        )

@router.get("/performance/alerts")
@limiter.limit("100/minute")
async def get_active_alerts(
    request: Request,
    level: Optional[str] = Query(None, description="Filter by alert level: info, warning, critical"),
    user=Depends(require_owner)
):
    """Get active performance alerts"""
    try:
        alert_level = None
        if level:
            try:
                alert_level = AlertLevel(level.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid alert level: {level}. Must be: info, warning, or critical"
                )
        
        alerts = db_monitor.get_active_alerts(alert_level)
        
        return {
            "success": True,
            "data": {
                "alerts": [
                    {
                        "level": alert.level.value,
                        "message": alert.message,
                        "metric_name": alert.metric_name,
                        "current_value": alert.current_value,
                        "threshold": alert.threshold,
                        "timestamp": alert.timestamp.isoformat()
                    }
                    for alert in alerts
                ],
                "total_count": len(alerts)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alerts: {str(e)}"
        )

@router.post("/performance/alerts/{metric_name}/resolve")
@limiter.limit("50/minute")
async def resolve_alert(
    metric_name: str,
    request: Request,
    user=Depends(require_owner)
):
    """Resolve alerts for a specific metric"""
    try:
        success = db_monitor.resolve_alert(metric_name)
        
        if success:
            return {
                "success": True,
                "message": f"Alerts for metric '{metric_name}' resolved successfully"
            }
        else:
            return {
                "success": False,
                "message": f"No active alerts found for metric '{metric_name}'"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve alerts: {str(e)}"
        )

@router.get("/performance/thresholds")
@limiter.limit("100/minute")
async def get_performance_thresholds(
    request: Request,
    user=Depends(require_owner)
):
    """Get current performance thresholds"""
    try:
        return {
            "success": True,
            "data": db_monitor.thresholds
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get thresholds: {str(e)}"
        )

@router.put("/performance/thresholds/{metric_name}")
@limiter.limit("50/minute")
async def update_performance_threshold(
    metric_name: str,
    request: Request,
    new_threshold: float,
    user=Depends(require_owner)
):
    """Update performance threshold for a metric"""
    try:
        if new_threshold <= 0:
            raise HTTPException(
                status_code=400,
                detail="Threshold must be greater than 0"
            )
        
        db_monitor.update_threshold(metric_name, new_threshold)
        
        return {
            "success": True,
            "message": f"Threshold for '{metric_name}' updated to {new_threshold}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update threshold: {str(e)}"
        )

@router.post("/performance/monitoring/start")
@limiter.limit("20/minute")
async def start_monitoring(
    request: Request,
    check_interval: int = Query(60, ge=10, le=300, description="Monitoring interval in seconds"),
    user=Depends(require_owner)
):
    """Start continuous performance monitoring"""
    try:
        await db_monitor.start_continuous_monitoring(check_interval)
        
        return {
            "success": True,
            "message": f"Continuous monitoring started with {check_interval}s interval"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start monitoring: {str(e)}"
        )

@router.post("/performance/monitoring/stop")
@limiter.limit("20/minute")
async def stop_monitoring(
    request: Request,
    user=Depends(require_owner)
):
    """Stop continuous performance monitoring"""
    try:
        await db_monitor.stop_continuous_monitoring()
        
        return {
            "success": True,
            "message": "Continuous monitoring stopped"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop monitoring: {str(e)}"
        )

@router.get("/performance/cache")
@limiter.limit("100/minute")
async def get_cache_info(
    request: Request,
    user=Depends(require_owner)
):
    """Get query cache information"""
    try:
        optimizer = get_query_optimizer(client)
        
        return {
            "success": True,
            "data": {
                "cache_size": len(optimizer.query_cache),
                "cache_ttl": optimizer.cache_ttl,
                "slow_query_threshold": optimizer.slow_query_threshold,
                "metrics_history": len(optimizer.query_metrics)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache info: {str(e)}"
        )

@router.delete("/performance/cache")
@limiter.limit("50/minute")
async def clear_cache(
    request: Request,
    pattern: Optional[str] = Query(None, description="Pattern to match for selective cache clearing"),
    user=Depends(require_owner)
):
    """Clear query cache"""
    try:
        optimizer = get_query_optimizer(client)
        optimizer.clear_cache(pattern)
        
        message = f"Cache cleared{' for pattern: ' + pattern if pattern else ''}"
        
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/performance/recommendations")
@limiter.limit("100/minute")
async def get_performance_recommendations(
    request: Request,
    user=Depends(require_owner)
):
    """Get performance optimization recommendations"""
    try:
        optimizer = get_query_optimizer(client)
        recommendations = optimizer.suggest_query_improvements()
        
        return {
            "success": True,
            "data": {
                "recommendations": recommendations,
                "total_count": len(recommendations)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )

@router.get("/health")
@limiter.limit("200/minute")
async def get_database_health(
    request: Request,
    user=Depends(get_current_user)
):
    """Get database health status"""
    try:
        health_check = db_monitor.check_connection_health()
        pool_stats = db_monitor.get_pool_stats()
        
        return {
            "success": True,
            "data": {
                "connection_health": health_check,
                "pool_stats": pool_stats,
                "monitoring_active": db_monitor.is_monitoring
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database health: {str(e)}"
        )
