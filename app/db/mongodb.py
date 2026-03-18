from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client : AsyncIOMotorClient = None
    db = None

db_manager = Database()

async def connect_to_mongo():
    global db_manager
    try:
        # Convert SRV to direct connection for Railway
        mongo_url = settings.MONGO_URL.replace("mongodb+srv://", "mongodb://")
        
        # Try connection with minimal SSL settings
        db_manager.client = AsyncIOMotorClient(
            mongo_url,
            ssl=True,
            ssl_cert_reqs=None,  # Don't require SSL cert verification
            serverSelectionTimeoutMS=30000,
            socketTimeoutMS=30000,
            connectTimeoutMS=30000,
            retryWrites=False,  # Disable retry writes for better compatibility
            w=1  # Simple write concern
        )
        
        # Test connection
        db_manager.client.admin.command('ping')
        db_manager.db = db_manager.client[settings.DATABASE_NAME]
        print(f"connected to Mongo:{settings.DATABASE_NAME}")
        
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        # Last resort - try without any SSL
        try:
            mongo_url = settings.MONGO_URL.replace("mongodb+srv://", "mongodb://")
            db_manager.client = AsyncIOMotorClient(
                mongo_url,
                ssl=False,
                serverSelectionTimeoutMS=30000,
                socketTimeoutMS=30000,
                connectTimeoutMS=30000
            )
            db_manager.db = db_manager.client[settings.DATABASE_NAME]
            print(f"connected to Mongo (no SSL):{settings.DATABASE_NAME}")
        except Exception as fallback_error:
            print(f"MongoDB fallback connection failed: {fallback_error}")
            raise

async def close_mongo_connection():
    if db_manager.client:
        db_manager.client.close()
        print("MongoDB connection closed")
