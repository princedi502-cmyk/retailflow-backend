"""
Request validation middleware for additional security checks
"""
import json
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
from app.core.security_logger import security_event_logger, get_client_info

# Request size limits (in bytes)
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_JSON_SIZE = 1 * 1024 * 1024     # 1MB
MAX_URL_LENGTH = 2048               # 2KB

# Field-specific limits
FIELD_LIMITS = {
    "username": {"min": 3, "max": 50},
    "email": {"min": 5, "max": 254},
    "password": {"min": 8, "max": 128},
    "name": {"min": 1, "max": 100},
    "description": {"min": 0, "max": 1000},
    "address": {"min": 10, "max": 500},
    "phone": {"min": 10, "max": 20},
    "barcode": {"min": 1, "max": 50},
    "search": {"min": 1, "max": 100},
    "message": {"min": 1, "max": 1000},
    "token": {"min": 10, "max": 512},
}

class RequestValidationMiddleware:
    """Middleware for comprehensive request validation"""
    
    async def __call__(self, request: Request, call_next):
        client_info = get_client_info(request)
        
        try:
            # Check URL length
            if len(str(request.url)) > MAX_URL_LENGTH:
                security_event_logger.log_security_violation(
                    "URL_TOO_LONG",
                    ip_address=client_info["ip_address"],
                    endpoint=client_info["endpoint"],
                    details=f"URL length: {len(str(request.url))}"
                )
                return self.create_error_response(
                    414, "Request URL too long"
                )
            
            # Check content length for POST/PUT requests
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_REQUEST_SIZE:
                security_event_logger.log_security_violation(
                    "REQUEST_TOO_LARGE",
                    ip_address=client_info["ip_address"],
                    endpoint=client_info["endpoint"],
                    details=f"Content length: {content_length}"
                )
                return self.create_error_response(
                    413, "Request entity too large"
                )
            
            # Validate JSON body if present
            if request.method in ["POST", "PUT", "PATCH"] and \
               request.headers.get("content-type", "").startswith("application/json"):
                try:
                    body = await request.body()

                    if len(body) > MAX_JSON_SIZE:
                        security_event_logger.log_security_violation(
                            "JSON_TOO_LARGE",
                            ip_address=client_info["ip_address"],
                            endpoint=client_info["endpoint"],
                            details=f"JSON size: {len(body)}"
                        )
                        return self.create_error_response(
                            413, "JSON payload too large"
                        )
                    # 🔥 CRITICAL FIX — properly reattach body so FastAPI can read it again
                    class MutableRequest(Request):
                        def __init__(self, request: Request, body: bytes):
                            super().__init__(scope=request.scope, receive=request._receive, send=request._send)
                            self._body = body
                            self._body_consumed = False
                        
                        async def body(self) -> bytes:
                            if not self._body_consumed:
                                self._body_consumed = True
                                return self._body
                            return b''
                        
                        async def receive(self):
                            if not self._body_consumed:
                                self._body_consumed = True
                                return {"type": "http.request", "body": self._body}
                            return {"type": "http.request", "body": b""}
                    
                    # Parse and validate JSON structure
                    try:
                        json_data = json.loads(body.decode())
                        self.validate_json_fields(json_data, client_info)
                    except json.JSONDecodeError:
                        return self.create_error_response(
                            400, "Invalid JSON format"
                        )
                    
                    # Replace the request with our mutable version and continue
                    mutable_request = MutableRequest(request, body)
                    response = await call_next(mutable_request)
                    return response
                    
                except Exception as e:
                    # If body reading fails, continue with request
                    # (it might be handled by FastAPI's built-in validation)
                    pass
            
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            security_event_logger.log_security_violation(
                "REQUEST_VALIDATION_ERROR",
                ip_address=client_info["ip_address"],
                endpoint=client_info["endpoint"],
                details=str(e)
            )
            raise e 
    
    def validate_json_fields(self, data: Any, client_info: Dict[str, str], path: str = "") -> None:
        """Recursively validate JSON fields against limits"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check field name length
                if len(key) > 100:
                    security_event_logger.log_security_violation(
                        "FIELD_NAME_TOO_LONG",
                        ip_address=client_info["ip_address"],
                        endpoint=client_info["endpoint"],
                        details=f"Field: {key}, Length: {len(key)}"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Field name too long"
                    )
                
                # Validate string fields
                if isinstance(value, str):
                    self.validate_string_field(key, value, client_info, current_path)
                # Recursively validate nested structures
                elif isinstance(value, (dict, list)):
                    self.validate_json_fields(value, client_info, current_path)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                if isinstance(item, (dict, list)):
                    self.validate_json_fields(item, client_info, current_path)
                elif isinstance(item, str):
                    self.validate_string_field(f"{path}_item", item, client_info, current_path)
    
    def validate_string_field(self, field_name: str, value: str, client_info: Dict[str, str], path: str) -> None:
        """Validate individual string field"""
        # Check general string length
        if len(value) > 10000:  # 10KB max for any string field
            security_event_logger.log_security_violation(
                "STRING_FIELD_TOO_LONG",
                ip_address=client_info["ip_address"],
                endpoint=client_info["endpoint"],
                details=f"Field: {path}, Length: {len(value)}"
            )
            raise HTTPException(
                status_code=400,
                detail="String field too long"
            )
        
        # Check specific field limits
        field_key = field_name.lower()
        for limit_key, limits in FIELD_LIMITS.items():
            if limit_key in field_key:
                if len(value) < limits["min"] or len(value) > limits["max"]:
                    security_event_logger.log_security_violation(
                        "FIELD_LENGTH_VIOLATION",
                        ip_address=client_info["ip_address"],
                        endpoint=client_info["endpoint"],
                        details=f"Field: {path}, Length: {len(value)}, Limits: {limits}"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_name}' length must be between {limits['min']} and {limits['max']} characters"
                    )
                break
    
    def create_error_response(self, status_code: int, message: str) -> JSONResponse:
        """Create standardized error response"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": True,
                "status_code": status_code,
                "message": message,
                "timestamp": "2025-03-16T00:00:00.000Z"  # Will be updated by error handlers
            }
        )

# Global middleware instance
request_validation_middleware = RequestValidationMiddleware()

def add_request_validation_middleware(app):
    """Add request validation middleware to FastAPI app"""
    app.middleware("http")(request_validation_middleware)
