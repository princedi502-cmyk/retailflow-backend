"""
MongoDB Optimization Validation Script
Validates that all optimizations are properly implemented and working
"""

import asyncio
import sys
import logging
from datetime import datetime, timezone

# Add the project root to the path
sys.path.append('/home/di-01/Desktop/prince/basics/Retail-flow/retail-backend')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_optimizations():
    """Validate all MongoDB optimizations"""
    
    print("🔍 MongoDB Optimization Validation Started...")
    print("=" * 50)
    
    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }
    
    # 1. Validate caching infrastructure
    try:
        from app.core.optimized_aggregations import aggregation_optimizer, OptimizedPipelines
        print("✅ Caching infrastructure imported successfully")
        results["passed"].append("Caching infrastructure")
    except Exception as e:
        print(f"❌ Caching infrastructure failed: {str(e)}")
        results["failed"].append(f"Caching infrastructure: {str(e)}")
    
    # 2. Validate optimized pipelines
    try:
        # Test that pipelines can be generated
        top_products_pipeline = OptimizedPipelines.top_products_pipeline(limit=5)
        category_pipeline = OptimizedPipelines.category_sales_pipeline(limit=10)
        employee_pipeline = OptimizedPipelines.employee_performance_pipeline(limit=20)
        
        print("✅ Optimized pipelines generated successfully")
        results["passed"].append("Optimized pipelines")
    except Exception as e:
        print(f"❌ Optimized pipelines failed: {str(e)}")
        results["failed"].append(f"Optimized pipelines: {str(e)}")
    
    # 3. Validate database connection
    try:
        from app.db.mongodb import db_manager
        
        # Test basic connection
        await db_manager.db.command("ping")
        print("✅ Database connection successful")
        results["passed"].append("Database connection")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        results["failed"].append(f"Database connection: {str(e)}")
    
    # 4. Validate analytics endpoints
    try:
        from app.api.router.analytics import router
        
        # Check that router has the expected endpoints
        routes = [route.path for route in router.routes]
        expected_routes = [
            "/revenue",
            "/top-products", 
            "/worst-products",
            "/category-sales",
            "/sales-by-employee",
            "/monthly-revenue",
            "/items-sold",
            "/this-month",
            "/low-stock-products",
            "/unsold-products"
        ]
        
        missing_routes = [route for route in expected_routes if route not in routes]
        if not missing_routes:
            print("✅ All analytics endpoints present")
            results["passed"].append("Analytics endpoints")
        else:
            print(f"⚠️  Missing analytics routes: {missing_routes}")
            results["warnings"].append(f"Missing routes: {missing_routes}")
            
    except Exception as e:
        print(f"❌ Analytics endpoints validation failed: {str(e)}")
        results["failed"].append(f"Analytics endpoints: {str(e)}")
    
    # 5. Validate cache manager
    try:
        from app.core.cache import cache_manager
        
        # Test basic cache operations
        test_key = "validation_test"
        await cache_manager.set(test_key, "test_value", ttl=60)
        cached_value = await cache_manager.get(test_key)
        await cache_manager.delete(test_key)
        
        if cached_value == "test_value":
            print("✅ Cache manager working correctly")
            results["passed"].append("Cache manager")
        else:
            print("❌ Cache manager not working correctly")
            results["failed"].append("Cache manager: value mismatch")
            
    except Exception as e:
        print(f"❌ Cache manager validation failed: {str(e)}")
        results["failed"].append(f"Cache manager: {str(e)}")
    
    # 6. Check for direct aggregation calls (should be none)
    try:
        import os
        import re
        
        analytics_file = "/home/di-01/Desktop/prince/basics/Retail-flow/retail-backend/app/api/router/analytics.py"
        
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                content = f.read()
                
            # Look for direct aggregation calls
            direct_aggregations = re.findall(r'\.aggregate\(', content)
            
            if len(direct_aggregations) == 0:
                print("✅ No direct aggregation calls found (all using cached version)")
                results["passed"].append("Direct aggregation cleanup")
            else:
                print(f"⚠️  Found {len(direct_aggregations)} direct aggregation calls")
                results["warnings"].append(f"Direct aggregations: {len(direct_aggregations)}")
        else:
            print("❌ Analytics file not found")
            results["failed"].append("Analytics file missing")
            
    except Exception as e:
        print(f"❌ Direct aggregation check failed: {str(e)}")
        results["failed"].append(f"Direct aggregation check: {str(e)}")
    
    # 7. Performance test
    try:
        import time
        
        start_time = time.time()
        
        # Test a simple cached aggregation
        pipeline = [{"$count": "test_count"}]
        result = await aggregation_optimizer.optimized_aggregate(
            collection_name="orders",
            pipeline=pipeline,
            cache_key="validation_test",
            cache_ttl=60
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        if execution_time < 1000:  # Should be very fast with caching
            print(f"✅ Performance test passed ({execution_time:.2f}ms)")
            results["passed"].append("Performance test")
        else:
            print(f"⚠️  Performance test slow ({execution_time:.2f}ms)")
            results["warnings"].append(f"Performance: {execution_time:.2f}ms")
            
    except Exception as e:
        print(f"❌ Performance test failed: {str(e)}")
        results["failed"].append(f"Performance test: {str(e)}")
    
    # Results Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS SUMMARY")
    print("=" * 50)
    
    print(f"✅ Passed: {len(results['passed'])}")
    for item in results['passed']:
        print(f"   • {item}")
    
    if results['warnings']:
        print(f"⚠️  Warnings: {len(results['warnings'])}")
        for item in results['warnings']:
            print(f"   • {item}")
    
    if results['failed']:
        print(f"❌ Failed: {len(results['failed'])}")
        for item in results['failed']:
            print(f"   • {item}")
    
    # Overall status
    total_checks = len(results['passed']) + len(results['warnings']) + len(results['failed'])
    success_rate = (len(results['passed']) / total_checks) * 100
    
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 OPTIMIZATION COMPLETE: System is ready for production!")
    elif success_rate >= 75:
        print("⚠️  OPTIMIZATION MOSTLY COMPLETE: Minor issues to address")
    else:
        print("❌ OPTIMIZATION INCOMPLETE: Significant issues need resolution")
    
    return results

if __name__ == "__main__":
    asyncio.run(validate_optimizations())
