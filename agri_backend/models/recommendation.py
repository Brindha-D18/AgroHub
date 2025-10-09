from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CropRecommendation(BaseModel):
    """Individual crop recommendation"""
    crop_name: str
    crop_name_local: Optional[str] = None
    suitability_score: float = Field(ge=0, le=100)
    expected_yield: str
    profit_margin: str
    water_requirement: str
    season: str
    reasons: List[str]
    warnings: Optional[List[str]] = []

class RecommendationResponse(BaseModel):
    """Complete recommendation response"""
    uid: str
    village: str
    state: str
    recommendations: List[CropRecommendation]
    soil_info: dict
    weather_info: Optional[dict] = None
    market_insights: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
class RecommendationRequest(BaseModel):
    """Request for getting recommendations"""
    uid: str
    force_refresh: bool = False  # Force new API calls instead of cache