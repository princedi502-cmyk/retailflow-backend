from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import ssl

class Database:
    client : AsyncIOMotorClient = None
    db = None

db_manager = Database()

async def connect_to_mongo():
    global db_manager
    import os
    
    # Check if we're in production environment
    is_production = os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("ENVIRONMENT") == "production"
    
    # For both development and production, try Atlas first
    try:
        mongo_url = settings.MONGO_URL
        print(f"Attempting Atlas connection: {mongo_url[:50]}...")
        
        # Atlas connection with minimal SSL settings
        db_manager.client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=20000,
            socketTimeoutMS=20000,
            connectTimeoutMS=20000,
            retryWrites=True,
            retryReads=True,
            w=1
        )
        
        # Test connection
        db_manager.client.admin.command('ping')
        db_manager.db = db_manager.client[settings.DATABASE_NAME]
        print(f"✅ Connected to Mongo Atlas: {settings.DATABASE_NAME}")
        
        # Test actual database operation to verify write access
        test_doc = {"connection_test": True, "timestamp": "2026-03-18", "env": "development" if not is_production else "production"}
        result = await db_manager.db["connection_test"].insert_one(test_doc)
        await db_manager.db["connection_test"].delete_one({"_id": result.inserted_id})
        print("✅ Atlas database operation test: SUCCESS")
        return
        
    except Exception as e:
        print(f"❌ Atlas connection failed: {e}")
        
        # Only fallback to local if NOT in production
        if not is_production:
            print("🔄 Falling back to local MongoDB for development...")
            try:
                local_url = "mongodb://localhost:27017"
                db_manager.client = AsyncIOMotorClient(
                    local_url,
                    serverSelectionTimeoutMS=5000,
                    socketTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                db_manager.db = db_manager.client["Retail_Flow_Dev"]
                print(f"✅ Connected to Local MongoDB (fallback): Retail_Flow_Dev")
                
                # Test local database operation
                test_doc = {"connection_test": True, "timestamp": "2026-03-18", "env": "local_fallback"}
                result = await db_manager.db["connection_test"].insert_one(test_doc)
                await db_manager.db["connection_test"].delete_one({"_id": result.inserted_id})
                print("✅ Local database operation test: SUCCESS")
                
            except Exception as local_error:
                print(f"❌ Local MongoDB fallback failed: {local_error}")
                raise Exception(f"❌ All database connection attempts failed. Atlas error: {e}, Local error: {local_error}")
        else:
            # In production, fail if Atlas doesn't work
            raise Exception(f"❌ Production Atlas connection failed: {e}")

async def close_mongo_connection():
    if db_manager.client:
        db_manager.client.close()
        print("MongoDB connection closed")
