"""
Initialize customer management system
This module sets up the necessary database indexes and initial data for the customer management system
"""
import asyncio
import logging
from app.db.mongodb import db_manager
from app.db.customer_indexes import create_customer_indexes

logger = logging.getLogger(__name__)


async def initialize_customer_system():
    """
    Initialize the customer management system by creating necessary indexes
    This should be called during application startup
    """
    try:
        logger.info("Initializing customer management system...")
        
        # Create customer indexes
        created_indexes = await create_customer_indexes()
        logger.info(f"Created {len(created_indexes)} customer indexes")
        
        # Verify customer collection exists and is accessible
        customer_collection = db_manager.db["customers"]
        
        # Test collection access
        count = await customer_collection.count_documents({})
        logger.info(f"Customer collection accessible. Current customer count: {count}")
        
        logger.info("✅ Customer management system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize customer management system: {e}")
        return False


async def get_customer_stats():
    """
    Get basic statistics about the customer collection
    """
    try:
        customer_collection = db_manager.db["customers"]
        
        # Get total customers
        total_customers = await customer_collection.count_documents({})
        
        # Get active customers
        active_customers = await customer_collection.count_documents({"is_active": True})
        
        # Get inactive customers
        inactive_customers = await customer_collection.count_documents({"is_active": False})
        
        # Get customers created in last 30 days
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_customers = await customer_collection.count_documents({
            "created_at": {"$gte": thirty_days_ago}
        })
        
        stats = {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "inactive_customers": inactive_customers,
            "recent_customers": recent_customers,
            "collection_name": "customers"
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get customer stats: {e}")
        return None


# Standalone execution for testing/initialization
if __name__ == "__main__":
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def main():
        from app.db.mongodb import connect_to_mongo, close_mongo_connection
        
        try:
            # Connect to database
            await connect_to_mongo()
            
            # Initialize customer system
            success = await initialize_customer_system()
            
            if success:
                # Get stats
                stats = await get_customer_stats()
                if stats:
                    print("\n📊 Customer Statistics:")
                    print(f"   Total customers: {stats['total_customers']}")
                    print(f"   Active customers: {stats['active_customers']}")
                    print(f"   Inactive customers: {stats['inactive_customers']}")
                    print(f"   Recent customers (30 days): {stats['recent_customers']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            # Close connection
            await close_mongo_connection()
    
    asyncio.run(main())
