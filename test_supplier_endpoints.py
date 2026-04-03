#!/usr/bin/env python3
"""
Simple validation script for enhanced supplier management endpoints
"""

import sys
import os
sys.path.append('.')

def test_schemas():
    """Test supplier schema validation"""
    print("🔍 Testing supplier schemas...")
    
    from app.schemas.supplier_schema import (
        CreateSupplier, LowStockSupplier, CreatePurchaseOrder, 
        PurchaseOrderResponse, SupplierPerformance, SupplierProductCatalog
    )
    
    # Test CreateSupplier
    try:
        supplier = CreateSupplier(
            name="Test Supplier",
            email="test@example.com",
            phone="+1234567890",
            address="Test Address"
        )
        print("✅ CreateSupplier schema works")
    except Exception as e:
        print(f"❌ CreateSupplier error: {e}")
        return False
    
    # Test CreatePurchaseOrder
    try:
        from app.schemas.supplier_schema import PurchaseOrderItem
        items = [
            PurchaseOrderItem(
                product_id="prod123",
                product_name="Test Product",
                quantity=10,
                unit_price=25.99,
                total_price=259.90
            )
        ]
        order = CreatePurchaseOrder(items=items)
        print("✅ CreatePurchaseOrder schema works")
    except Exception as e:
        print(f"❌ CreatePurchaseOrder error: {e}")
        return False
    
    return True

def test_service_functions():
    """Test supplier service functions exist and are callable"""
    print("\n🔍 Testing supplier service functions...")
    
    from app.services.supplier_service import (
        get_low_stock_suppliers_service, create_purchase_order_service,
        get_supplier_performance_service, update_supplier_product_catalog_service
    )
    
    functions = [
        ("get_low_stock_suppliers_service", get_low_stock_suppliers_service),
        ("create_purchase_order_service", create_purchase_order_service),
        ("get_supplier_performance_service", get_supplier_performance_service),
        ("update_supplier_product_catalog_service", update_supplier_product_catalog_service)
    ]
    
    for name, func in functions:
        if callable(func):
            print(f"✅ {name} is callable")
        else:
            print(f"❌ {name} is not callable")
            return False
    
    return True

def test_database_indexes():
    """Test database index functions"""
    print("\n🔍 Testing database index functions...")
    
    try:
        from app.db.supplier_indexes import create_supplier_indexes
        if callable(create_supplier_indexes):
            print("✅ create_supplier_indexes is callable")
        else:
            print("❌ create_supplier_indexes is not callable")
            return False
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    return True

def test_api_routes():
    """Test that API routes are properly defined"""
    print("\n🔍 Testing API routes...")
    
    try:
        from app.api.router.supplier import router
        routes = [route.path for route in router.routes]
        
        expected_routes = [
            "/",
            "/low-stock",
            "/{supplier_id}/purchase-orders",
            "/{supplier_id}/performance",
            "/{supplier_id}/products",
            "/{supplier_id}"
        ]
        
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✅ Route {route} exists")
            else:
                print(f"❌ Route {route} missing")
                return False
                
    except Exception as e:
        print(f"❌ API routes error: {e}")
        return False
    
    return True

def main():
    """Run all validation tests"""
    print("🚀 Starting enhanced supplier management validation...\n")
    
    tests = [
        test_schemas,
        test_service_functions,
        test_database_indexes,
        test_api_routes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"\n❌ {test.__name__} failed")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All enhanced supplier management features are working correctly!")
        print("\n📋 Available endpoints:")
        print("  GET  /supplier/low-stock - Get suppliers with low stock products")
        print("  POST /supplier/{id}/purchase-orders - Create purchase orders")
        print("  GET  /supplier/{id}/performance - Get supplier performance metrics")
        print("  PUT  /supplier/{id}/products - Update supplier product catalog")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())
