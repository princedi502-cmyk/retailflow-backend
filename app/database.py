from pymongo import MongoClient
import os
from dotenv import load_dotenv
from app.core.db_config import DatabaseConfig

load_dotenv()

# Get database configuration
MONGO_URL = DatabaseConfig.get_connection_string()
DATABASE_NAME = DatabaseConfig.get_database_name()

# Get pool options based on environment
pool_options = DatabaseConfig.get_pool_options()
client_kwargs = DatabaseConfig.get_client_kwargs()

# Create client with connection pooling and additional options
client = MongoClient(
    MONGO_URL, 
    maxPoolSize=pool_options.max_pool_size,
    minPoolSize=pool_options.min_pool_size,
    maxIdleTimeMS=pool_options.max_idle_time_seconds * 1000,  # Convert to milliseconds
    waitQueueTimeoutMS=pool_options.wait_queue_timeout * 1000,  # Convert to milliseconds
    connectTimeoutMS=int(pool_options.connect_timeout * 1000),  # Convert to milliseconds
    socketTimeoutMS=int(pool_options.socket_timeout * 1000),  # Convert to milliseconds
    **client_kwargs
)
db = client[DATABASE_NAME]

users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]
supplier_collection = db["suppliers"]
purchase_order_collection =  db["purchase_orders"]

# Function to get database stats for monitoring
def get_db_stats():
    """Get database statistics for monitoring connection pool performance"""
    try:
        stats = db.command("dbStats")
        return {
            "collections": stats.get("collections", 0),
            "dataSize": stats.get("dataSize", 0),
            "storageSize": stats.get("storageSize", 0),
            "indexes": stats.get("indexes", 0)
        }
    except Exception as e:
        return {"error": str(e)}

# Function to test connection
def test_connection():
    """Test database connection"""
    try:
        db.command("ping")
        return True
    except Exception as e:
        return False

# Function to close all connections
def close_connections():
    """Close all database connections"""
    try:
        client.close()
        return True
    except Exception as e:
        return False