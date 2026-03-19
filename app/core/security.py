# from datetime import datetime,timedelta, timezone
# from typing import Optional
# import secrets
# import string
# from jose import jwt
# from passlib.context import CryptContext
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from app.core.config import settings 

# # Account lockout settings
# MAX_FAILED_ATTEMPTS = 5
# LOCKOUT_DURATION_MINUTES = 30

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def generate_salt(length: int = 32) -> str:
#     """Generate a cryptographically secure random salt"""
#     alphabet = string.ascii_letters + string.digits + string.punctuation
#     return ''.join(secrets.choice(alphabet) for _ in range(length))

# def hash_password_with_salt(password: str, salt: str = None) -> tuple[str, str]:
#     """
#     Hash password with unique salt
#     Returns: (hashed_password, salt)
#     """
#     if not isinstance(password, str):
#         password = str(password)
    
#     # Generate salt if not provided
#     if salt is None:
#         salt = generate_salt()
    
#     # Truncate password to 72 chars for bcrypt compatibility
#     password = password[:72]
    
#     # Hash the password (bcrypt handles salting internally)
#     hashed = pwd_context.hash(password)
    
#     return hashed, salt

# def verify_password_with_salt(plain_password: str, hashed_password: str, salt: str) -> bool:
#     """Verify password against hashed password with salt"""
#     # Truncate password to 72 chars for bcrypt compatibility
#     plain_password = plain_password[:72]
    
#     # Verify against stored hash
#     return pwd_context.verify(plain_password, hashed_password)

# # Legacy functions for backward compatibility
# def hashed_password(password: str) -> str:
#     """Legacy function - use hash_password_with_salt instead"""
#     hashed, _ = hash_password_with_salt(password)
#     return hashed

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """Legacy function - requires salt for proper verification"""
#     # This will only work if salt is embedded in hash (bcrypt)
#     if len(plain_password) > 72:
#         plain_password = plain_password[:72]
#     return pwd_context.verify(plain_password, hashed_password)

# def create_access_token(data:dict, expires_delta:Optional[timedelta]=None):
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))    
#     to_encode.update({"exp":expire})
#     return jwt.encode(to_encode,settings.SECRET_KEY,algorithm=settings.ALGORITHM)

# def create_refresh_token(data:dict):
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
#     to_encode.update({"exp":expire, "type": "refresh"})
#     return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# def verify_token(token: str):
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#         return payload
#     except jwt.ExpiredSignatureError:
#         return None
#     except jwt.JWTError:
#         return None

# async def get_token_payload(token: str = Depends(OAuth2PasswordBearer(tokenUrl="auth/login"))):
#     """Get token payload without user lookup - for password change endpoint"""
#     try:
#         payload = jwt.decode(
#             token,
#             settings.SECRET_KEY,
#             algorithms=[settings.ALGORITHM]
#         )
#         return payload
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired"
#         )
#     except jwt.JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token"
#         )

# def is_account_locked(user: dict) -> bool:
#     """Check if user account is locked"""
#     if not user.get("lockout_until"):
#         return False
    
#     lockout_until = user["lockout_until"]
#     if isinstance(lockout_until, str):
#         lockout_until = datetime.fromisoformat(lockout_until.replace('Z', '+00:00'))
#         # Ensure timezone info is present
#         if lockout_until.tzinfo is None:
#             lockout_until = lockout_until.replace(tzinfo=timezone.utc)
    
#     return lockout_until > datetime.now(timezone.utc)

# def get_lockout_time_remaining(user: dict) -> int:
#     """Get remaining lockout time in minutes"""
#     if not user.get("lockout_until"):
#         return 0
    
#     lockout_until = user["lockout_until"]
#     if isinstance(lockout_until, str):
#         lockout_until = datetime.fromisoformat(lockout_until.replace('Z', '+00:00'))
#         # Ensure timezone info is present
#         if lockout_until.tzinfo is None:
#             lockout_until = lockout_until.replace(tzinfo=timezone.utc)
    
#     remaining = lockout_until - datetime.now(timezone.utc)
#     return max(0, int(remaining.total_seconds() / 60))

# def should_lock_account(user: dict) -> bool:
#     """Check if account should be locked based on failed attempts"""
#     return user.get("failed_attempts", 0) >= MAX_FAILED_ATTEMPTS

# def lock_account(user: dict) -> datetime:
#     """Lock user account for specified duration"""
#     lockout_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
#     return lockout_until

# def reset_failed_attempts(user: dict) -> dict:
#     """Reset failed attempts counter"""
#     user["failed_attempts"] = 0
#     user["lockout_until"] = None
#     return user

# def increment_failed_attempts(user: dict) -> dict:
#     """Increment failed attempts counter"""
#     user["failed_attempts"] = user.get("failed_attempts", 0) + 1
#     return user


from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import string
import hashlib

from jose import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

# ------------------- CONFIG -------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

# ------------------- SALT -------------------

def generate_salt(length: int = 16) -> str:
    """Generate compact secure salt"""
    return secrets.token_hex(length)  # smaller & secure


# ------------------- PASSWORD -------------------

def _normalize(password: str, salt: str) -> str:
    """
    Combine password + salt and hash with SHA256
    → ensures fixed length (<72 bytes always)
    """
    combined = f"{password}{salt}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def hash_password_with_salt(password: str, salt: str = None):
    print("🔥 RAW PASSWORD LENGTH:", len(password))
    
    normalized = _normalize(password, salt)
    
    print("✅ NORMALIZED LENGTH:", len(normalized))
    
    hashed = pwd_context.hash(normalized)
    
    return hashed, salt


def verify_password_with_salt(plain_password: str, hashed_password: str, salt: str) -> bool:
    normalized = _normalize(plain_password, salt)
    return pwd_context.verify(normalized, hashed_password)


# ------------------- LEGACY SUPPORT -------------------

def hash_password(password: str) -> str:
    hashed, _ = hash_password_with_salt(password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # fallback (no salt)
    normalized = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.verify(normalized, hashed_password)


# ------------------- JWT -------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None


async def get_token_payload(token: str = Depends(OAuth2PasswordBearer(tokenUrl="auth/login"))):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ------------------- ACCOUNT LOCK -------------------

def is_account_locked(user: dict) -> bool:
    lockout_until = user.get("lockout_until")
    if not lockout_until:
        return False

    if isinstance(lockout_until, str):
        lockout_until = datetime.fromisoformat(lockout_until.replace('Z', '+00:00'))

    return lockout_until > datetime.now(timezone.utc)


def get_lockout_time_remaining(user: dict) -> int:
    lockout_until = user.get("lockout_until")
    if not lockout_until:
        return 0

    if isinstance(lockout_until, str):
        lockout_until = datetime.fromisoformat(lockout_until.replace('Z', '+00:00'))

    remaining = lockout_until - datetime.now(timezone.utc)
    return max(0, int(remaining.total_seconds() / 60))


def should_lock_account(user: dict) -> bool:
    return user.get("failed_attempts", 0) >= MAX_FAILED_ATTEMPTS


def lock_account(user: dict) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)


def reset_failed_attempts(user: dict) -> dict:
    user["failed_attempts"] = 0
    user["lockout_until"] = None
    return user


def increment_failed_attempts(user: dict) -> dict:
    user["failed_attempts"] = user.get("failed_attempts", 0) + 1
    return user