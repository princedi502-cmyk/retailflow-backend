import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

def generate_verification_token(length: int = 32) -> str:
    """
    Generate a secure email verification token
    
    Args:
        length: Token length (default 32 characters)
    
    Returns:
        Random token string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_token_expiry_hours(hours: int = 24) -> datetime:
    """
    Get token expiry time
    
    Args:
        hours: Hours until expiry (default 24)
    
    Returns:
        Datetime when token expires
    """
    return datetime.now(timezone.utc) + timedelta(hours=hours)

def is_token_expired(expiry_time: Optional[datetime]) -> bool:
    """
    Check if token has expired
    
    Args:
        expiry_time: Token expiry datetime
    
    Returns:
        True if expired, False otherwise
    """
    if not expiry_time:
        return True
    
    # Ensure both datetimes have timezone info for comparison
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    return now > expiry_time
