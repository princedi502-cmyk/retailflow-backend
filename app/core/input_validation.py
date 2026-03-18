"""
Additional input validation utilities
"""
import re
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel, validator


class BaseValidationMixin:
    """Base validation mixin for Pydantic models"""
    
    @validator('*', pre=True)
    def sanitize_fields(cls, v):
        """Sanitize all fields before validation"""
        if isinstance(v, str):
            # Remove dangerous characters
            dangerous_chars = ['<', '>', '"', "'", '&', ';', '--', '/*', '*/']
            for char in dangerous_chars:
                v = v.replace(char, '')
            
            # Limit length
            if len(v) > 1000:
                raise ValueError("Input too long")
            
            return v.strip()
        return v


class ProductCreateValidation(BaseModel, BaseValidationMixin):
    """Validated product creation model"""
    name: str
    barcode: str
    price: float
    stock: int
    low_stock_threshold: int
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError("Product name is required")
        if len(v) > 100:
            raise ValueError("Product name too long")
        return v.strip()
    
    @validator('barcode')
    def validate_barcode(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError("Barcode is required")
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Barcode can only contain letters, numbers, hyphens, and underscores")
        return v.strip()
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        if v > 99999.99:
            raise ValueError("Price too high")
        return round(v, 2)
    
    @validator('stock')
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError("Stock cannot be negative")
        if v > 999999:
            raise ValueError("Stock value too high")
        return v
    
    @validator('low_stock_threshold')
    def validate_threshold(cls, v):
        if v < 0:
            raise ValueError("Threshold cannot be negative")
        if v > 999999:
            raise ValueError("Threshold value too high")
        return v


class UserCreateValidation(BaseModel, BaseValidationMixin):
    """Validated user creation model"""
    username: str
    email: str
    password: str
    role: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Username too long")
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v.strip()
    
    @validator('email')
    def validate_email(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.strip().lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['admin', 'owner', 'employee']:
            raise ValueError("Invalid role")
        return v


class SupplierCreateValidation(BaseModel, BaseValidationMixin):
    """Validated supplier creation model"""
    name: str
    email: str
    phone: str
    address: str
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError("Supplier name is required")
        if len(v) > 100:
            raise ValueError("Supplier name too long")
        return v.strip()
    
    @validator('email')
    def validate_email(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.strip().lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        if not re.match(r'^[\d\s\-\+\(\)]+$', v):
            raise ValueError("Invalid phone number format")
        return v.strip()
    
    @validator('address')
    def validate_address(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Address must be at least 10 characters long")
        if len(v) > 500:
            raise ValueError("Address too long")
        return v.strip()


def validate_pagination_params(page: int = 1, limit: int = 50) -> tuple[int, int]:
    """Validate pagination parameters"""
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page must be at least 1"
        )
    
    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="Limit must be at least 1"
        )
    
    if limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit cannot exceed 100"
        )
    
    return page, limit


def validate_search_query(query: str) -> str:
    """Validate search query"""
    if not query or len(query.strip()) < 1:
        raise HTTPException(
            status_code=400,
            detail="Search query is required"
        )
    
    if len(query) > 100:
        raise HTTPException(
            status_code=400,
            detail="Search query too long"
        )
    
    # Remove dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '--', '/*', '*/']
    for char in dangerous_chars:
        query = query.replace(char, '')
    
    return query.strip()


def validate_date_range(start_date: str = None, end_date: str = None) -> tuple[Optional[str], Optional[str]]:
    """Validate date range parameters"""
    if start_date:
        try:
            # Basic date format validation
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', start_date):
                raise ValueError("Invalid date format, use YYYY-MM-DD")
        except:
            raise HTTPException(
                status_code=400,
                detail="Invalid start date format"
            )
    
    if end_date:
        try:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', end_date):
                raise ValueError("Invalid date format, use YYYY-MM-DD")
        except:
            raise HTTPException(
                status_code=400,
                detail="Invalid end date format"
            )
    
    return start_date, end_date
