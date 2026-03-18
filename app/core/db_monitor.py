"""
Advanced database monitoring module with performance tracking and alerting
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
from dataclasses import dataclass, field
from enum import Enum
from pymongo import MongoClient
from app.core.db_config import DatabaseConfig
from app.core.query_optimizer import get_query_optimizer

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceAlert:
    """Performance alert data structure"""
    level: AlertLevel
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class DatabaseMonitor:
    """Advanced database performance monitoring with alerting"""
    
    def __init__(self, client: MongoClient):
        self.client = client
        self.config = DatabaseConfig.get_monitoring_config()
        self.last_stats_time = 0
        self.alerts: List[PerformanceAlert] = []
        self.max_alerts_history = 1000
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Performance thresholds
        self.thresholds = {
            'slow_query_percentage': 10.0,  # percentage
            'avg_execution_time': 500.0,    # milliseconds
            'connection_pool_usage': 80.0,  # percentage
            'memory_usage': 85.0,           # percentage
            'response_time': 1000.0          # milliseconds
        }
        
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics"""
        try:
            pool = self.client._topology._servers.get('server0', None)
            if pool and hasattr(pool, 'pool'):
                connection_pool = pool.pool
                return {
                    "active_connections": getattr(connection_pool, 'active_sockets', 0),
                    "available_connections": getattr(connection_pool, 'available_sockets', 0),
                    "total_connections": getattr(connection_pool, 'total_sockets', 0),
                    "max_pool_size": getattr(connection_pool, 'max_pool_size', 0),
                    "min_pool_size": getattr(connection_pool, 'min_pool_size', 0)
                }
            return {"error": "Pool statistics not available"}
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {"error": str(e)}
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        try:
            from app.db.mongodb import db_manager
            database = db_manager.db
            
            # Get server status
            server_status = database.command("serverStatus")
            
            # Get database stats
            db_stats = database.command("dbStats")
            
            return {
                "server": {
                    "connections": server_status.get("connections", {}),
                    "network": server_status.get("network", {}),
                    "opcounters": server_status.get("opcounters", {}),
                    "uptime": server_status.get("uptime", 0)
                },
                "database": {
                    "collections": db_stats.get("collections", 0),
                    "dataSize": db_stats.get("dataSize", 0),
                    "storageSize": db_stats.get("storageSize", 0),
                    "indexes": db_stats.get("indexes", 0),
                    "indexSize": db_stats.get("indexSize", 0)
                }
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}
    
    def check_connection_health(self) -> Dict[str, Any]:
        """Check database connection health"""
        try:
            start_time = time.time()
            self.client.admin.command('ping')
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            health_status = "healthy" if response_time < 1000 else "degraded"
            if response_time > 5000:
                health_status = "unhealthy"
            
            return {
                "status": health_status,
                "response_time_ms": round(response_time, 2),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def log_slow_queries(self, threshold_ms: Optional[int] = None) -> None:
        """Log slow queries (placeholder for implementation)"""
        if not self.config.get("log_slow_queries", False):
            return
            
        threshold = threshold_ms or self.config.get("slow_query_threshold", 1000)
        # Implementation would require query profiling setup
        logger.info(f"Slow query monitoring enabled with threshold: {threshold_ms}ms")
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report with alerts"""
        current_time = time.time()
        
        # Check if enough time has passed since last stats collection
        if current_time - self.last_stats_time < self.config.get("stats_interval", 60):
            return {"message": "Stats collection not due yet"}
        
        self.last_stats_time = current_time
        
        # Get basic stats
        pool_stats = self.get_pool_stats()
        database_stats = self.get_database_stats()
        health_check = self.check_connection_health()
        
        # Get query optimizer stats
        optimizer = get_query_optimizer(self.client)
        query_stats = optimizer.get_performance_stats()
        
        # Check for performance issues and create alerts
        await self._check_performance_thresholds(pool_stats, database_stats, health_check, query_stats)
        
        report = {
            "timestamp": current_time,
            "pool_stats": pool_stats,
            "database_stats": database_stats,
            "health_check": health_check,
            "query_stats": query_stats,
            "active_alerts": len(self.get_active_alerts()),
            "alerts_summary": self._get_alerts_summary()
        }
        
        return report
    
    async def _check_performance_thresholds(self, pool_stats: Dict, database_stats: Dict, 
                                          health_check: Dict, query_stats: Dict):
        """Check performance thresholds and create alerts"""
        
        # Check connection pool usage
        if "total_connections" in pool_stats and "max_pool_size" in pool_stats:
            usage_percent = (pool_stats["total_connections"] / pool_stats["max_pool_size"]) * 100
            if usage_percent > self.thresholds['connection_pool_usage']:
                await self._create_alert(
                    AlertLevel.WARNING if usage_percent < 95 else AlertLevel.CRITICAL,
                    f"High connection pool usage: {usage_percent:.1f}%",
                    "connection_pool_usage",
                    usage_percent,
                    self.thresholds['connection_pool_usage']
                )
        
        # Check response time
        response_time = health_check.get("response_time_ms", 0)
        if response_time > self.thresholds['response_time']:
            await self._create_alert(
                AlertLevel.WARNING if response_time < 2000 else AlertLevel.CRITICAL,
                f"High database response time: {response_time:.1f}ms",
                "response_time",
                response_time,
                self.thresholds['response_time']
            )
        
        # Check query performance
        if query_stats:
            slow_query_pct = query_stats.get('slow_query_percentage', 0)
            if slow_query_pct > self.thresholds['slow_query_percentage']:
                await self._create_alert(
                    AlertLevel.WARNING if slow_query_pct < 20 else AlertLevel.CRITICAL,
                    f"High slow query rate: {slow_query_pct:.1f}%",
                    "slow_query_percentage",
                    slow_query_pct,
                    self.thresholds['slow_query_percentage']
                )
            
            avg_time = query_stats.get('avg_execution_time', 0)
            if avg_time > self.thresholds['avg_execution_time']:
                await self._create_alert(
                    AlertLevel.WARNING if avg_time < 1000 else AlertLevel.CRITICAL,
                    f"High average query time: {avg_time:.1f}ms",
                    "avg_execution_time",
                    avg_time,
                    self.thresholds['avg_execution_time']
                )
    
    async def _create_alert(self, level: AlertLevel, message: str, 
                          metric_name: str, current_value: float, threshold: float):
        """Create a new performance alert"""
        # Check if similar alert already exists and is unresolved
        existing_alert = next(
            (alert for alert in self.alerts 
             if alert.metric_name == metric_name 
             and not alert.resolved),
            None
        )
        
        if existing_alert:
            # Update existing alert
            existing_alert.current_value = current_value
            existing_alert.timestamp = datetime.now(timezone.utc)
            return
        
        # Create new alert
        alert = PerformanceAlert(
            level=level,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold
        )
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts_history:
            self.alerts = self.alerts[-self.max_alerts_history:]
        
        # Log alert
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.CRITICAL: logger.error
        }.get(level, logger.info)
        
        log_level(f"DB Performance Alert: {message}")
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[PerformanceAlert]:
        """Get all active (unresolved) alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        if level:
            active_alerts = [alert for alert in active_alerts if alert.level == level]
        
        return active_alerts
    
    def _get_alerts_summary(self) -> Dict[str, int]:
        """Get summary of alerts by level"""
        active_alerts = self.get_active_alerts()
        return {
            'critical': len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
            'warning': len([a for a in active_alerts if a.level == AlertLevel.WARNING]),
            'info': len([a for a in active_alerts if a.level == AlertLevel.INFO])
        }
    
    def resolve_alert(self, metric_name: str) -> bool:
        """Mark alerts for a metric as resolved"""
        resolved_count = 0
        for alert in self.alerts:
            if alert.metric_name == metric_name and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                resolved_count += 1
        
        if resolved_count > 0:
            logger.info(f"Resolved {resolved_count} alerts for metric: {metric_name}")
            return True
        return False
    
    async def start_continuous_monitoring(self, check_interval: int = 60):
        """Start continuous performance monitoring"""
        if self.is_monitoring:
            logger.warning("Monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(check_interval))
        logger.info("Continuous database monitoring started")
    
    async def stop_continuous_monitoring(self):
        """Stop continuous performance monitoring"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Continuous database monitoring stopped")
    
    async def _monitor_loop(self, check_interval: int):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self.get_performance_report()
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(check_interval)
    
    def update_threshold(self, metric_name: str, new_threshold: float):
        """Update performance threshold"""
        if metric_name in self.thresholds:
            old_threshold = self.thresholds[metric_name]
            self.thresholds[metric_name] = new_threshold
            logger.info(f"Updated {metric_name} threshold: {old_threshold} -> {new_threshold}")
        else:
            logger.warning(f"Unknown metric: {metric_name}")

# Global monitor instance
db_monitor: Optional[DatabaseMonitor] = None

def get_database_monitor(db_client) -> DatabaseMonitor:
    """Get or create database monitor instance"""
    global db_monitor
    if db_monitor is None:
        db_monitor = DatabaseMonitor(db_client)
    return db_monitor

# Initialize monitor when imported (lazy initialization)
# db_monitor = get_database_monitor(db_manager.client)
