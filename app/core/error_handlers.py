"""
Standardized error handlers for consistent and secure error responses
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError as RequestValidationError
from typing import Dict, Any, Optional
import traceback
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Custom exception for security-related errors"""
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)

def create_error_response(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    error_response = {
        "error": True,
        "status_code": status_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if error_code:
        error_response["error_code"] = error_code
    
    if details and status_code < 500:  # Only include details for client errors
        error_response["details"] = details
    
    if request_id:
        error_response["request_id"] = request_id
    
    return error_response

def get_client_friendly_message(status_code: int, original_message: str) -> str:
    """Convert technical error messages to client-friendly messages"""
    # Don't expose internal error details for 5xx errors
    if status_code >= 500:
        return "An internal server error occurred. Please try again later."
    
    # Common error message mappings
    message_mappings = {
        400: "Invalid request data provided.",
        401: "Authentication required to access this resource.",
        403: "You don't have permission to access this resource.",
        404: "The requested resource was not found.",
        422: "The request data is invalid.",
        429: "Too many requests. Please try again later.",
    }
    
    return message_mappings.get(status_code, original_message)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with standardized responses"""
    # Log security-relevant exceptions
    if exc.status_code in [401, 403, 429]:
        logger.warning(
            f"Security exception: {exc.status_code} - {exc.detail} - "
            f"IP: {request.client.host if request.client else 'unknown'} - "
            f"Path: {request.url.path}"
        )
    
    # Create client-friendly message
    client_message = get_client_friendly_message(exc.status_code, exc.detail)
    
    # Determine error code
    error_code = f"HTTP_{exc.status_code}"
    
    response_data = create_error_response(
        status_code=exc.status_code,
        message=client_message,
        error_code=error_code,
        details=exc.detail if exc.status_code < 500 else None
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with standardized responses"""
    # Log validation errors
    logger.warning(
        f"Validation error: {len(exc.errors())} errors - "
        f"IP: {request.client.host if request.client else 'unknown'} - "
        f"Path: {request.url.path}"
    )
    
    # Extract first validation error for simplicity
    if exc.errors():
        first_error = exc.errors()[0]
        field = first_error.get("loc", ["unknown"])[-1]
        message = f"Invalid value for field '{field}'"
    else:
        message = "Invalid request data"
    
    response_data = create_error_response(
        status_code=422,
        message=message,
        error_code="VALIDATION_ERROR",
        details="Request validation failed. Please check your input data."
    )
    
    return JSONResponse(
        status_code=422,
        content=response_data
    )

async def security_error_handler(request: Request, exc: SecurityError) -> JSONResponse:
    """Handle security-specific errors"""
    # Log security errors with higher severity
    logger.error(
        f"Security error: {exc.message} - {exc.details or 'No details'} - "
        f"IP: {request.client.host if request.client else 'unknown'} - "
        f"Path: {request.url.path}"
    )
    
    response_data = create_error_response(
        status_code=400,
        message="Invalid request detected",
        error_code="SECURITY_ERROR",
        details="The request was blocked for security reasons."
    )
    
    return JSONResponse(
        status_code=400,
        content=response_data
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    # Log full error details for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)} - "
        f"IP: {request.client.host if request.client else 'unknown'} - "
        f"Path: {request.url.path}"
    )
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    response_data = create_error_response(
        status_code=500,
        message="An internal server error occurred",
        error_code="INTERNAL_ERROR"
    )
    
    return JSONResponse(
        status_code=500,
        content=response_data
    )

def setup_error_handlers(app):
    """Register all error handlers with the FastAPI app"""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SecurityError, security_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
