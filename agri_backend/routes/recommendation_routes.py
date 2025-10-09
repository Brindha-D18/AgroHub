from fastapi import APIRouter, HTTPException, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging
from datetime import datetime

from database import get_database
from auth import verify_firebase_token
from models.recommendation import RecommendationResponse
from services.bhuvan_api import bhuvan_service
from services.recommender import recommender_service

router = APIRouter(prefix="/recommendations", tags=["Crop Recommendations"])
logger = logging.getLogger(__name__)

@router.get("/{uid}", response_model=RecommendationResponse)
async def get_recommendations(
    uid: str,
    force_refresh: bool = Query(False, description="Force fresh API calls"),
    top_n: int = Query(5, ge=1, le=10, description="Number of recommendations"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Get personalized crop recommendations for a user
    
    This endpoint:
    1. Fetches user profile (village, state, crop history)
    2. Gets geocode from Bhuvan API
    3. Fetches soil properties from Bhuvan/SoilGrids
    4. Generates recommendations using rule-based engine
    5. Returns top N crops with suitability scores
    """
    # Verify authorization
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access recommendations for this user"
        )
    
    try:
        # 1. Fetch user profile
        user = await db.users.find_one({"uid": uid})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile not found for UID: {uid}"
            )
        
        village = user.get("village")
        state = user.get("state")
        language = user.get("language", "en")
        crop_history = user.get("crop_history", [])
        
        if not village or not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User profile missing village or state information"
            )
        
        logger.info(f"Generating recommendations for {uid} - {village}, {state}")
        
        # 2. Check cache first (unless force_refresh)
        cache_key = f"recommendations_{uid}"
        if not force_refresh:
            cached = await db.cache.find_one({"key": cache_key})
            if cached and cached.get("expires_at") > datetime.utcnow():
                logger.info(f"Returning cached recommendations for {uid}")
                cached_data = cached.get("data")
                cached_data["from_cache"] = True
                return cached_data
        
        # 3. Get geocode from Bhuvan
        geocode = await bhuvan_service.get_village_geocode(village, state)
        
        if not geocode:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch location data. Please try again later."
            )
        
        lat = geocode["lat"]
        lon = geocode["lon"]
        
        logger.info(f"Geocode retrieved: {lat}, {lon}")
        
        # 4. Get soil properties
        soil_info = await bhuvan_service.get_soil_properties(lat, lon)
        
        if not soil_info:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch soil data. Please try again later."
            )
        
        logger.info(f"Soil info retrieved: {soil_info.get('soil_type')}, pH: {soil_info.get('ph')}")
        
        # 5. Extract previous crops from history
        prev_crops = [entry.get("crop_name") for entry in crop_history[-5:]]
        
        # 6. Generate recommendations
        recommendations = recommender_service.get_recommendations(
            soil_info=soil_info,
            prev_crops=prev_crops,
            user_language=language,
            top_n=top_n
        )
        
        # 7. Get market insights (placeholder for now)
        market_insights = recommender_service.get_market_insights()
        
        # 8. Prepare response
        response_data = RecommendationResponse(
            uid=uid,
            village=geocode["village"],
            state=geocode["state"],
            recommendations=recommendations,
            soil_info={
                "type": soil_info.get("soil_type"),
                "ph": soil_info.get("ph"),
                "moisture": soil_info.get("soil_moisture"),
                "nitrogen": soil_info.get("nitrogen"),
                "phosphorus": soil_info.get("phosphorus"),
                "potassium": soil_info.get("potassium"),
                "organic_carbon": soil_info.get("organic_carbon"),
                "coordinates": {"lat": lat, "lon": lon}
            },
            weather_info=None,  # TODO: Integrate weather API
            market_insights=market_insights,
            timestamp=datetime.utcnow()
        )
        
        # 9. Cache the result (valid for 24 hours)
        from datetime import timedelta
        await db.cache.update_one(
            {"key": cache_key},
            {
                "$set": {
                    "key": cache_key,
                    "data": response_data.dict(),
                    "expires_at": datetime.utcnow() + timedelta(hours=24),
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        logger.info(f"Successfully generated {len(recommendations)} recommendations for {uid}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )

@router.post("/{uid}/feedback")
async def submit_recommendation_feedback(
    uid: str,
    crop_name: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1-5"),
    comment: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Submit feedback on a recommendation
    This data can be used to improve ML models later
    """
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    try:
        feedback_entry = {
            "uid": uid,
            "crop_name": crop_name,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.utcnow()
        }
        
        await db.feedback.insert_one(feedback_entry)
        
        logger.info(f"Feedback received from {uid} for crop: {crop_name}")
        
        return {
            "message": "Feedback submitted successfully",
            "feedback": feedback_entry
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error submitting feedback"
        )

@router.get("/{uid}/history")
async def get_recommendation_history(
    uid: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Get user's past recommendations (from cache)
    """
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    try:
        # Fetch from cache collection
        cache_key = f"recommendations_{uid}"
        cached = await db.cache.find_one({"key": cache_key})
        
        if not cached:
            return {
                "uid": uid,
                "message": "No recommendation history found",
                "history": []
            }
        
        return {
            "uid": uid,
            "last_updated": cached.get("updated_at"),
            "recommendations": cached.get("data", {}).get("recommendations", [])
        }
        
    except Exception as e:
        logger.error(f"Error fetching recommendation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching recommendation history"
        )

@router.delete("/{uid}/cache")
async def clear_recommendation_cache(
    uid: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(verify_firebase_token)
):
    """
    Clear cached recommendations for a user
    Useful when user updates their profile
    """
    if current_user["uid"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    try:
        cache_key = f"recommendations_{uid}"
        result = await db.cache.delete_one({"key": cache_key})
        
        if result.deleted_count > 0:
            logger.info(f"Cleared recommendation cache for {uid}")
            return {"message": "Cache cleared successfully"}
        else:
            return {"message": "No cache found to clear"}
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error clearing cache"
        )