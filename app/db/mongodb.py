from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client : AsyncIOMotorClient = None
    db = None

db_manager = Database()

async def connect_to_mongo():
    global db_manager
    try:
        # Try with minimal TLS configuration for Railway
        db_manager.client = AsyncIOMotorClient(
            settings.MONGO_URL,
            serverSelectionTimeoutMS=30000,
            socketTimeoutMS=30000,
            connectTimeoutMS=30000,
            retryWrites=True,
            w="majority"
        )
        # Test connection
        db_manager.client.admin.command('ping')
        db_manager.db = db_manager.client[settings.DATABASE_NAME]
        print(f"connected to Mongo:{settings.DATABASE_NAME}")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        # Fallback without TLS
        try:
            db_manager.client = AsyncIOMotorClient(
                settings.MONGO_URL.replace("mongodb+srv://", "mongodb://"),
                serverSelectionTimeoutMS=30000,
                socketTimeoutMS=30000,
                connectTimeoutMS=30000
            )
            db_manager.db = db_manager.client[settings.DATABASE_NAME]
            print(f"connected to Mongo (fallback):{settings.DATABASE_NAME}")
        except Exception as fallback_error:
            print(f"MongoDB fallback connection failed: {fallback_error}")
            raise

async def close_mongo_connection():
    if db_manager.client:
        db_manager.client.close()
        print("MongoDB connection closed")
