import re
from typing import List
from app.core.security_middleware import injection_protection
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request
from bson import ObjectId
from pydantic import Field, validator
from app.api.router.dependency import get_current_user, require_owner, require_employee
from app.db.mongodb import db_manager
from app.schemas.product_schema import ProductCreate, ProductResponse,LowStockProductResponse
from app.core.rate_limit import limiter
from app.core.cache import cache_manager, product_cache_key, CacheTTL

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/", response_model=ProductResponse)
@limiter.limit("30/minute")
async def create_product(
    request: Request,
    product: ProductCreate,
    user=Depends(require_owner)
):
    # Validate product data
    if not product.name or not product.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Product name is required"
        )
    
    if len(product.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Product name must be at least 2 characters long"
        )
    
    if product.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Price must be greater than 0"
        )
    
    if product.stock < 0:
        raise HTTPException(
            status_code=400,
            detail="Stock cannot be negative"
        )
    
    if product.low_stock_threshold is not None and product.low_stock_threshold < 0:
        raise HTTPException(
            status_code=400,
            detail="Low stock threshold cannot be negative"
        )
    
    if product.barcode and not re.match(r'^[A-Za-z0-9-_]+$', product.barcode):
        raise HTTPException(
            status_code=400,
            detail="Barcode can only contain letters, numbers, hyphens, and underscores"
        )

    product_dict = product.model_dump()

    result = await db_manager.db["products"].insert_one(product_dict)

    new_product = await db_manager.db["products"].find_one({"_id": result.inserted_id})

    new_product["id"] = str(new_product["_id"])
    del new_product["_id"]

    return new_product

@router.get("/", response_model=list[ProductResponse])
async def get_products(
    page: int = Query(1, ge=1, le=1000, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user=Depends(get_current_user)
):
    cache_key = product_cache_key(page=page, limit=limit)
    
    # Try to get from cache first
    cached_products = await cache_manager.get(cache_key)
    if cached_products is not None:
        return cached_products
    
    skip_value = (page - 1) * limit 
    products = []
    async for product in db_manager.db["products"].find().skip(skip_value).limit(limit):
        product["id"] = str(product["_id"])
        del product["_id"]
        products.append(product)

    # Cache the result
    await cache_manager.set(cache_key, products, CacheTTL.MEDIUM)
    
    return products

@router.get("/low-stock",response_model=List[LowStockProductResponse])
async def get_low_stock_products(
    page: int = Query(1, ge=1, le=1000, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user=Depends(get_current_user)
):
    cache_key = f"products:low-stock:{page}:{limit}"
    
    # Try to get from cache first
    cached_products = await cache_manager.get(cache_key)
    if cached_products is not None:
        return cached_products
    
    products = []
    
    skip_value = (page - 1) * limit
    
    cursor = db_manager.db["products"].find({
        "$expr": { "$lt": ["$stock", "$low_stock_threshold"] }
    }).skip(skip_value).limit(limit)
    
    async for product in cursor:
        product["id"] = str(product["_id"])
        del product["_id"]
        products.append(product)

    # Cache the result with shorter TTL since stock changes frequently
    await cache_manager.set(cache_key, products, CacheTTL.SHORT)
    
    return products

@router.get("/search",response_model=List[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    page: int = Query(1, ge=1, le=1000, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user=Depends(get_current_user)
):
    # Validate search query
    if len(q.strip()) < 1:
        raise HTTPException(
            status_code=400,
            detail="Search query must be at least 1 character long"
        )
    
    if not q:
        return []

    # Sanitize and validate search query
    sanitized_q = injection_protection.sanitize_input(q)
    if not sanitized_q:
        return []
    
    cache_key = product_cache_key(page=page, limit=limit, search=sanitized_q)
    
    # Try to get from cache first
    cached_products = await cache_manager.get(cache_key)
    if cached_products is not None:
        return cached_products

    # Use sanitized regex pattern
    regex_pattern = injection_protection.sanitize_regex_pattern(sanitized_q)
    
    skip_value = (page - 1) * limit

    cursor = db_manager.db["products"].find({"name":{"$regex":regex_pattern, "$options":"i"}}).skip(skip_value).limit(limit)

    products = []

    async for product in cursor:
        product["id"] = str(product["_id"])
        del product["_id"]
        products.append(product)
    
    products.sort(key=lambda x: not x["name"].lower().startswith(q.lower()))

    # Cache search results with medium TTL
    await cache_manager.set(cache_key, products, CacheTTL.MEDIUM)
    
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str = Path(..., min_length=24, max_length=24, description="Product ID"),
    user=Depends(get_current_user)
):
    # Validate ObjectId format and prevent injection
    if not injection_protection.validate_object_id(product_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID format"
        )

    cache_key = product_cache_key(product_id=product_id)
    
    # Try to get from cache first
    cached_product = await cache_manager.get(cache_key)
    if cached_product is not None:
        return cached_product

    try:
        product = await db_manager.db["products"].find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID"
        )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product["id"] = str(product["_id"])
    del product["_id"]

    # Cache individual product with longer TTL
    await cache_manager.set(cache_key, product, CacheTTL.LONG)
    
    return product

@router.put("/{product_id}", response_model=ProductResponse)
@limiter.limit("50/minute")
async def update_product(
    request: Request,
    product: ProductCreate,
    product_id: str = Path(..., min_length=24, max_length=24, description="Product ID"),
    user=Depends(require_owner)
):
    
    # Validate ObjectId format
    if not re.match(r'^[0-9a-fA-F]{24}$', product_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID format"
        )
    
    # Validate product data
    if not product.name or not product.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Product name is required"
        )
    
    if len(product.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Product name must be at least 2 characters long"
        )
    
    if product.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Price must be greater than 0"
        )
    
    if product.stock < 0:
        raise HTTPException(
            status_code=400,
            detail="Stock cannot be negative"
        )
    
    if product.low_stock_threshold is not None and product.low_stock_threshold < 0:
        raise HTTPException(
            status_code=400,
            detail="Low stock threshold cannot be negative"
        )

    try:
        updated = await db_manager.db["products"].find_one_and_update(
            {"_id": ObjectId(product_id)},
            {"$set": product.model_dump()},
            return_document=True
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID"
        )

    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")

    updated["id"] = str(updated["_id"])
    del updated["_id"]

    # Invalidate all product-related caches
    await cache_manager.delete(product_cache_key(product_id=product_id))
    await cache_manager.delete_pattern("products:list:*")
    await cache_manager.delete_pattern("products:search:*")
    await cache_manager.delete_pattern("products:low-stock:*")

    return updated
@router.delete("/{product_id}")
@limiter.limit("20/minute")
async def delete_product(
    request: Request,
    product_id: str,
    user=Depends(require_employee)
):
    
    # Validate ObjectId format and prevent injection
    if not injection_protection.validate_object_id(product_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID format"
        )

    product_collection = db_manager.db["products"]

    try:
        result = await product_collection.delete_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID"
        )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    # Invalidate all product-related caches
    await cache_manager.delete(product_cache_key(product_id=product_id))
    await cache_manager.delete_pattern("products:list:*")
    await cache_manager.delete_pattern("products:search:*")
    await cache_manager.delete_pattern("products:low-stock:*")

    return {"message": "Product deleted"}

@router.get("/barcode/{barcode}",response_model=ProductResponse)
async def get_product_by_barcode(
    barcode: str = Path(..., min_length=1, max_length=50, description="Product barcode"),
    user=Depends(get_current_user)
):
    
    # Validate barcode format
    if not re.match(r'^[A-Za-z0-9-_]+$', barcode):
        raise HTTPException(
            status_code=400,
            detail="Invalid barcode format"
        )
    
    product = await db_manager.db["products"].find_one({"barcode": str(barcode)})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product["id"] = str(product["_id"])
    del product["_id"]
    
    return product




