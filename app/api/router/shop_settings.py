from fastapi import APIRouter, Depends, HTTPException
from app.api.router.dependency import get_current_user, require_owner
from app.schemas.shop_settings_schema import ShopSettingsUpdate, ShopSettingsResponse
from app.services.shop_settings_service import (
    get_shop_settings_by_owner,
    update_shop_settings,
    get_or_create_shop_settings
)
from app.core.rate_limit import limiter
from fastapi import Request

router = APIRouter(
    prefix="/shop-settings",
    tags=["shop-settings"]
)


@router.get("/", response_model=ShopSettingsResponse)
@limiter.limit("60/minute")
async def get_settings(
    request: Request,
    current_user: dict = Depends(require_owner)
):
    """
    Get shop settings (owner only).
    Returns default settings if none exist yet.
    """
    owner_id = str(current_user.get("_id") or current_user.get("id"))
    
    settings = await get_or_create_shop_settings(owner_id)
    
    return {
        "id": settings.id,
        "owner_id": settings.owner_id,
        "business_name": settings.business_name,
        "address": settings.address,
        "gst_number": settings.gst_number,
        "terms_conditions": settings.terms_conditions,
        "greeting_message": settings.greeting_message,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }


@router.put("/", response_model=ShopSettingsResponse)
@limiter.limit("20/minute")
async def update_settings(
    request: Request,
    settings: ShopSettingsUpdate,
    current_user: dict = Depends(require_owner)
):
    """
    Update shop settings (owner only).
    Creates default settings if they don't exist yet.
    """
    owner_id = str(current_user.get("_id") or current_user.get("id"))
    
    try:
        data = settings.model_dump(exclude_unset=True)
        updated_settings = await update_shop_settings(data, owner_id)
        
        return {
            "id": updated_settings.id,
            "owner_id": updated_settings.owner_id,
            "business_name": updated_settings.business_name,
            "address": updated_settings.address,
            "gst_number": updated_settings.gst_number,
            "terms_conditions": updated_settings.terms_conditions,
            "greeting_message": updated_settings.greeting_message,
            "created_at": updated_settings.created_at,
            "updated_at": updated_settings.updated_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
