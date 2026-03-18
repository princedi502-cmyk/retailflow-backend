from typing import List
import re
from fastapi import APIRouter,Depends, HTTPException, Path, Query, Request
from app.schemas.supplier_schema import CreateSupplier,SupplierResponse
from app.api.router.dependency import get_current_user,require_employee,require_owner
from app.services.supplier_service import create_supplier_service, get_supplier_service,update_supplier_service,delete_supplier_service
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
    page: int = Query(1, ge=1, le=1000, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user=Depends(get_current_user)
):
    cache_key = supplier_cache_key(page=page, limit=limit)
    
    # Try to get from cache first
    cached_suppliers = await cache_manager.get(cache_key)
    if cached_suppliers is not None:
        return cached_suppliers
    
    suppliers = await get_supplier_service(page, limit)
    
    # Cache with longer TTL as supplier data changes infrequently
    await cache_manager.set(cache_key, suppliers, CacheTTL.LONG)
    
    return suppliers

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