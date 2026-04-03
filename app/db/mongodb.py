from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client : AsyncIOMotorClient = None
    db = None

db_manager = Database()

async def connect_to_mongo():
    global db_manager
    import os
    
    # Check if we're in production environment
    is_production = os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("ENVIRONMENT") == "production" or os.getenv("RENDER") == "true"
    
    # For both development and production, try Atlas first
    try:
        mongo_url = settings.MONGO_URL
        print(f"Attempting Atlas connection: {mongo_url[:50]}...")
        
        # Atlas connection with proper SSL settings for production compatibility
        db_manager.client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=30000,
            socketTimeoutMS=30000,
            connectTimeoutMS=30000,
            retryWrites=True,
            retryReads=True,
            w=1,
            maxPoolSize=50,
            minPoolSize=5,
            # Use MongoDB Atlas's recommended SSL settings
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False
        )
        
        # Test connection
        db_manager.client.admin.command('ping')
        db_manager.db = db_manager.client[settings.DATABASE_NAME]
        print(f"✅ Connected to Mongo Atlas: {settings.DATABASE_NAME}")
        
        # Test actual database operation to verify write access
        test_doc = {"connection_test": True, "timestamp": "2026-03-18", "env": "production" if is_production else "development"}
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
            # In production, try alternative Atlas connection before failing
            print("🔄 Trying alternative Atlas connection...")
            try:
                # Try with different SSL settings for problematic environments
                mongo_url = settings.MONGO_URL
                db_manager.client = AsyncIOMotorClient(
                    mongo_url,
                    serverSelectionTimeoutMS=30000,
                    socketTimeoutMS=30000,
                    connectTimeoutMS=30000,
                    retryWrites=True,
                    retryReads=True,
                    w=1,
                    # Alternative SSL settings for restrictive environments
                    tls=True,
                    tlsAllowInvalidCertificates=True,  # Allow self-signed certs
                    tlsAllowInvalidHostnames=True   # Allow hostname mismatches
                )
                
                # Test connection
                db_manager.client.admin.command('ping')
                db_manager.db = db_manager.client[settings.DATABASE_NAME]
                print(f"✅ Connected to Mongo Atlas (relaxed SSL): {settings.DATABASE_NAME}")
                return
                
            except Exception as alt_error:
                print(f"❌ Alternative Atlas connection failed: {alt_error}")
                raise Exception(f"❌ Production Atlas connection failed. Primary: {e}, Alternative: {alt_error}")

async def close_mongo_connection():
    if db_manager.client:
        db_manager.client.close()
        print("MongoDB connection closed")

async def connect():
    """Main connect method that tries both Atlas and local"""
    await connect_to_mongo()
