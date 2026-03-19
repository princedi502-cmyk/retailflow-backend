from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr, validator, BaseModel
import asyncio
from slowapi.util import get_remote_address
from bson import ObjectId

from app.schemas.user_schema import UserCreate, UserResponse, PasswordChange, EmailVerificationRequest, ResendVerificationRequest, PasswordResetRequest, PasswordResetConfirm
from app.db.mongodb import db_manager
from app.core.security import (
    hash_password_with_salt, verify_password_with_salt, create_access_token, 
    create_refresh_token, verify_token, get_token_payload, is_account_locked,
    get_lockout_time_remaining, should_lock_account, lock_account,
    reset_failed_attempts, increment_failed_attempts, MAX_FAILED_ATTEMPTS,
    LOCKOUT_DURATION_MINUTES
)
from app.core.rate_limit import limiter
from app.core.security_middleware import injection_protection
from app.utils.email_verification import generate_verification_token, get_token_expiry_hours, is_token_expired
from app.utils.password_reset import generate_reset_token, get_reset_token_expiry_hours, is_reset_token_expired
from app.utils.email_service import email_service


router = APIRouter(prefix="/auth", tags=["auth"])      

class RefreshTokenRequest(BaseModel):
    refresh_token: str      

@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate):
    # Sanitize input
    sanitized_user = injection_protection.sanitize_input(user_in.model_dump())
    
    # Validate email format
    if not injection_protection.validate_email(sanitized_user["email"]):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    # Validate password strength
    is_valid, message = injection_protection.validate_password_strength(sanitized_user["password"])
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=message
        )
    
    # Validate username
    if len(sanitized_user["username"].strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters long"
        )
    
    # Validate role
    if sanitized_user.get("role") not in ["admin", "owner", "employee"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Must be one of: admin, owner, employee"
        )
    
    # Username should only contain alphanumeric characters and underscores
    if not sanitized_user["username"].replace('_', '').isalnum():
        raise HTTPException(
            status_code=400,
            detail="Username can only contain letters, numbers, and underscores"
        )

    existing_user = await db_manager.db["users"].find_one(
        {"email": sanitized_user["email"]}
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user_dict = sanitized_user.copy()
    
    # Hash password with unique salt
    hashed_password, salt = hash_password_with_salt(sanitized_user["password"])
    user_dict["hashed_password"] = hashed_password
    user_dict["salt"] = salt
    
    # Add email verification fields
    user_dict["is_email_verified"] = False
    user_dict["email_verification_token"] = generate_verification_token()
    user_dict["email_verification_expires"] = get_token_expiry_hours(24)
    
    # Remove plain password from user_dict to prevent storing it
    del user_dict["password"]

    result = await db_manager.db["users"].insert_one(user_dict)

    # Send verification email (DISABLED FOR TESTING)
    try:
        print(f"🔍 EMAIL TEST: Would send verification to {user_dict['email']}")
        # email_sent = email_service.send_email_verification(
        #     user_dict["email"], 
        #     user_dict["email_verification_token"]
        # )
        # if not email_sent:
        #     print(f"Failed to send verification email to {user_dict['email']}")
    except Exception as e:
        print(f"Error sending verification email: {e}")

    return {
        "id": str(result.inserted_id),
        "username": user_dict["username"],
        "email": user_dict["email"],
        "role": user_dict["role"],
        "message": "Registration successful. Please check your email for verification instructions.",
        "requires_email_verification": True
    }


@router.get("/dev/verification-tokens")
@limiter.limit("5/minute")
async def get_verification_tokens(request: Request):
    """Development endpoint to get verification tokens for manual testing"""
    try:
        from app.db.mongodb import db_manager
        
        users = await db_manager.db["users"].find({
            "email_verification_token": {"$exists": True, "$ne": None},
            "is_email_verified": False
        }).to_list(length=10)
        
        tokens = []
        for user in users:
            tokens.append({
                "email": user["email"],
                "username": user["username"],
                "token": user["email_verification_token"],
                "expires": user.get("email_verification_expires"),
                "verification_link": f"http://localhost:5173/verify-email?token={user['email_verification_token']}"
            })
        
        return {
            "message": "Development endpoint - verification tokens for testing",
            "users": tokens,
            "note": "Use these tokens for manual email verification testing"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get verification tokens: {str(e)}"
        )


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    # Sanitize and validate input
    sanitized_email = injection_protection.sanitize_input(form_data.username)
    sanitized_password = injection_protection.sanitize_input(form_data.password)
    
    if not sanitized_email or not sanitized_email.strip():
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )
    
    if not sanitized_password or not sanitized_password.strip():
        raise HTTPException(
            status_code=400,
            detail="Password is required"
        )
    
    # Basic email validation
    if not injection_protection.validate_email(sanitized_email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )

    try:
        user = await asyncio.wait_for(
            db_manager.db["users"].find_one({"email": sanitized_email}),
            timeout=5
        )
    except asyncio.TimeoutError:
        print("🔥 MONGODB TIMEOUT DETECTED - Connection hanging!")
        raise HTTPException(
            status_code=503,
            detail="Database connection timeout. Please try again."
        )


    # user = await db_manager.db["users"].find_one(
    #     {"email": sanitized_email}
    # )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if account is locked
    if is_account_locked(user):
        remaining_minutes = get_lockout_time_remaining(user)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is locked. Try again in {remaining_minutes} minutes."
        )
    
    password_valid = verify_password(
        sanitized_password,
        user["hashed_password"]
    )



    # # Handle both old users (no salt) and new users (with salt)
    # password_valid = False
    # if user.get("salt"):
    # # if "salt" in user:
    #     # New user with salted password
    #     password_valid = verify_password_with_salt(
    #         sanitized_password, user["hashed_password"], user["salt"]
    #     )
    # else:
    #     # Old user with legacy password hash
    #     from app.core.security import verify_password
    #     password_valid = verify_password(sanitized_password, user["hashed_password"])
    
    if not password_valid:
        # Increment failed attempts
        user = increment_failed_attempts(user)
        
        # Check if account should be locked
        if should_lock_account(user):
            lockout_time = lock_account(user)
            await db_manager.db["users"].update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "failed_attempts": user["failed_attempts"],
                    "lockout_until": lockout_time
                }}
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked due to too many failed attempts. Try again in {LOCKOUT_DURATION_MINUTES} minutes."
            )
        else:
            # Update failed attempts count
            await db_manager.db["users"].update_one(
                {"_id": user["_id"]},
                {"$set": {"failed_attempts": user["failed_attempts"]}}
            )
            remaining_attempts = MAX_FAILED_ATTEMPTS - user["failed_attempts"]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect username or password. {remaining_attempts} attempts remaining."
            )
    
    # Reset failed attempts on successful login
    user = reset_failed_attempts(user)
    await db_manager.db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "failed_attempts": 0,
            "lockout_until": None
        }}
    )

    # Check if email is verified
    if not user.get("is_email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your inbox for verification instructions."
        )

    access_token = create_access_token(
    data={
        "sub": str(user["_id"]),
        "email":user["email"],
        "role": user.get("role")
    }
)

    refresh_token = create_refresh_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role")
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
@limiter.limit("20/minute")
async def refresh_token(request: Request, token_request: RefreshTokenRequest):
    # Sanitize input
    sanitized_refresh_token = injection_protection.sanitize_input(token_request.refresh_token)
    
    if not sanitized_refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Refresh token is required"
        )
    
    # Verify refresh token
    payload = verify_token(sanitized_refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user from database
    try:
        user = await db_manager.db["users"].find_one(
            {"_id": ObjectId(payload["sub"])}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new access token
    access_token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role")
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(request: Request, password_change: PasswordChange, token_data: dict = Depends(get_token_payload)):
    # Sanitize input
    sanitized_current = injection_protection.sanitize_input(password_change.current_password)
    sanitized_new = injection_protection.sanitize_input(password_change.new_password)
    
    if not sanitized_current or not sanitized_new:
        raise HTTPException(
            status_code=400,
            detail="Both current and new passwords are required"
        )
    
    # Get user from database
    try:
        user = await db_manager.db["users"].find_one(
            {"_id": ObjectId(token_data["sub"])}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Verify current password with salt
    if not verify_password_with_salt(sanitized_current, user["hashed_password"], user["salt"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password is same as current
    if verify_password_with_salt(sanitized_new, user["hashed_password"], user["salt"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as current password"
        )
    
    # Validate new password strength
    is_valid, message = injection_protection.validate_password_strength(sanitized_new)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=message
        )
    
    # Hash new password with new unique salt
    new_hashed_password, new_salt = hash_password_with_salt(sanitized_new)
    
    # Update user password and salt
    await db_manager.db["users"].update_one(
        {"_id": ObjectId(token_data["sub"])},
        {"$set": {
            "hashed_password": new_hashed_password,
            "salt": new_salt
        }}
    )
    
    return {"message": "Password changed successfully"}


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(request: Request, verification_data: EmailVerificationRequest):
    # Sanitize input
    sanitized_token = injection_protection.sanitize_input(verification_data.token)
    
    if not sanitized_token:
        raise HTTPException(
            status_code=400,
            detail="Verification token is required"
        )
    
    # Find user by verification token
    user = await db_manager.db["users"].find_one({
        "email_verification_token": sanitized_token
    })
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Invalid verification token"
        )
    
    # Check if token is expired
    if is_token_expired(user.get("email_verification_expires")):
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired. Please request a new one."
        )
    
    # Check if already verified
    if user.get("is_email_verified", False):
        raise HTTPException(
            status_code=400,
            detail="Email is already verified"
        )
    
    # Mark email as verified and clear verification token
    await db_manager.db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "is_email_verified": True,
            "email_verification_token": None,
            "email_verification_expires": None
        }}
    )
    
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(request: Request, resend_data: ResendVerificationRequest):
    # Sanitize input
    sanitized_email = injection_protection.sanitize_input(resend_data.email)
    
    if not sanitized_email:
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )
    
    # Validate email format
    if not injection_protection.validate_email(sanitized_email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    # Find user by email
    user = await db_manager.db["users"].find_one({
        "email": sanitized_email
    })
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found with this email address"
        )
    
    # Check if already verified
    if user.get("is_email_verified", False):
        raise HTTPException(
            status_code=400,
            detail="Email is already verified"
        )
    
    # Generate new verification token
    new_token = generate_verification_token()
    new_expiry = get_token_expiry_hours(24)
    
    # Update user with new token
    await db_manager.db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "email_verification_token": new_token,
            "email_verification_expires": new_expiry
        }}
    )
    
    # Send verification email
    try:
        email_sent = email_service.send_email_verification(
            user["email"], 
            new_token
        )
        if not email_sent:
            print(f"Failed to resend verification email to {user['email']}")
    except Exception as e:
        print(f"Error resending verification email: {e}")
    
    return {
        "message": "Verification email sent successfully. Please check your inbox.",
        "note": "For development purposes, your verification token is: " + new_token
    }


@router.post("/request-password-reset")
@limiter.limit("3/minute")
async def request_password_reset(request: Request, reset_request: PasswordResetRequest):
    # Sanitize input
    sanitized_email = injection_protection.sanitize_input(reset_request.email)
    
    if not sanitized_email:
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )
    
    # Validate email format
    if not injection_protection.validate_email(sanitized_email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    # Find user by email
    user = await db_manager.db["users"].find_one({
        "email": sanitized_email
    })
    
    if not user:
        # Don't reveal that email doesn't exist for security
        return {"message": "If an account with this email exists, a password reset link has been sent."}
    
    # Generate new reset token
    reset_token = generate_reset_token()
    reset_expiry = get_reset_token_expiry_hours(1)  # 1 hour expiry
    
    # Update user with reset token
    await db_manager.db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_reset_token": reset_token,
            "password_reset_expires": reset_expiry
        }}
    )
    
    # Send password reset email (DISABLED FOR TESTING)
    try:
        print(f"🔍 EMAIL TEST: Would send password reset to {sanitized_email}")
        # email_sent = email_service.send_password_reset_email(sanitized_email, reset_token)
        # if not email_sent:
        #     print(f"Failed to send password reset email to {sanitized_email}")
    except Exception as e:
        print(f"Error sending password reset email: {e}")
    
    return {
        "message": "Password reset link sent successfully. Please check your email.",
        "note": f"For development purposes, your reset token is: {reset_token}"
    }


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, reset_confirm: PasswordResetConfirm):
    # Sanitize input
    sanitized_token = injection_protection.sanitize_input(reset_confirm.token)
    sanitized_new_password = injection_protection.sanitize_input(reset_confirm.new_password)
    
    if not sanitized_token or not sanitized_new_password:
        raise HTTPException(
            status_code=400,
            detail="Reset token and new password are required"
        )
    
    # Find user by reset token
    user = await db_manager.db["users"].find_one({
        "password_reset_token": sanitized_token
    })
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Invalid or expired reset token"
        )
    
    # Check if token is expired
    if is_reset_token_expired(user.get("password_reset_expires")):
        # Clear expired token
        await db_manager.db["users"].update_one(
            {"_id": user["_id"]},
            {"$set": {
                "password_reset_token": None,
                "password_reset_expires": None
            }}
        )
        raise HTTPException(
            status_code=400,
            detail="Reset token has expired. Please request a new one."
        )
    
    # Validate new password strength
    is_valid, message = injection_protection.validate_password_strength(sanitized_new_password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=message
        )
    
    # Hash new password with new unique salt
    new_hashed_password, new_salt = hash_password_with_salt(sanitized_new_password)
    
    # Update user password and clear reset token
    await db_manager.db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "hashed_password": new_hashed_password,
            "salt": new_salt,
            "password_reset_token": None,
            "password_reset_expires": None,
            "failed_attempts": 0,  # Reset failed attempts on password reset
            "lockout_until": None  # Unlock account if it was locked
        }}
    )
    
    # Send password reset confirmation email
    try:
        email_sent = email_service.send_password_reset_confirmation(user["email"])
        if not email_sent:
            print(f"Failed to send password reset confirmation email to {user['email']}")
    except Exception as e:
        print(f"Error sending password reset confirmation email: {e}")
    
    return {"message": "Password reset successfully. You can now log in with your new password."}