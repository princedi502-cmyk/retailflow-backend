from typing import List, Optional
import re
from fastapi import APIRouter,Depends, HTTPException, Path, Query, Request, Response
from app.schemas.supplier_schema import (
    CreateSupplier, SupplierResponse, LowStockSupplier, 
    CreatePurchaseOrder, PurchaseOrderResponse, SupplierPerformance,
    SupplierProductCatalog, PurchaseOrderListResponse,
    PurchaseOrderStatusUpdate, PurchaseOrderWithSupplierResponse
)
from app.api.router.dependency import get_current_user,require_employee,require_owner
from app.services.supplier_service import (
    create_supplier_service, get_supplier_service, update_supplier_service, delete_supplier_service,
    get_low_stock_suppliers_service, create_purchase_order_service, 
    get_supplier_performance_service, update_supplier_product_catalog_service,
    get_purchase_orders_service, update_purchase_order_status_service
)
from app.core.rate_limit import limiter
from app.core.cache import cache_manager, supplier_cache_key, CacheTTL


router = APIRouter(
    prefix="/supplier",
    tags=["suppliers"]
)

@router.post("/",response_model=SupplierResponse)
@limiter.limit("30/minute")
async def create_supplier(
    request: Request,
    supplier: CreateSupplier, 
    user=Depends(require_owner)
):
    # Validate supplier data
    if not supplier.name or not supplier.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Supplier name is required"
        )
    
    if len(supplier.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Supplier name must be at least 2 characters long"
        )
    
    if supplier.email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', supplier.email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    if supplier.phone and not re.match(r'^[+]?[\d\s\-\(\)]{10,}$', supplier.phone):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number format"
        )

    result = await create_supplier_service(supplier)
    
    # Invalidate supplier-related caches when new supplier is created
    await cache_manager.delete_pattern("suppliers:list:*")
    
    return result


@router.get("/",response_model=List[SupplierResponse])
async def get_suppliers(
    response: Response,
    page: int = Query(1, ge=1, le=1000, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user=Depends(get_current_user)
):
    cache_key = supplier_cache_key(page=page, limit=limit)
    
    # Try to get from cache first
    cached_suppliers = await cache_manager.get(cache_key)
    if cached_suppliers is not None:
        # Backward-compatible handling for old cache shape (list-only)
        if isinstance(cached_suppliers, list):
            response.headers["X-Total-Count"] = str(len(cached_suppliers))
            response.headers["X-Total-Pages"] = "1"
            response.headers["X-Page"] = str(page)
            response.headers["X-Limit"] = str(limit)
            return cached_suppliers

        response.headers["X-Total-Count"] = str(cached_suppliers.get("total_count", 0))
        response.headers["X-Total-Pages"] = str(cached_suppliers.get("total_pages", 1))
        response.headers["X-Page"] = str(cached_suppliers.get("page", page))
        response.headers["X-Limit"] = str(cached_suppliers.get("limit", limit))
        return cached_suppliers.get("suppliers", [])
    
    suppliers_data = await get_supplier_service(page, limit)
    
    # Cache with longer TTL as supplier data changes infrequently
    await cache_manager.set(cache_key, suppliers_data, CacheTTL.LONG)

    response.headers["X-Total-Count"] = str(suppliers_data["total_count"])
    response.headers["X-Total-Pages"] = str(suppliers_data["total_pages"])
    response.headers["X-Page"] = str(suppliers_data["page"])
    response.headers["X-Limit"] = str(suppliers_data["limit"])
    
    return suppliers_data["suppliers"]

@router.put("/{supplier_id}",response_model=SupplierResponse)
@limiter.limit("40/minute")
async def update_supplier(
    request: Request,
    supplier: CreateSupplier,
    supplier_id: str = Path(..., min_length=24, max_length=24, description="Supplier ID"),
    user=Depends(require_owner)
):
    # Validate ObjectId format
    if not re.match(r'^[0-9a-fA-F]{24}$', supplier_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid supplier ID format"
        )
    
    # Validate supplier data
    if not supplier.name or not supplier.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Supplier name is required"
        )
    
    if len(supplier.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Supplier name must be at least 2 characters long"
        )
    
    if supplier.email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', supplier.email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    if supplier.phone and not re.match(r'^[+]?[\d\s\-\(\)]{10,}$', supplier.phone):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number format"
        )
    
    result = await update_supplier_service(supplier_id, supplier)
    
    # Invalidate supplier-related caches
    await cache_manager.delete(supplier_cache_key(supplier_id=supplier_id))
    await cache_manager.delete_pattern("suppliers:list:*")
    
    return result

@router.delete("/{supplier_id}")
@limiter.limit("20/minute")
async def delete_supplier(
    request: Request,
    supplier_id: str = Path(..., min_length=24, max_length=24, description="Supplier ID"),
    user=Depends(require_owner)
):
    # Validate ObjectId format
    if not re.match(r'^[0-9a-fA-F]{24}$', supplier_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid supplier ID format"
        )
    
    result = await delete_supplier_service(supplier_id)
    
    # Invalidate supplier-related caches
    await cache_manager.delete(supplier_cache_key(supplier_id=supplier_id))
    await cache_manager.delete_pattern("suppliers:list:*")
    
    return result

@router.get("/low-stock", response_model=List[LowStockSupplier])
@limiter.limit("50/minute")
async def get_low_stock_suppliers(
    request: Request,
    user=Depends(require_employee)
):
    """
    Get suppliers with products that need restocking
    """
    cache_key = "suppliers:low_stock"
    
    # Try to get from cache first
    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    low_stock_suppliers = await get_low_stock_suppliers_service()
    
    # Cache with short TTL as inventory changes frequently
    await cache_manager.set(cache_key, low_stock_suppliers, CacheTTL.SHORT)
    
    return low_stock_suppliers

@router.post("/{supplier_id}/purchase-orders", response_model=PurchaseOrderResponse)
@limiter.limit("20/minute")
async def create_purchase_order(
    request: Request,
    supplier_id: str = Path(..., min_length=24, max_length=24, description="Supplier ID"),
    purchase_order: CreatePurchaseOrder = None,
    user=Depends(require_employee)
):
    """
    Create a purchase order for a supplier
    """
    # Validate ObjectId format
    if not re.match(r'^[0-9a-fA-F]{24}$', supplier_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid supplier ID format"
        )
    
    # Validate purchase order items
    if not purchase_order.items:
        raise HTTPException(
            status_code=400,
            detail="Purchase order must contain at least one item"
        )
    
    # Validate each item
    for item in purchase_order.items:
        if item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item.product_name} must have positive quantity"
            )
        if item.unit_price <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item.product_name} must have positive unit price"
            )
        if abs(item.total_price - (item.quantity * item.unit_price)) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Total price mismatch for item {item.product_name}"
            )
    
    result = await create_purchase_order_service(supplier_id, purchase_order)
    
    # Invalidate relevant caches
    await cache_manager.delete_pattern("suppliers:performance:*")
    await cache_manager.delete_pattern("purchase_orders:*")
    
    return result

@router.get("/purchase-orders", response_model=PurchaseOrderListResponse)
@limiter.limit("50/minute")
async def get_purchase_orders(
    request: Request,
    page: int = Query(1, ge=1, le=1000, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    status: Optional[str] = Query(None, description="Optional status filter"),
    supplier_id: Optional[str] = Query(None, description="Optional supplier id filter"),
    user=Depends(require_employee)
):
    """
    Get purchase orders with pagination and optional lifecycle filtering.
    """
    cache_key = f"purchase_orders:list:{page}:{limit}:{status or 'all'}:{supplier_id or 'all'}"

    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        return cached_data

    result = await get_purchase_orders_service(
        page=page,
        limit=limit,
        status=status,
        supplier_id=supplier_id
    )

    await cache_manager.set(cache_key, result, CacheTTL.SHORT)
    return result

@router.patch("/purchase-orders/{purchase_order_id}/status", response_model=PurchaseOrderWithSupplierResponse)
@limiter.limit("30/minute")
async def update_purchase_order_status(
    request: Request,
    purchase_order_id: str = Path(..., min_length=24, max_length=24, description="Purchase order ID"),
    status_update: PurchaseOrderStatusUpdate = None,
    user=Depends(require_employee)
):
    """
    Update purchase-order lifecycle status.
    """
    if not re.match(r'^[0-9a-fA-F]{24}$', purchase_order_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid purchase order ID format"
        )

    if not status_update or not status_update.status:
        raise HTTPException(
            status_code=400,
            detail="Status is required"
        )

    result = await update_purchase_order_status_service(purchase_order_id, status_update.status)

    await cache_manager.delete_pattern("purchase_orders:*")
    await cache_manager.delete_pattern("suppliers:performance:*")

    return result

@router.get("/{supplier_id}/performance", response_model=SupplierPerformance)
@limiter.limit("50/minute")
async def get_supplier_performance(
    request: Request,
    supplier_id: str = Path(..., min_length=24, max_length=24, description="Supplier ID"),
    user=Depends(require_employee)
):
    """
    Get supplier performance metrics
    """
    # Validate ObjectId format
    if not re.match(r'^[0-9a-fA-F]{24}$', supplier_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid supplier ID format"
        )
    
    cache_key = f"suppliers:performance:{supplier_id}"
    
    # Try to get from cache first
    cached_performance = await cache_manager.get(cache_key)
    if cached_performance is not None:
        return cached_performance
    
    performance = await get_supplier_performance_service(supplier_id)
    
    # Cache with medium TTL as performance changes moderately
    await cache_manager.set(cache_key, performance, CacheTTL.MEDIUM)
    
    return performance

@router.put("/{supplier_id}/products")
@limiter.limit("30/minute")
async def update_supplier_product_catalog(
    request: Request,
    supplier_id: str = Path(..., min_length=24, max_length=24, description="Supplier ID"),
    products: List[SupplierProductCatalog] = None,
    user=Depends(require_owner)
):
    """
    Update supplier product catalog
    """
    # Validate ObjectId format
    if not re.match(r'^[0-9a-fA-F]{24}$', supplier_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid supplier ID format"
        )
    
    # Validate products list
    if not products:
        raise HTTPException(
            status_code=400,
            detail="Products list cannot be empty"
        )
    
    # Validate each product
    for product in products:
        if not product.product_id or not product.product_name:
            raise HTTPException(
                status_code=400,
                detail="Product ID and name are required"
            )
        if product.unit_price <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Product {product.product_name} must have positive unit price"
            )
        if product.min_order_quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Product {product.product_name} must have positive minimum order quantity"
            )
        if product.lead_time_days < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Product {product.product_name} cannot have negative lead time"
            )
    
    result = await update_supplier_product_catalog_service(supplier_id, products)
    
    # Invalidate relevant caches
    await cache_manager.delete_pattern(f"suppliers:products:{supplier_id}*")
    await cache_manager.delete_pattern("suppliers:low_stock")
    
    return result
