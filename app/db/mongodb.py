from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client : AsyncIOMotorClient = None
    db = None

db_manager = Database()

async def connect_to_mongo():
    global db_manager
    # MongoDB Atlas requires TLS configuration
    db_manager.client = AsyncIOMotorClient(
        settings.MONGO_URL,
        tls=True,
        tlsAllowInvalidCertificates=False,
        serverSelectionTimeoutMS=30000,
        socketTimeoutMS=30000,
        connectTimeoutMS=30000
    )
    db_manager.db = db_manager.client[settings.DATABASE_NAME]
    print(f"connected to Mongo:{settings.DATABASE_NAME}")

async def close_mongo_connection():
    if db_manager.client:
        db_manager.client.close()
        print("MongoDB connection closed")
