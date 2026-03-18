import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

def generate_reset_token(length: int = 32) -> str:
    """Generate a cryptographically secure password reset token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_reset_token_expiry_hours(hours: int = 1) -> datetime:
    """Get expiry time for reset token"""
    return datetime.now(timezone.utc) + timedelta(hours=hours)

def is_reset_token_expired(expires: Optional[datetime]) -> bool:
    """Check if reset token is expired"""
    if not expires:
        return True
    
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
    
    # Ensure both datetimes have timezone info for comparison
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    return expires < now
