"""
Database indexes for supplier management system
Optimized indexes for supplier queries, purchase orders, and performance metrics
"""

from app.db.mongodb import db_manager
from typing import List, Dict, Any

async def create_supplier_indexes():
    """
    Create optimized indexes for supplier collections
    """
    
    # Supplier collection indexes
    supplier_indexes = [
        # Basic lookup indexes
        {"index": {"name": 1}, "options": {"unique": True}},
        {"index": {"email": 1}, "options": {"unique": True}},
        {"index": {"phone": 1}, "options": {"sparse": True}},
        
        # Search and filtering indexes
        {"index": {"created_at": -1}},
        {"index": {"name": "text", "address": "text"}},
        
        # Compound indexes for common queries
        {"index": {"name": 1, "created_at": -1}},
        {"index": {"email": 1, "created_at": -1}}
    ]
    
    # Purchase orders collection indexes
    purchase_order_indexes = [
        # Supplier lookup indexes
        {"index": {"supplier_id": 1, "order_date": -1}},
        {"index": {"supplier_id": 1, "status": 1}},
        {"index": {"order_number": 1}, "options": {"unique": True}},
        
        # Date-based indexes for performance metrics
        {"index": {"order_date": -1}},
        {"index": {"expected_delivery_date": 1}},
        {"index": {"delivered_date": 1}},
        
        # Status-based indexes
        {"index": {"status": 1, "order_date": -1}},
        
        # Compound indexes for performance calculations
        {"index": {"supplier_id": 1, "status": 1, "order_date": -1}},
        {"index": {"supplier_id": 1, "delivered_date": -1}}
    ]
    
    # Supplier products catalog indexes
    supplier_product_indexes = [
        # Supplier-product relationship
        {"index": {"supplier_id": 1, "product_id": 1}, "options": {"unique": True}},
        {"index": {"supplier_id": 1, "is_active": 1}},
        {"index": {"product_id": 1, "is_active": 1}},
        
        # Search and filtering
        {"index": {"supplier_id": 1, "product_name": "text"}},
        {"index": {"updated_at": -1}},
        
        # Performance-related indexes
        {"index": {"supplier_id": 1, "unit_price": 1}},
        {"index": {"supplier_id": 1, "lead_time_days": 1}}
    ]
    
    # Inventory collection indexes (for low stock detection)
    inventory_indexes = [
        # Low stock detection
        {"index": {"supplier_id": 1, "current_stock": 1, "reorder_level": 1}},
        {"index": {"current_stock": 1, "reorder_level": 1}},
        {"index": {"supplier_id": 1, "product_id": 1}},
        
        # Product tracking
        {"index": {"product_id": 1, "supplier_id": 1}},
        {"index": {"updated_at": -1}}
    ]
    
    # Create all indexes
    collections_config = [
        ("suppliers", supplier_indexes),
        ("purchase_orders", purchase_order_indexes),
        ("supplier_products", supplier_product_indexes),
        ("inventory", inventory_indexes)
    ]
    
    index_creation_results = {}
    
    for collection_name, indexes in collections_config:
        try:
            collection = db_manager.db[collection_name]
            existing_indexes = await collection.list_indexes()
            existing_index_names = {idx['name'] for idx in existing_indexes}
            
            created_indexes = []
            for index_config in indexes:
                index_key = index_config["index"]
                index_options = index_config.get("options", {})
                
                # Generate index name
                index_name = "_".join([f"{k}_{v}" for k, v in index_key.items()])
                
                if index_name not in existing_index_names:
                    await collection.create_index(index_key, **index_options)
                    created_indexes.append(index_name)
            
            index_creation_results[collection_name] = {
                "status": "success",
                "created_indexes": created_indexes,
                "total_indexes": len(indexes)
            }
            
        except Exception as e:
            index_creation_results[collection_name] = {
                "status": "error",
                "error": str(e)
            }
    
    return index_creation_results

async def analyze_supplier_query_performance():
    """
    Analyze query performance for supplier operations
    """
    
    # Sample queries to analyze
    analysis_queries = [
        {
            "collection": "suppliers",
            "query": {"name": "Test Supplier"},
            "description": "Supplier lookup by name"
        },
        {
            "collection": "purchase_orders", 
            "query": {"supplier_id": "507f1f77bcf86cd799439011", "status": "delivered"},
            "description": "Supplier delivered orders"
        },
        {
            "collection": "inventory",
            "query": {"current_stock": {"$lte": 10}},
            "description": "Low stock items"
        },
        {
            "collection": "supplier_products",
            "query": {"supplier_id": "507f1f77bcf86cd799439011", "is_active": True},
            "description": "Active supplier products"
        }
    ]
    
    analysis_results = {}
    
    for query_info in analysis_queries:
        collection_name = query_info["collection"]
        query = query_info["query"]
        description = query_info["description"]
        
        try:
            collection = db_manager.db[collection_name]
            
            # Explain query execution
            explanation = await collection.find(query).limit(1).explain()
            
            analysis_results[description] = {
                "collection": collection_name,
                "query": query,
                "index_used": explanation.get("queryPlanner", {}).get("winningPlan", {}).get("inputStage", {}).get("indexName", "COLLSCAN"),
                "documents_examined": explanation.get("executionStats", {}).get("totalDocsExamined", 0),
                "execution_time_ms": explanation.get("executionStats", {}).get("executionTimeMillis", 0)
            }
            
        except Exception as e:
            analysis_results[description] = {
                "collection": collection_name,
                "query": query,
                "error": str(e)
            }
    
    return analysis_results

async def get_supplier_index_stats():
    """
    Get statistics about supplier-related indexes
    """
    
    collections = ["suppliers", "purchase_orders", "supplier_products", "inventory"]
    index_stats = {}
    
    for collection_name in collections:
        try:
            collection = db_manager.db[collection_name]
            indexes = await collection.list_indexes()
            
            collection_stats = []
            for index in indexes:
                stats = await collection.index_stats(index["name"])
                collection_stats.append({
                    "name": index["name"],
                    "keys": index["key"],
                    "size_bytes": stats.get("size", 0),
                    "usage_count": stats.get("accesses", {}).get("ops", 0)
                })
            
            index_stats[collection_name] = collection_stats
            
        except Exception as e:
            index_stats[collection_name] = {"error": str(e)}
    
    return index_stats
