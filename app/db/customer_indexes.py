"""
Database indexes for customers collection to optimize query performance
"""
from app.db.mongodb import db_manager
from typing import List, Dict


async def create_customer_indexes():
    """
    Create indexes for the customers collection to optimize query performance
    """
    customer_collection = db_manager.db["customers"]
    
    # Define indexes to create
    indexes: List[Dict] = [
        # Unique index on email for fast lookups and uniqueness validation
        {
            "keys": [("email", 1)],
            "options": {
                "unique": True,
                "name": "idx_email_unique",
                "background": True
            }
        },
        
        # Unique index on phone for fast lookups and uniqueness validation
        {
            "keys": [("phone", 1)],
            "options": {
                "unique": True,
                "name": "idx_phone_unique", 
                "background": True
            }
        },
        
        # Compound index for pagination with sorting by created_at
        {
            "keys": [("created_at", -1)],
            "options": {
                "name": "idx_created_at_desc",
                "background": True
            }
        },
        
        # Index for active status filtering
        {
            "keys": [("is_active", 1)],
            "options": {
                "name": "idx_is_active",
                "background": True
            }
        },
        
        # Compound index for active customers with pagination
        {
            "keys": [("is_active", 1), ("created_at", -1)],
            "options": {
                "name": "idx_is_active_created_at",
                "background": True
            }
        },
        
        # Text index for search functionality (name, email, phone)
        {
            "keys": [
                ("name", "text"),
                ("email", "text"), 
                ("phone", "text")
            ],
            "options": {
                "name": "idx_customer_search_text",
                "background": True,
                "default_language": "none"  # Better for case-sensitive searches
            }
        },
        
        # Index for customer order history queries
        {
            "keys": [("total_orders", -1)],
            "options": {
                "name": "idx_total_orders_desc",
                "background": True
            }
        },
        
        # Index for customer spending analysis
        {
            "keys": [("total_spent", -1)],
            "options": {
                "name": "idx_total_spent_desc",
                "background": True
            }
        }
    ]
    
    created_indexes = []
    
    for index_def in indexes:
        try:
            # Create index
            index_name = index_def["options"]["name"]
            await customer_collection.create_index(
                keys=index_def["keys"],
                **index_def["options"]
            )
            created_indexes.append(index_name)
            print(f"✅ Created customer index: {index_name}")
            
        except Exception as e:
            # Check if index already exists
            if "already exists" in str(e).lower():
                print(f"⚠️  Index already exists: {index_def['options']['name']}")
            else:
                print(f"❌ Failed to create index {index_def['options']['name']}: {e}")
    
    return created_indexes


async def list_customer_indexes():
    """
    List all existing indexes on the customers collection
    """
    customer_collection = db_manager.db["customers"]
    
    try:
        indexes = await customer_collection.list_indexes()
        index_list = []
        
        async for index in indexes:
            index_list.append({
                "name": index["name"],
                "keys": index["key"],
                "unique": index.get("unique", False)
            })
        
        return index_list
        
    except Exception as e:
        print(f"❌ Failed to list customer indexes: {e}")
        return []


async def drop_customer_indexes():
    """
    Drop all custom indexes (except _id_) on the customers collection
    Use with caution - this is mainly for testing/index rebuilding
    """
    customer_collection = db_manager.db["customers"]
    
    try:
        indexes = await customer_collection.list_indexes()
        dropped_indexes = []
        
        async for index in indexes:
            index_name = index["name"]
            # Don't drop the default _id_ index
            if index_name != "_id_":
                await customer_collection.drop_index(index_name)
                dropped_indexes.append(index_name)
                print(f"🗑️  Dropped customer index: {index_name}")
        
        return dropped_indexes
        
    except Exception as e:
        print(f"❌ Failed to drop customer indexes: {e}")
        return []


async def analyze_customer_index_usage():
    """
    Analyze index usage statistics for the customers collection
    """
    try:
        # This would require MongoDB profiling or explain plans
        # For now, return basic index information
        indexes = await list_customer_indexes()
        
        analysis = {
            "total_indexes": len(indexes),
            "indexes": indexes,
            "recommendations": [
                "Monitor query performance with explain()",
                "Consider compound indexes for frequent query patterns",
                "Review text search index effectiveness"
            ]
        }
        
        return analysis
        
    except Exception as e:
        print(f"❌ Failed to analyze customer index usage: {e}")
        return None


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("🔧 Setting up customer database indexes...")
        created = await create_customer_indexes()
        print(f"✅ Created {len(created)} customer indexes")
        
        print("\n📋 Current customer indexes:")
        indexes = await list_customer_indexes()
        for idx in indexes:
            print(f"  - {idx['name']}: {idx['keys']} (unique: {idx['unique']})")
    
    asyncio.run(main())
