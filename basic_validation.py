#!/usr/bin/env python3
"""
Simple import test for Employee Performance System
Tests only imports without database connections
"""

import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """Test that basic modules can be imported successfully"""
    print("🧪 Testing Basic Imports")
    print("=" * 50)
    
    try:
        # Test models only
        print("1. Testing employee performance models...")
        from app.models.employee_performance_model import (
            EmployeePerformanceCreate, EmployeePerformanceUpdate, EmployeePerformanceResponse,
            PerformanceReviewCreate, PerformanceReviewResponse, SalesHistoryEntry,
            EmployeeSalesHistoryResponse, LeaderboardEntry, WorkforceAnalytics
        )
        print("✅ Employee performance models imported successfully")
        
        # Test schemas only
        print("2. Testing employee performance schemas...")
        from app.schemas.employee_performance_schema import (
            EmployeePerformanceRequest, EmployeePerformanceUpdateRequest, PerformanceReviewRequest,
            SalesHistoryRequest, LeaderboardRequest, WorkforceAnalyticsRequest,
            EmployeePerformanceResponse, PerformanceReviewResponse, EmployeeSalesHistoryResponse,
            LeaderboardResponse, WorkforceAnalyticsResponse
        )
        print("✅ Employee performance schemas imported successfully")
        
        # Test API router only
        print("3. Testing employee performance API router...")
        from app.api.router.employee_performance import router
        print("✅ Employee performance API router imported successfully")
        
        # Test database indexes only
        print("4. Testing employee performance database indexes...")
        from app.db.employee_performance_indexes import (
            create_employee_performance_indexes, get_employee_performance_index_stats,
            drop_employee_performance_indexes, initialize_employee_performance_indexes
        )
        print("✅ Employee performance database indexes imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_creation():
    """Test that models can be created without database"""
    print("\n🔧 Testing Model Creation")
    print("=" * 50)
    
    try:
        from app.models.employee_performance_model import EmployeePerformanceCreate, PerformanceReviewCreate
        from app.schemas.employee_performance_schema import PerformanceReviewRequest, LeaderboardRequest
        from datetime import datetime
        
        # Test employee performance model
        print("1. Testing employee performance model creation...")
        performance_data = EmployeePerformanceCreate(
            employee_id="507f1f77bcf86cd799439011",
            total_sales=1000.50,
            total_orders=25,
            average_order_value=40.02,
            conversion_rate=15.5,
            period_start=datetime.now(),
            period_end=datetime.now()
        )
        print(f"✅ Employee performance model created: ${performance_data.total_sales} in sales")
        
        # Test performance review model
        print("2. Testing performance review model creation...")
        review_data = PerformanceReviewCreate(
            employee_id="507f1f77bcf86cd799439011",
            reviewer_id="507f1f77bcf86cd799439011",
            review_type="monthly",
            rating=4.5,
            strengths=["Good communication", "High sales"],
            areas_for_improvement=["Time management"],
            goals=["Increase sales by 10%"],
            comments="Good performance",
            review_date=datetime.now()
        )
        print(f"✅ Performance review model created: {review_data.rating}/5 rating")
        
        # Test request models
        print("3. Testing request models...")
        review_request = PerformanceReviewRequest(
            reviewer_id="507f1f77bcf86cd799439011",
            review_type="monthly",
            rating=4.5,
            strengths=["Good communication"],
            areas_for_improvement=["Time management"],
            goals=["Increase sales"],
            comments="Good performance"
        )
        leaderboard_request = LeaderboardRequest(limit=10)
        
        print(f"✅ Request models created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_routes():
    """Test that API routes are properly defined"""
    print("\n🌐 Testing API Routes")
    print("=" * 50)
    
    try:
        from app.api.router.employee_performance import router
        
        # Check that routes are defined
        routes = [route.path for route in router.routes]
        expected_routes = [
            "/employees/performance/{employee_id}",
            "/employees/performance/leaderboard", 
            "/employees/{employee_id}/sales-history",
            "/employees/{employee_id}/performance-review",
            "/employees/{employee_id}/performance-reviews",
            "/employees/analytics",
            "/employees/{employee_id}/performance-summary"
        ]
        
        print("1. Checking API routes...")
        found_routes = 0
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✅ Route {route} found")
                found_routes += 1
            else:
                print(f"❌ Route {route} missing")
        
        print(f"✅ Total routes found: {found_routes}/{len(expected_routes)}")
        
        return found_routes == len(expected_routes)
        
    except Exception as e:
        print(f"❌ API route test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Employee Performance System Basic Validation")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Model Creation", test_model_creation), 
        ("API Routes", test_api_routes)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Tests...")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed! Employee Performance System structure is correct.")
        print("\n📝 Next Steps:")
        print("1. Start the backend server")
        print("2. Create database indexes with: python -c 'from app.db_indexes import create_indexes; create_indexes()'")
        print("3. Test the API endpoints")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
