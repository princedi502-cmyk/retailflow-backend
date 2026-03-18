"""
Simple database indexes setup for RetailFlow
Run this script once to create all necessary indexes for production
"""

from app.db.mongodb import db_manager

def create_indexes():
    """Create all necessary database indexes"""
    
    # Users collection indexes
    db.users.create_index("email", unique=True)
    db.users.create_index("username", unique=True)
    db.users.create_index("role")
    db.users.create_index([("role", 1), ("created_at", -1)])  # User analytics
    db.users.create_index("last_login")  # Activity tracking
    
    # Products collection indexes
    db.products.create_index("name", unique=True)
    db.products.create_index("barcode", unique=True, sparse=True)
    db.products.create_index("category")
    db.products.create_index("stock")
    db.products.create_index([("stock", 1), ("low_stock_threshold", 1)])
    
    # Compound indexes for product analytics
    db.products.create_index([("category", 1), ("stock", -1)])  # Category stock analysis
    db.products.create_index([("price", 1), ("category", 1)])  # Price range by category
    db.products.create_index([("name", "text"), ("category", "text")])  # Text search
    
    # Orders collection indexes - optimized for analytics aggregations
    db.orders.create_index("user_id")
    db.orders.create_index("created_at")
    db.orders.create_index([("user_id", 1), ("created_at", -1)])
    db.orders.create_index("items.name")
    db.orders.create_index("items.product_id")
    
    # Compound indexes for aggregation performance
    db.orders.create_index([("created_at", -1), ("total_price", -1)])  # Revenue analytics
    db.orders.create_index([("items.product_id", 1), ("created_at", -1)])  # Product sales trends
    db.orders.create_index([("status", 1), ("created_at", -1)])  # Status tracking
    db.orders.create_index([("items.name", 1), ("items.quantity", 1)])  # Product quantity analysis
    
    # Suppliers collection indexes
    db.suppliers.create_index("name", unique=True)
    db.suppliers.create_index("email", unique=True)
    
    # Purchase orders collection indexes
    db.purchase_orders.create_index("supplier_id")
    db.purchase_orders.create_index("status")
    db.purchase_orders.create_index("created_at")
    
    print("✅ All database indexes created successfully!")

if __name__ == "__main__":
    create_indexes()
