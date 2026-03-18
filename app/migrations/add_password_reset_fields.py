"""
Migration script to add password reset fields to existing users
"""
import asyncio
from app.db.mongodb import db_manager
from datetime import datetime, timezone

async def add_password_reset_fields():
    """Add password reset fields to all existing users"""
    
    # Find all users that don't have password reset fields
    users_without_reset_fields = await db_manager.db["users"].find({
        "$or": [
            { "password_reset_token": { "$exists": False } },
            { "password_reset_expires": { "$exists": False } }
        ]
    }).to_list(length=None)
    
    print(f"Found {len(users_without_reset_fields)} users without password reset fields")
    
    if not users_without_reset_fields:
        print("All users already have password reset fields")
        return
    
    # Update each user to add the new fields
    for user in users_without_reset_fields:
        await db_manager.db["users"].update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password_reset_token": None,
                    "password_reset_expires": None
                }
            }
        )
        print(f"Updated user: {user['email']}")
    
    print(f"Successfully updated {len(users_without_reset_fields)} users")

if __name__ == "__main__":
    asyncio.run(add_password_reset_fields())
