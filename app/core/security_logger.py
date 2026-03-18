"""
Security event logging system for monitoring and auditing
"""
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import Request
from app.core.config import settings

# Configure security logger
security_logger = logging.getLogger("security")

class SecurityEventLogger:
    """Centralized security event logging"""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
    
    def log_authentication_event(
        self,
        event_type: str,
        email: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        details: Optional[str] = None
    ):
        """Log authentication-related events"""
        event_data = {
            "event_type": "AUTHENTICATION",
            "sub_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "email": email,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details
        }
        
        if success:
            self.logger.info(f"AUTH_SUCCESS: {json.dumps(event_data)}")
        else:
            self.logger.warning(f"AUTH_FAILURE: {json.dumps(event_data)}")
    
    def log_authorization_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        success: bool = True,
        details: Optional[str] = None
    ):
        """Log authorization-related events"""
        event_data = {
            "event_type": "AUTHORIZATION",
            "sub_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "user_id": user_id,
            "user_role": user_role,
            "ip_address": ip_address,
            "endpoint": endpoint,
            "method": method,
            "details": details
        }
        
        if success:
            self.logger.info(f"AUTHZ_SUCCESS: {json.dumps(event_data)}")
        else:
            self.logger.warning(f"AUTHZ_FAILURE: {json.dumps(event_data)}")
    
    def log_security_violation(
        self,
        violation_type: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[str] = None,
        severity: str = "MEDIUM"
    ):
        """Log security violations"""
        event_data = {
            "event_type": "SECURITY_VIOLATION",
            "sub_type": violation_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "user_id": user_id,
            "ip_address": ip_address,
            "endpoint": endpoint,
            "details": details
        }
        
        if severity == "HIGH":
            self.logger.error(f"SECURITY_VIOLATION_HIGH: {json.dumps(event_data)}")
        elif severity == "MEDIUM":
            self.logger.warning(f"SECURITY_VIOLATION_MEDIUM: {json.dumps(event_data)}")
        else:
            self.logger.info(f"SECURITY_VIOLATION_LOW: {json.dumps(event_data)}")
    
    def log_rate_limit_event(
        self,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        limit_type: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log rate limiting events"""
        event_data = {
            "event_type": "RATE_LIMIT",
            "sub_type": limit_type or "EXCEEDED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip_address": ip_address,
            "endpoint": endpoint,
            "details": details
        }
        
        self.logger.warning(f"RATE_LIMIT_EXCEEDED: {json.dumps(event_data)}")
    
    def log_data_access(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        details: Optional[str] = None
    ):
        """Log data access events"""
        event_data = {
            "event_type": "DATA_ACCESS",
            "sub_type": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details
        }
        
        if success:
            self.logger.info(f"DATA_ACCESS_SUCCESS: {json.dumps(event_data)}")
        else:
            self.logger.warning(f"DATA_ACCESS_FAILURE: {json.dumps(event_data)}")
    
    def log_system_event(
        self,
        event_type: str,
        details: Optional[str] = None,
        severity: str = "INFO"
    ):
        """Log system-level security events"""
        event_data = {
            "event_type": "SYSTEM",
            "sub_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "details": details
        }
        
        if severity == "ERROR":
            self.logger.error(f"SYSTEM_ERROR: {json.dumps(event_data)}")
        elif severity == "WARNING":
            self.logger.warning(f"SYSTEM_WARNING: {json.dumps(event_data)}")
        else:
            self.logger.info(f"SYSTEM_INFO: {json.dumps(event_data)}")

# Global instance
security_event_logger = SecurityEventLogger()

def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client information from request"""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "endpoint": str(request.url.path),
        "method": request.method
    }

def setup_security_logging():
    """Configure security logging with appropriate handlers and formatters"""
    # Create security logger if it doesn't exist
    logger = logging.getLogger("security")
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create file handler for security events
    try:
        file_handler = logging.FileHandler("security_events.log")
        file_handler.setLevel(logging.INFO)
    except Exception:
        # If file handler fails, just use console
        file_handler = None
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    if file_handler:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
