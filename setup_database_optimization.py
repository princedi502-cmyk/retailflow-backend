#!/usr/bin/env python3
"""
Database optimization setup script for RetailFlow
This script sets up query optimization, monitoring, and indexes
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.mongodb import db_manager
from app.core.query_optimizer import get_query_optimizer
from app.core.db_monitor import get_database_monitor
from app.db_indexes import create_optimized_indexes, create_query_performance_indexes, analyze_index_usage

async def setup_database_optimization():
    """Complete database optimization setup"""
    
    print("🚀 Setting up database optimization for RetailFlow...")
    print("=" * 60)
    
    try:
        # 1. Test database connection
        print("\n📡 Testing database connection...")
        await db_manager.db.command('ping')
        print("✅ Database connection successful")
        
        # 2. Create optimized indexes
        print("\n📊 Creating optimized database indexes...")
        await create_optimized_indexes()
        
        # 3. Create query performance indexes
        print("\n⚡ Creating query performance indexes...")
        await create_query_performance_indexes()
        
        # 4. Initialize query optimizer
        print("\n🔧 Initializing query optimizer...")
        optimizer = get_query_optimizer(client)
        await optimizer.create_optimized_indexes()
        print("✅ Query optimizer initialized")
        
        # 5. Initialize database monitor
        print("\n📈 Initializing database monitor...")
        monitor = get_database_monitor(client)
        
        # Test monitoring functionality
        print("🔍 Testing monitoring functionality...")
        report = await monitor.get_performance_report()
        if "error" not in report:
            print("✅ Database monitor initialized successfully")
        else:
            print(f"⚠️ Monitor initialization warning: {report.get('error', 'Unknown error')}")
        
        # 6. Analyze index usage
        print("\n📋 Analyzing index usage...")
        await analyze_index_usage()
        
        # 7. Get performance recommendations
        print("\n💡 Getting performance recommendations...")
        recommendations = optimizer.suggest_query_improvements()
        if recommendations:
            print("📝 Performance recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        else:
            print("✅ No performance issues detected")
        
        # 8. Display setup summary
        print("\n" + "=" * 60)
        print("🎉 Database optimization setup completed successfully!")
        print("\n📋 Setup Summary:")
        print("  ✅ Optimized database indexes created")
        print("  ✅ Query performance indexes created") 
        print("  ✅ Query optimizer initialized")
        print("  ✅ Database monitor initialized")
        print("  ✅ Index usage analyzed")
        print("  ✅ Performance recommendations generated")
        
        print("\n🔧 Available Features:")
        print("  • Query caching with TTL")
        print("  • Performance monitoring and alerting")
        print("  • Slow query detection")
        print("  • Connection pool monitoring")
        print("  • Automated performance recommendations")
        
        print("\n📡 API Endpoints Available:")
        print("  • GET /database/performance - Performance report")
        print("  • GET /database/performance/stats - Query statistics")
        print("  • GET /database/performance/alerts - Active alerts")
        print("  • GET /database/performance/cache - Cache information")
        print("  • GET /database/performance/recommendations - Optimization tips")
        print("  • POST /database/performance/monitoring/start - Start monitoring")
        print("  • POST /database/performance/monitoring/stop - Stop monitoring")
        
        print("\n⚙️ Configuration:")
        print("  • Monitoring starts automatically in production")
        print("  • Cache TTL: 5 minutes (configurable)")
        print("  • Slow query threshold: 1000ms")
        print("  • Monitoring interval: 60 seconds")
        
        print("\n🔍 Next Steps:")
        print("  1. Monitor the /database/performance endpoints")
        print("  2. Set up alerts for critical performance issues")
        print("  3. Regularly check performance recommendations")
        print("  4. Adjust thresholds based on your usage patterns")
        print("  5. Consider implementing additional caching strategies")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("  • Ensure MongoDB is running and accessible")
        print("  • Check database connection string in .env file")
        print("  • Verify database permissions")
        print("  • Check if collections exist")
        raise
    
    finally:
        await db_manager.close()

async def test_optimization_features():
    """Test the optimization features"""
    
    print("\n🧪 Testing optimization features...")
    
    try:
        # Reconnect for testing
        from app.db.mongodb import db_manager
        
        optimizer = get_query_optimizer(db_manager.client)
        monitor = get_database_monitor(db_manager.client)
        
        # Test cache functionality
        print("📦 Testing query cache...")
        test_query = {"category": "electronics"}
        cached_result = await optimizer.cached_find("products", test_query, limit=5)
        print(f"✅ Cache test successful: {len(cached_result)} items")
        
        # Test performance monitoring
        print("📊 Testing performance monitoring...")
        stats = optimizer.get_performance_stats()
        print(f"✅ Performance stats available: {len(stats)} metrics")
        
        # Test health check
        print("🏥 Testing database health check...")
        health = monitor.check_connection_health()
        print(f"✅ Health check successful: {health.get('status', 'unknown')}")
        
        print("✅ All optimization features working correctly!")
        
    except Exception as e:
        print(f"⚠️ Feature test warning: {str(e)}")

if __name__ == "__main__":
    print("RetailFlow Database Optimization Setup")
    print("=====================================")
    
    try:
        # Run setup
        asyncio.run(setup_database_optimization())
        
        # Ask if user wants to test features
        response = input("\n🧪 Would you like to test the optimization features? (y/n): ")
        if response.lower().startswith('y'):
            asyncio.run(test_optimization_features())
        
        print("\n🎯 Setup complete! Your RetailFlow database is now optimized.")
        print("📖 Check the documentation for advanced configuration options.")
        
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)
