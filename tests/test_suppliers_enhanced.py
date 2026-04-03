"""
Comprehensive tests for enhanced supplier management endpoints
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi.testclient import TestClient
from app.main import app
from app.db.mongodb import db_manager
from app.schemas.supplier_schema import (
    CreateSupplier, SupplierProductCatalog, CreatePurchaseOrder, PurchaseOrderItem
)

client = TestClient(app)

class TestSupplierLowStock:
    """Test GET /suppliers/low-stock endpoint"""
    
    @pytest.fixture
    async def setup_test_data(self):
        """Setup test data for low stock tests"""
        # Create test supplier
        supplier_data = {
            "name": "Test Supplier",
            "email": "test@supplier.com",
            "phone": "+1234567890",
            "address": "Test Address"
        }
        supplier_result = await db_manager.db["suppliers"].insert_one({
            **supplier_data,
            "created_at": datetime.now(timezone.utc)
        })
        supplier_id = supplier_result.inserted_id
        
        # Create test products
        product1_id = ObjectId()
        product2_id = ObjectId()
        
        await db_manager.db["products"].insert_many([
            {
                "_id": product1_id,
                "name": "Product 1",
                "description": "Test Product 1",
                "price": 10.99,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "_id": product2_id,
                "name": "Product 2", 
                "description": "Test Product 2",
                "price": 15.99,
                "created_at": datetime.now(timezone.utc)
            }
        ])
        
        # Create inventory with low stock
        await db_manager.db["inventory"].insert_many([
            {
                "supplier_id": supplier_id,
                "product_id": product1_id,
                "current_stock": 5,
                "reorder_level": 10,
                "unit_price": 10.99
            },
            {
                "supplier_id": supplier_id,
                "product_id": product2_id,
                "current_stock": 15,
                "reorder_level": 20,
                "unit_price": 15.99
            }
        ])
        
        yield supplier_id
        
        # Cleanup
        await db_manager.db["suppliers"].delete_one({"_id": supplier_id})
        await db_manager.db["products"].delete_many({"_id": {"$in": [product1_id, product2_id]}})
        await db_manager.db["inventory"].delete_many({"supplier_id": supplier_id})
    
    def test_get_low_stock_suppliers_success(self, setup_test_data):
        """Test successful retrieval of low stock suppliers"""
        response = client.get("/supplier/low-stock")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # If there are low stock suppliers
            supplier = data[0]
            assert "id" in supplier
            assert "name" in supplier
            assert "email" in supplier
            assert "low_stock_products" in supplier
            assert isinstance(supplier["low_stock_products"], list)
            
            if supplier["low_stock_products"]:
                product = supplier["low_stock_products"][0]
                assert "product_id" in product
                assert "product_name" in product
                assert "current_stock" in product
                assert "reorder_level" in product
                assert "unit_price" in product

class TestSupplierPurchaseOrders:
    """Test POST /suppliers/{id}/purchase-orders endpoint"""
    
    @pytest.fixture
    async def setup_supplier(self):
        """Setup test supplier"""
        supplier_data = {
            "name": "Test Supplier",
            "email": "test@supplier.com",
            "phone": "+1234567890",
            "address": "Test Address"
        }
        result = await db_manager.db["suppliers"].insert_one({
            **supplier_data,
            "created_at": datetime.now(timezone.utc)
        })
        supplier_id = str(result.inserted_id)
        
        yield supplier_id
        
        # Cleanup
        await db_manager.db["suppliers"].delete_one({"_id": ObjectId(supplier_id)})
        await db_manager.db["purchase_orders"].delete_many({"supplier_id": supplier_id})
    
    def test_create_purchase_order_success(self, setup_supplier):
        """Test successful purchase order creation"""
        supplier_id = setup_supplier
        
        purchase_order_data = {
            "items": [
                {
                    "product_id": "507f1f77bcf86cd799439011",
                    "product_name": "Test Product",
                    "quantity": 10,
                    "unit_price": 25.99,
                    "total_price": 259.90
                }
            ],
            "expected_delivery_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "Test purchase order"
        }
        
        response = client.post(f"/supplier/{supplier_id}/purchase-orders", json=purchase_order_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["supplier_id"] == supplier_id
        assert "order_number" in data
        assert data["status"] == "pending"
        assert len(data["items"]) == 1
        assert data["total_amount"] == 259.90
        assert data["notes"] == "Test purchase order"
    
    def test_create_purchase_order_invalid_supplier_id(self):
        """Test purchase order creation with invalid supplier ID"""
        purchase_order_data = {
            "items": [
                {
                    "product_id": "507f1f77bcf86cd799439011",
                    "product_name": "Test Product",
                    "quantity": 10,
                    "unit_price": 25.99,
                    "total_price": 259.90
                }
            ]
        }
        
        response = client.post("/supplier/invalid_id/purchase-orders", json=purchase_order_data)
        assert response.status_code == 400
        assert "Invalid supplier ID format" in response.json()["detail"]
    
    def test_create_purchase_order_nonexistent_supplier(self):
        """Test purchase order creation with non-existent supplier"""
        fake_id = "507f1f77bcf86cd799439011"
        purchase_order_data = {
            "items": [
                {
                    "product_id": "507f1f77bcf86cd799439012",
                    "product_name": "Test Product",
                    "quantity": 10,
                    "unit_price": 25.99,
                    "total_price": 259.90
                }
            ]
        }
        
        response = client.post(f"/supplier/{fake_id}/purchase-orders", json=purchase_order_data)
        assert response.status_code == 404
        assert "Supplier not found" in response.json()["detail"]
    
    def test_create_purchase_order_empty_items(self, setup_supplier):
        """Test purchase order creation with empty items list"""
        supplier_id = setup_supplier
        
        purchase_order_data = {"items": []}
        
        response = client.post(f"/supplier/{supplier_id}/purchase-orders", json=purchase_order_data)
        assert response.status_code == 400
        assert "must contain at least one item" in response.json()["detail"]
    
    def test_create_purchase_order_invalid_item_prices(self, setup_supplier):
        """Test purchase order creation with mismatched total prices"""
        supplier_id = setup_supplier
        
        purchase_order_data = {
            "items": [
                {
                    "product_id": "507f1f77bcf86cd799439011",
                    "product_name": "Test Product",
                    "quantity": 10,
                    "unit_price": 25.99,
                    "total_price": 300.00  # Incorrect total
                }
            ]
        }
        
        response = client.post(f"/supplier/{supplier_id}/purchase-orders", json=purchase_order_data)
        assert response.status_code == 400
        assert "Total price mismatch" in response.json()["detail"]

class TestSupplierPerformance:
    """Test GET /suppliers/{id}/performance endpoint"""
    
    @pytest.fixture
    async def setup_supplier_with_orders(self):
        """Setup supplier with purchase orders for performance testing"""
        # Create supplier
        supplier_data = {
            "name": "Performance Test Supplier",
            "email": "perf@test.com",
            "phone": "+1234567890",
            "address": "Test Address"
        }
        supplier_result = await db_manager.db["suppliers"].insert_one({
            **supplier_data,
            "created_at": datetime.now(timezone.utc)
        })
        supplier_id = str(supplier_result.inserted_id)
        
        # Create purchase orders
        base_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        orders_data = [
            {
                "supplier_id": supplier_id,
                "order_number": "PO-001",
                "items": [{"product_id": "prod1", "product_name": "Product 1", "quantity": 5, "unit_price": 10.0, "total_price": 50.0}],
                "total_amount": 50.0,
                "status": "delivered",
                "order_date": base_date,
                "delivered_date": base_date + timedelta(days=3),
                "expected_delivery_date": base_date + timedelta(days=5)
            },
            {
                "supplier_id": supplier_id,
                "order_number": "PO-002", 
                "items": [{"product_id": "prod2", "product_name": "Product 2", "quantity": 10, "unit_price": 20.0, "total_price": 200.0}],
                "total_amount": 200.0,
                "status": "pending",
                "order_date": base_date + timedelta(days=10)
            }
        ]
        
        await db_manager.db["purchase_orders"].insert_many(orders_data)
        
        yield supplier_id
        
        # Cleanup
        await db_manager.db["suppliers"].delete_one({"_id": ObjectId(supplier_id)})
        await db_manager.db["purchase_orders"].delete_many({"supplier_id": supplier_id})
    
    def test_get_supplier_performance_success(self, setup_supplier_with_orders):
        """Test successful retrieval of supplier performance metrics"""
        supplier_id = setup_supplier_with_orders
        
        response = client.get(f"/supplier/{supplier_id}/performance")
        assert response.status_code == 200
        data = response.json()
        
        assert data["supplier_id"] == supplier_id
        assert data["supplier_name"] == "Performance Test Supplier"
        assert data["total_orders"] == 2
        assert "on_time_delivery_rate" in data
        assert "average_fulfillment_time" in data
        assert "product_quality_score" in data
        assert "total_purchase_value" in data
        assert data["total_purchase_value"] == 250.0
        assert "performance_trend" in data
        assert data["performance_trend"] in ["improving", "declining", "stable"]
    
    def test_get_supplier_performance_no_orders(self, setup_supplier):
        """Test performance metrics for supplier with no orders"""
        supplier_id = setup_supplier
        
        response = client.get(f"/supplier/{supplier_id}/performance")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_orders"] == 0
        assert data["on_time_delivery_rate"] == 0.0
        assert data["average_fulfillment_time"] == 0.0
        assert data["total_purchase_value"] == 0.0
        assert data["performance_trend"] == "stable"

class TestSupplierProductCatalog:
    """Test PUT /suppliers/{id}/products endpoint"""
    
    @pytest.fixture
    async def setup_supplier(self):
        """Setup test supplier"""
        supplier_data = {
            "name": "Catalog Test Supplier",
            "email": "catalog@test.com",
            "phone": "+1234567890",
            "address": "Test Address"
        }
        result = await db_manager.db["suppliers"].insert_one({
            **supplier_data,
            "created_at": datetime.now(timezone.utc)
        })
        supplier_id = str(result.inserted_id)
        
        yield supplier_id
        
        # Cleanup
        await db_manager.db["suppliers"].delete_one({"_id": ObjectId(supplier_id)})
        await db_manager.db["supplier_products"].delete_many({"supplier_id": supplier_id})
    
    def test_update_supplier_product_catalog_success(self, setup_supplier):
        """Test successful update of supplier product catalog"""
        supplier_id = setup_supplier
        
        products_data = [
            {
                "product_id": "507f1f77bcf86cd799439011",
                "product_name": "Product 1",
                "description": "Test product 1",
                "unit_price": 25.99,
                "min_order_quantity": 10,
                "lead_time_days": 5,
                "is_active": True
            },
            {
                "product_id": "507f1f77bcf86cd799439012",
                "product_name": "Product 2",
                "description": "Test product 2",
                "unit_price": 15.99,
                "min_order_quantity": 5,
                "lead_time_days": 3,
                "is_active": True
            }
        ]
        
        response = client.put(f"/supplier/{supplier_id}/products", json=products_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "products" in data
        assert len(data["products"]) == 2
        assert data["products"][0]["supplier_id"] == supplier_id
    
    def test_update_supplier_product_catalog_empty_list(self, setup_supplier):
        """Test update with empty products list"""
        supplier_id = setup_supplier
        
        response = client.put(f"/supplier/{supplier_id}/products", json=[])
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]
    
    def test_update_supplier_product_catalog_invalid_prices(self, setup_supplier):
        """Test update with invalid product prices"""
        supplier_id = setup_supplier
        
        products_data = [
            {
                "product_id": "507f1f77bcf86cd799439011",
                "product_name": "Product 1",
                "unit_price": -10.0,  # Invalid negative price
                "min_order_quantity": 10,
                "lead_time_days": 5
            }
        ]
        
        response = client.put(f"/supplier/{supplier_id}/products", json=products_data)
        assert response.status_code == 400
        assert "positive unit price" in response.json()["detail"]

class TestSupplierIndexes:
    """Test supplier database indexes"""
    
    @pytest.mark.asyncio
    async def test_create_supplier_indexes(self):
        """Test creation of supplier indexes"""
        from app.db.supplier_indexes import create_supplier_indexes
        
        results = await create_supplier_indexes()
        
        assert isinstance(results, dict)
        assert "suppliers" in results
        assert "purchase_orders" in results
        assert "supplier_products" in results
        assert "inventory" in results
        
        # Check that all indexes were created successfully
        for collection_name, result in results.items():
            assert result["status"] == "success"
            assert "created_indexes" in result
            assert "total_indexes" in result
    
    @pytest.mark.asyncio
    async def test_analyze_supplier_query_performance(self):
        """Test supplier query performance analysis"""
        from app.db.supplier_indexes import analyze_supplier_query_performance
        
        results = await analyze_supplier_query_performance()
        
        assert isinstance(results, dict)
        
        for query_desc, analysis in results.items():
            assert "collection" in analysis
            assert "query" in analysis
            if "error" not in analysis:
                assert "index_used" in analysis
                assert "documents_examined" in analysis
                assert "execution_time_ms" in analysis

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
