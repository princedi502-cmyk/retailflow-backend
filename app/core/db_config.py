"""
Database configuration module for connection pooling settings
"""

import os
from typing import Dict, Any
from pymongo.pool import PoolOptions

class DatabaseConfig:
    """Database configuration class for connection pooling"""
    
    @staticmethod
    def get_pool_options() -> PoolOptions:
        """Get optimized pool options based on environment"""
        env = os.getenv("ENVIRONMENT", "development")
        
        if env == "production":
            return PoolOptions(
                max_pool_size=100,         # Higher pool for production
                min_pool_size=10,          # Maintain more connections
                max_idle_time_seconds=60,   # 1 minute idle time (in seconds)
                wait_queue_timeout=10,      # 10 second wait timeout (in seconds)
                connect_timeout=15.0,       # 15 second connection timeout (in seconds)
                socket_timeout=30.0,        # 30 second socket timeout (in seconds)
            )
        else:
            # Development/staging settings
            return PoolOptions(
                max_pool_size=50,          # Moderate pool for development
                min_pool_size=5,           # Fewer maintained connections
                max_idle_time_seconds=30,  # 30 second idle time (in seconds)
                wait_queue_timeout=5,      # 5 second wait timeout (in seconds)
                connect_timeout=10.0,      # 10 second connection timeout (in seconds)
                socket_timeout=20.0,       # 20 second socket timeout (in seconds)
            )
    
    @staticmethod
    def get_client_kwargs() -> dict:
        """Get additional MongoClient constructor arguments"""
        env = os.getenv("ENVIRONMENT", "development")
        
        if env == "production":
            return {
                "retrywrites": True,
                "retryreads": True,
                "w": "majority",
                "readPreference": "secondaryPreferred",
                "tls": True,
                "tlsAllowInvalidCertificates": False,
                "ssl": True,
                "ssl_cert_reqs": "CERT_REQUIRED"
            }
        else:
            return {
                "retrywrites": True,
                "retryreads": True,
                "w": "majority",
                "readPreference": "primary",
                "tls": True,
                "tlsAllowInvalidCertificates": False,
                "ssl": True,
                "ssl_cert_reqs": "CERT_REQUIRED"
            }
    
    @staticmethod
    def get_connection_string() -> str:
        """Get MongoDB connection string with validation"""
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            raise ValueError("MONGO_URL environment variable is not set")
        return mongo_url
    
    @staticmethod
    def get_database_name() -> str:
        """Get database name"""
        return os.getenv("DATABASE_NAME", "Retail_Flow")
    
    @staticmethod
    def get_monitoring_config() -> Dict[str, Any]:
        """Get monitoring configuration for database performance"""
        return {
            "enable_stats": os.getenv("DB_ENABLE_STATS", "true").lower() == "true",
            "stats_interval": int(os.getenv("DB_STATS_INTERVAL", "60")),  # seconds
            "alert_threshold": int(os.getenv("DB_ALERT_THRESHOLD", "80")),  # percentage
            "log_slow_queries": os.getenv("DB_LOG_SLOW_QUERIES", "true").lower() == "true",
            "slow_query_threshold": int(os.getenv("DB_SLOW_QUERY_THRESHOLD", "1000")),  # ms
            "safe_mode": os.getenv("DB_MONITORING_SAFE_MODE", "true").lower() == "true",
            "read_only": os.getenv("DB_MONITORING_READ_ONLY", "true").lower() == "true",
            "no_schema_changes": os.getenv("DB_MONITORING_NO_SCHEMA_CHANGES", "true").lower() == "true"
        }
