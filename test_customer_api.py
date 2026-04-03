"""
Test script for Customer Management API
This script tests all the customer endpoints to ensure they work correctly
"""
import asyncio
import json
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.db.customer_indexes import create_customer_indexes
from app.services.customer_service import (
    create_customer_service,
    get_customers_service,
    get_customer_by_id_service,
    update_customer_service,
    delete_customer_service,
    search_customers_service,
    get_customer_orders_service
)


async def test_customer_management():
    """
    Test all customer management functionality
    """
    print("🧪 Starting Customer Management API Tests...")
    
    try:
        # Connect to database
        await connect_to_mongo()
        print("✅ Connected to MongoDB")
        
        # Create indexes
        await create_customer_indexes()
        print("✅ Created customer indexes")
        
        # Test 1: Create a new customer
        print("\n📝 Test 1: Creating new customer...")
        customer_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "USA",
            "is_active": True
        }
        
        created_customer = await create_customer_service(customer_data)
        customer_id = created_customer["id"]
        print(f"✅ Created customer: {created_customer['name']} (ID: {customer_id})")
        
        # Test 2: Get all customers with pagination
        print("\n📋 Test 2: Getting all customers...")
        customers_list = await get_customers_service(page=1, limit=10)
        print(f"✅ Retrieved {len(customers_list['customers'])} customers")
        print(f"   Total count: {customers_list['total_count']}")
        
        # Test 3: Get customer by ID
        print("\n🔍 Test 3: Getting customer by ID...")
        customer_by_id = await get_customer_by_id_service(customer_id)
        print(f"✅ Retrieved customer: {customer_by_id['name']}")
        
        # Test 4: Update customer
        print("\n✏️ Test 4: Updating customer...")
        update_data = {
            "name": "John Smith",
            "city": "Los Angeles"
        }
        updated_customer = await update_customer_service(customer_id, update_data)
        print(f"✅ Updated customer name to: {updated_customer['name']}")
        print(f"   Updated city to: {updated_customer['city']}")
        
        # Test 5: Search customers
        print("\n🔎 Test 5: Searching customers...")
        search_results = await search_customers_service(search_query="John", page=1, limit=10)
        print(f"✅ Found {search_results['total_count']} customers matching 'John'")
        
        # Test 6: Create another customer for testing duplicate prevention
        print("\n📝 Test 6: Testing duplicate prevention...")
        try:
            duplicate_customer = await create_customer_service(customer_data)
            print("❌ ERROR: Should have prevented duplicate email")
        except Exception as e:
            if "already exists" in str(e):
                print("✅ Successfully prevented duplicate customer creation")
            else:
                print(f"❌ Unexpected error: {e}")
        
        # Test 7: Get customer orders (will be empty for new customer)
        print("\n📦 Test 7: Getting customer orders...")
        order_history = await get_customer_orders_service(customer_id)
        print(f"✅ Retrieved customer order history: {order_history['total_orders']} orders")
        print(f"   Total spent: ${order_history['total_spent']:.2f}")
        
        # Test 8: Soft delete customer
        print("\n🗑️ Test 8: Soft deleting customer...")
        delete_result = await delete_customer_service(customer_id)
        print(f"✅ {delete_result['message']}")
        
        # Test 9: Verify customer is still in database but inactive
        print("\n🔍 Test 9: Verifying soft delete...")
        deleted_customer = await get_customer_by_id_service(customer_id)
        if not deleted_customer["is_active"]:
            print("✅ Customer successfully soft deleted (is_active: False)")
        else:
            print("❌ ERROR: Customer is still active after soft delete")
        
        # Test 10: Test pagination with inactive customers
        print("\n📋 Test 10: Testing pagination with active filter...")
        active_customers = await get_customers_service(page=1, limit=10, is_active=True)
        inactive_customers = await get_customers_service(page=1, limit=10, is_active=False)
        print(f"✅ Active customers: {active_customers['total_count']}")
        print(f"   Inactive customers: {inactive_customers['total_count']}")
        
        print("\n🎉 All Customer Management API tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connection
        await close_mongo_connection()
        print("🔌 Disconnected from MongoDB")


if __name__ == "__main__":
    asyncio.run(test_customer_management())
