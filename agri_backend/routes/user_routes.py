from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging

from database import get_database
from auth import verify_firebase_token
from models.user import User, UserUpdate

router = APIRouter(prefix="/user", tags=["User Profile"])
logger = logging.getLogger(__name__)

@router.get("/{uid}", response_model=User)
async def get_user_profile(
    uid: str,
    db = Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Get user profile by Firebase UID
    """
    # Check authorization
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this profile"
        )

    try:
        user = await db.users.find_one({"uid": uid})  # async call with await

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile not found for UID: {uid}"
            )

        user.pop("_id", None)  # remove MongoDB internal ID
        logger.info(f"Retrieved profile for user: {uid}")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user profile"
        )

@router.put("/{uid}", response_model=User)
async def update_user_profile(
    uid: str,
    user_update: UserUpdate,
    db= Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Update user profile
    """
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this profile"
        )
    try:
        # Prepare update data (exclude None values)
        update_data = user_update.dict(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update timestamp
        from datetime import datetime
        update_data["updated_at"] = datetime.utcnow()
        
        result = await db.users.update_one(
            {"uid": uid},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}"
            )
        
        # Fetch and return updated user
        updated_user = await db.users.find_one({"uid": uid})
        updated_user.pop("_id", None)
        
        logger.info(f"Updated profile for user: {uid}")
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user profile"
        )

@router.post("/{uid}/crop-history")
async def add_crop_history(
    uid: str,
    crop_name: str,
    season: str,
    year: int,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Add a crop to user's history
    """
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this profile"
        )
    
    try:
        from datetime import datetime
        
        crop_entry = {
            "crop_name": crop_name,
            "season": season,
            "year": year,
            "added_at": datetime.utcnow()
        }
        
        result = await db.users.update_one(
            {"uid": uid},
            {
                "$push": {"crop_history": crop_entry},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}"
            )
        
        logger.info(f"Added crop history for user {uid}: {crop_name}")
        return {
            "message": "Crop history added successfully",
            "crop_entry": crop_entry
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding crop history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding crop history"
        )

@router.get("/{uid}/crop-history")
async def get_crop_history(
    uid: str,
    limit: Optional[int] = 10,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Get user's crop history
    """
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this data"
        )
    
    try:
        user = await db.users.find_one(
            {"uid": uid},
            {"crop_history": 1}
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}"
            )
        
        crop_history = user.get("crop_history", [])
        
        # Sort by year and return limited results
        crop_history = sorted(
            crop_history,
            key=lambda x: (x.get("year", 0), x.get("added_at", "")),
            reverse=True
        )[:limit]
        
        return {
            "uid": uid,
            "crop_history": crop_history,
            "total_records": len(crop_history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching crop history: {str(e)}")
        raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Error fetching crop history"
)
