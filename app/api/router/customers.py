from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    CustomerSearchResponse,
    CustomerOrderHistoryResponse
)
from app.services.customer_service import (
    create_customer_service,
    get_customers_service,
    get_customer_by_id_service,
    update_customer_service,
    delete_customer_service,
    search_customers_service,
    get_customer_orders_service
)
from app.api.router.dependency import get_current_user

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=CustomerResponse, status_code=201)
async def create_customer(
    customer: CustomerCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new customer
    
    - **name**: Customer full name
    - **email**: Valid email address (must be unique)
    - **phone**: Phone number with country code (must be unique)
    - **address**: Street address (optional)
    - **city**: City name (optional)
    - **state**: State or province (optional)
    - **postal_code**: Postal or ZIP code (optional)
    - **country**: Country name (optional)
    - **is_active**: Whether the customer account is active (default: True)
    """
    try:
        customer_data = customer.dict()
        result = await create_customer_service(customer_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/", response_model=CustomerListResponse)
async def get_customers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all customers with pagination
    
    - **page**: Page number (default: 1)
    - **limit**: Number of items per page (default: 10, max: 100)
    - **is_active**: Filter by active status (optional)
    """
    try:
        result = await get_customers_service(page=page, limit=limit, is_active=is_active)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/search", response_model=CustomerSearchResponse)
async def search_customers(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search customers by name, email, or phone
    
    - **q**: Search query (searches in name, email, and phone fields)
    - **page**: Page number (default: 1)
    - **limit**: Number of items per page (default: 10, max: 100)
    - Search is case-insensitive and uses regex matching
    """
    try:
        result = await search_customers_service(search_query=q, page=page, limit=limit)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get customer details by ID
    
    - **customer_id**: MongoDB ObjectId of the customer
    """
    try:
        result = await get_customer_by_id_service(customer_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_update: CustomerUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update customer information
    
    - **customer_id**: MongoDB ObjectId of the customer
    - All fields are optional - only provided fields will be updated
    - Email and phone must remain unique across all customers
    """
    try:
        update_data = customer_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )
        
        result = await update_customer_service(customer_id, update_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete customer (soft delete)
    
    - **customer_id**: MongoDB ObjectId of the customer
    - This performs a soft delete by setting is_active to False
    - Customer data is preserved for order history and analytics
    """
    try:
        result = await delete_customer_service(customer_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{customer_id}/orders", response_model=CustomerOrderHistoryResponse)
async def get_customer_orders(
    customer_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customer order history
    
    - **customer_id**: MongoDB ObjectId of the customer
    - **page**: Page number (default: 1)
    - **limit**: Number of orders per page (default: 10, max: 100)
    - Updates customer's total_orders and total_spent fields
    """
    try:
        result = await get_customer_orders_service(customer_id=customer_id, page=page, limit=limit)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
