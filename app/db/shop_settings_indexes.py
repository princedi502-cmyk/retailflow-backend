from app.db.mongodb import db_manager


async def create_shop_settings_indexes():
    """Create indexes for shop_settings collection."""
    collection = db_manager.db["shop_settings"]
    
    indexes = [
        {
            "keys": [("owner_id", 1)],
            "options": {
                "unique": True,
                "name": "idx_owner_id_unique",
                "background": True
            }
        }
    ]
    
    for index in indexes:
        await collection.create_index(
            index["keys"],
            **index["options"]
        )
    
    print("Shop settings indexes created successfully")
