"""
Centralized validation utilities for the RetailFlow API
"""
import re
from fastapi import HTTPException
from typing import Any, Optional


def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not email.strip():
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    return True


def validate_password_strength(password: str) -> bool:
    """Validate password strength requirements"""
    if not password or not password.strip():
        raise HTTPException(
            status_code=400,
            detail="Password is required"
        )
    
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )
    
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter"
        )
    
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter"
        )
    
    if not re.search(r'\d', password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one digit"
        )
    
    return True


def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username or not username.strip():
        raise HTTPException(
            status_code=400,
            detail="Username is required"
        )
    
    if len(username.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters long"
        )
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise HTTPException(
            status_code=400,
            detail="Username can only contain letters, numbers, and underscores"
        )
    
    return True


def validate_object_id(object_id: str, field_name: str = "ID") -> bool:
    """Validate MongoDB ObjectId format"""
    if not object_id or not object_id.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is required"
        )
    
    if not re.match(r'^[0-9a-fA-F]{24}$', object_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name.lower()} format"
        )
    
    return True


def validate_name(name: str, field_name: str = "Name", min_length: int = 2) -> bool:
    """Validate name field"""
    if not name or not name.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is required"
        )
    
    if len(name.strip()) < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be at least {min_length} characters long"
        )
    
    return True


def validate_positive_number(value: float, field_name: str) -> bool:
    """Validate that a number is positive"""
    if value <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be greater than 0"
        )
    
    return True


def validate_non_negative_number(value: float, field_name: str) -> bool:
    """Validate that a number is non-negative"""
    if value < 0:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} cannot be negative"
        )
    
    return True


def validate_phone_number(phone: Optional[str]) -> bool:
    """Validate phone number format"""
    if phone and not re.match(r'^[+]?[\d\s\-\(\)]{10,}$', phone):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number format"
        )
    
    return True


def validate_barcode(barcode: Optional[str]) -> bool:
    """Validate barcode format"""
    if barcode and not re.match(r'^[A-Za-z0-9-_]+$', barcode):
        raise HTTPException(
            status_code=400,
            detail="Barcode can only contain letters, numbers, hyphens, and underscores"
        )
    
    return True


def validate_search_query(query: str) -> bool:
    """Validate search query to prevent injection"""
    if not query or not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query is required"
        )
    
    if len(query.strip()) < 1:
        raise HTTPException(
            status_code=400,
            detail="Search query must be at least 1 character long"
        )
    
    # Prevent regex injection
    if any(char in query for char in ['.*', '^', '$', '+', '?', '|', '(', ')', '[', ']', '{', '}']):
        raise HTTPException(
            status_code=400,
            detail="Search query contains invalid characters"
        )
    
    return True


def validate_pagination_params(page: int, limit: int) -> bool:
    """Validate pagination parameters"""
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page number must be greater than 0"
        )
    
    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="Limit must be greater than 0"
        )
    
    return True


def validate_year(year: int) -> bool:
    """Validate year parameter"""
    if not re.match(r'^\d{4}$', str(year)):
        raise HTTPException(
            status_code=400,
            detail="Invalid year format"
        )
    
    return True
