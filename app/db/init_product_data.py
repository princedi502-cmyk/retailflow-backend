import asyncio
from app.db.mongodb import db_manager
from app.schemas.product_schema import ProductCreate

async def initialize_sample_products():
    """Initialize sample products for testing"""
    try:
        # Check if products already exist
        existing_count = await db_manager.db["products"].count_documents({})
        if existing_count > 0:
            print(f"Products already exist: {existing_count} found")
            return
        
        # Sample products
        sample_products = [
            ProductCreate(
                name="Laptop Pro 15",
                price=1299.99,
                stock=25,
                barcode="LP001",
                category="Electronics",
                low_stock_threshold=10
            ),
            ProductCreate(
                name="Wireless Mouse",
                price=29.99,
                stock=150,
                barcode="WM002",
                category="Electronics",
                low_stock_threshold=20
            ),
            ProductCreate(
                name="Office Chair",
                price=199.99,
                stock=8,
                barcode="OC003",
                category="Furniture",
                low_stock_threshold=15
            ),
            ProductCreate(
                name="Desk Lamp LED",
                price=45.99,
                stock=75,
                barcode="DL004",
                category="Lighting",
                low_stock_threshold=25
            ),
            ProductCreate(
                name="USB-C Hub",
                price=59.99,
                stock=3,
                barcode="UH005",
                category="Electronics",
                low_stock_threshold=10
            ),
            ProductCreate(
                name="Notebook Set",
                price=12.99,
                stock=200,
                barcode="NS006",
                category="Stationery",
                low_stock_threshold=50
            ),
            ProductCreate(
                name="Coffee Maker",
                price=89.99,
                stock=15,
                barcode="CM007",
                category="Appliances",
                low_stock_threshold=8
            ),
            ProductCreate(
                name="Monitor Stand",
                price=34.99,
                stock=45,
                barcode="MS008",
                category="Furniture",
                low_stock_threshold=20
            )
        ]
        
        # Insert products
        product_dicts = [product.model_dump() for product in sample_products]
        result = await db_manager.db["products"].insert_many(product_dicts)
        
        print(f"Successfully created {len(result.inserted_ids)} sample products")
        
        # Display created products
        for i, product_id in enumerate(result.inserted_ids):
            print(f"  {i+1}. {sample_products[i].name} (ID: {product_id})")
            
    except Exception as e:
        print(f"Error initializing products: {e}")

if __name__ == "__main__":
    asyncio.run(initialize_sample_products())
