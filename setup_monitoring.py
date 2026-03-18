#!/usr/bin/env python3
"""
Database Monitoring Setup Script for RetailFlow
Initializes and configures comprehensive database monitoring
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.db_monitor import get_database_monitor
from app.core.query_optimizer import get_query_optimizer
from app.db.mongodb import db_manager
from app.core.db_config import DatabaseConfig

async def setup_monitoring():
    """Setup and initialize database monitoring"""
    print("🔧 Setting up Database Monitoring for RetailFlow...")
    
    try:
        # Initialize database monitor
        print("\n📊 Initializing Database Monitor...")
        monitor = get_database_monitor(db_manager.client)
        config = monitor.config
        
        print(f"✅ Database Monitor initialized")
        print(f"   - Stats Enabled: {config.get('enable_stats', True)}")
        print(f"   - Safe Mode: {config.get('safe_mode', True)}")
        print(f"   - Read Only: {config.get('read_only', True)}")
        print(f"   - Stats Interval: {config.get('stats_interval', 60)}s")
        
        # Initialize query optimizer
        print("\n⚡ Initializing Query Optimizer...")
        optimizer = get_query_optimizer(db_manager.client)
        
        print(f"✅ Query Optimizer initialized")
        print(f"   - Cache TTL: {optimizer.cache_ttl}s")
        print(f"   - Slow Query Threshold: {optimizer.slow_query_threshold}ms")
        print(f"   - Max Metrics History: {optimizer.max_metrics_history}")
        
        # Create optimized indexes
        print("\n🗂️  Creating Optimized Database Indexes...")
        await optimizer.create_optimized_indexes()
        print("✅ Database indexes created successfully")
        
        # Test database connection and health
        print("\n🏥 Testing Database Health...")
        health = monitor.check_connection_health()
        pool_stats = monitor.get_pool_stats()
        
        print(f"✅ Database Health: {health['status']}")
        print(f"   - Response Time: {health.get('response_time_ms', 0):.2f}ms")
        if 'error' not in pool_stats:
            print(f"   - Pool Connections: {pool_stats.get('total_connections', 0)}/{pool_stats.get('max_pool_size', 0)}")
        
        # Get initial performance report
        print("\n📈 Generating Initial Performance Report...")
        report = await monitor.get_performance_report()
        
        if 'error' not in report:
            print("✅ Performance report generated")
            print(f"   - Active Alerts: {report.get('active_alerts', 0)}")
            alerts_summary = report.get('alerts_summary', {})
            print(f"   - Critical: {alerts_summary.get('critical', 0)}")
            print(f"   - Warning: {alerts_summary.get('warning', 0)}")
            print(f"   - Info: {alerts_summary.get('info', 0)}")
        
        # Get performance recommendations
        print("\n💡 Performance Recommendations:")
        recommendations = optimizer.suggest_query_improvements()
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        print("\n🎉 Database Monitoring Setup Complete!")
        print("\n📋 Next Steps:")
        print("   1. Start your FastAPI application")
        print("   2. Visit /database/performance to view monitoring dashboard")
        print("   3. Use API endpoints to manage monitoring:")
        print("      - POST /database/performance/monitoring/start")
        print("      - GET /database/performance/alerts")
        print("      - GET /database/health")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        return False

async def test_monitoring_endpoints():
    """Test monitoring endpoints (requires running server)"""
    print("\n🧪 Testing Monitoring Endpoints...")
    
    import httpx
    
    base_url = "http://localhost:8000"
    endpoints = [
        "/database/health",
        "/database/performance/stats",
        "/database/performance/thresholds"
    ]
    
    async with httpx.AsyncClient() as client:
        for endpoint in endpoints:
            try:
                response = await client.get(f"{base_url}{endpoint}")
                if response.status_code == 200:
                    print(f"✅ {endpoint} - OK")
                else:
                    print(f"⚠️  {endpoint} - {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} - {str(e)}")

def print_monitoring_info():
    """Print monitoring configuration and usage information"""
    print("\n" + "="*60)
    print("📊 DATABASE MONITORING INFORMATION")
    print("="*60)
    
    config = DatabaseConfig.get_monitoring_config()
    
    print("\n🔧 Configuration:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    
    print("\n🌐 API Endpoints:")
    endpoints = [
        ("GET /database/health", "Database health status"),
        ("GET /database/performance", "Comprehensive performance report"),
        ("GET /database/performance/stats", "Query performance statistics"),
        ("GET /database/performance/alerts", "Active performance alerts"),
        ("POST /database/performance/monitoring/start", "Start continuous monitoring"),
        ("POST /database/performance/monitoring/stop", "Stop continuous monitoring"),
        ("GET /database/performance/cache", "Query cache information"),
        ("DELETE /database/performance/cache", "Clear query cache"),
        ("GET /database/performance/recommendations", "Performance recommendations")
    ]
    
    for endpoint, description in endpoints:
        print(f"   {endpoint:<45} - {description}")
    
    print("\n⚠️  Important Notes:")
    print("   - Monitoring runs in safe mode by default")
    print("   - All operations are read-only unless explicitly disabled")
    print("   - Alerts are automatically generated based on thresholds")
    print("   - Query caching improves performance for repeated queries")
    print("   - Slow queries are logged and tracked")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Database Monitoring")
    parser.add_argument("--test", action="store_true", help="Test monitoring endpoints")
    parser.add_argument("--info", action="store_true", help="Show monitoring information")
    
    args = parser.parse_args()
    
    if args.info:
        print_monitoring_info()
    elif args.test:
        asyncio.run(test_monitoring_endpoints())
    else:
        success = asyncio.run(setup_monitoring())
        if success:
            print_monitoring_info()
        else:
            sys.exit(1)
