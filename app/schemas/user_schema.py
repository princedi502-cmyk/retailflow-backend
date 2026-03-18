from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class BaseUser(BaseModel):
    username: str
    email: EmailStr

class UserCreate(BaseUser):
    password: str = Field(..., min_length=8, max_length=128, description="Password must be at least 8 characters long")
    role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseUser):
    id: str

    class Config:
        from_attributes = True

class UserInDB(BaseUser):
    id: str
    hashed_password: str
    salt: str
    role: str
    failed_attempts: int = 0
    lockout_until: Optional[datetime] = None
    is_email_verified: bool = False
    email_verification_token: Optional[str] = None
    email_verification_expires: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128, description="New password must be at least 8 characters long")

class EmailVerificationRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128, description="New password must be at least 8 characters long")