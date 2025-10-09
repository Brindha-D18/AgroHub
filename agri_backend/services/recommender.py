from typing import List, Dict
from datetime import datetime
import math
from models.recommendation import CropRecommendation

class CropRecommenderService:
    def __init__(self):
        # Crop database with requirements
        self.crop_database = {
            "Rice": {
                "ph_range": (5.5, 7.0),
                "temp_range": (20, 35),
                "water": "High",
                "duration": 120,
                "season": ["Kharif", "Rabi"],
                "nitrogen": 120,
                "profit_per_hectare": 45000,
                "yield_per_hectare": 4.0,
                "sustainability": 7.0
            },
            "Wheat": {
                "ph_range": (6.0, 7.5),
                "temp_range": (15, 25),
                "water": "Medium",
                "duration": 120,
                "season": ["Rabi"],
                "nitrogen": 100,
                "profit_per_hectare": 65000,
                "yield_per_hectare": 4.5,
                "sustainability": 8.5
            },
            "Sugarcane": {
                "ph_range": (6.0, 7.5),
                "temp_range": (25, 35),
                "water": "High",
                "duration": 365,
                "season": ["Year-round"],
                "nitrogen": 200,
                "profit_per_hectare": 120000,
                "yield_per_hectare": 70.0,
                "sustainability": 6.0
            },
            "Cotton": {
                "ph_range": (6.0, 8.0),
                "temp_range": (21, 30),
                "water": "Medium",
                "duration": 180,
                "season": ["Kharif"],
                "nitrogen": 120,
                "profit_per_hectare": 55000,
                "yield_per_hectare": 2.5,
                "sustainability": 6.5
            },
            "Maize": {
                "ph_range": (5.5, 7.0),
                "temp_range": (20, 30),
                "water": "Medium",
                "duration": 90,
                "season": ["Kharif", "Rabi"],
                "nitrogen": 150,
                "profit_per_hectare": 40000,
                "yield_per_hectare": 3.5,
                "sustainability": 8.0
            },
            "Groundnut": {
                "ph_range": (6.0, 7.0),
                "temp_range": (25, 30),
                "water": "Low",
                "duration": 120,
                "season": ["Kharif"],
                "nitrogen": 25,
                "profit_per_hectare": 50000,
                "yield_per_hectare": 2.0,
                "sustainability": 9.0
            },
            "Pulses": {
                "ph_range": (6.0, 7.5),
                "temp_range": (20, 30),
                "water": "Low",
                "duration": 90,
                "season": ["Rabi"],
                "nitrogen": 20,
                "profit_per_hectare": 35000,
                "yield_per_hectare": 1.5,
                "sustainability": 9.5
            },
            "Potato": {
                "ph_range": (5.0, 6.5),
                "temp_range": (15, 25),
                "water": "Medium",
                "duration": 90,
                "season": ["Rabi"],
                "nitrogen": 120,
                "profit_per_hectare": 80000,
                "yield_per_hectare": 25.0,
                "sustainability": 7.5
            },
            "Tomato": {
                "ph_range": (6.0, 7.0),
                "temp_range": (18, 27),
                "water": "Medium",
                "duration": 120,
                "season": ["Rabi", "Summer"],
                "nitrogen": 100,
                "profit_per_hectare": 90000,
                "yield_per_hectare": 30.0,
                "sustainability": 7.0
            },
            "Onion": {
                "ph_range": (6.0, 7.0),
                "temp_range": (20, 30),
                "water": "Medium",
                "duration": 120,
                "season": ["Kharif", "Rabi"],
                "nitrogen": 100,
                "profit_per_hectare": 70000,
                "yield_per_hectare": 20.0,
                "sustainability": 7.5
            }
        }
    
    def get_current_season(self) -> str:
        """Determine current agricultural season"""
        month = datetime.now().month
        
        if month in [6, 7, 8, 9, 10]:
            return "Kharif"  # Monsoon season
        elif month in [11, 12, 1, 2, 3]:
            return "Rabi"  # Winter season
        else:
            return "Summer"  # Summer season
    
    def calculate_crop_score(self, crop_data: Dict, soil_data: Dict, 
                            weather_data: Dict, season: str) -> float:
        """Calculate suitability score for a crop"""
        score = 0
        max_score = 0
        
        # pH suitability (30 points)
        max_score += 30
        if soil_data.get("ph"):
            ph = soil_data["ph"]
            ph_min, ph_max = crop_data["ph_range"]
            if ph_min <= ph <= ph_max:
                score += 30
            elif abs(ph - ph_min) <= 0.5 or abs(ph - ph_max) <= 0.5:
                score += 20
            elif abs(ph - ph_min) <= 1.0 or abs(ph - ph_max) <= 1.0:
                score += 10
        
        # Temperature suitability (25 points)
        max_score += 25
        if weather_data.get("temperature"):
            temp = weather_data["temperature"]
            temp_min, temp_max = crop_data["temp_range"]
            if temp_min <= temp <= temp_max:
                score += 25
            elif abs(temp - temp_min) <= 3 or abs(temp - temp_max) <= 3:
                score += 15
            elif abs(temp - temp_min) <= 5 or abs(temp - temp_max) <= 5:
                score += 8
        
        # Season match (20 points)
        max_score += 20
        if season in crop_data["season"]:
            score += 20
        
        # Nitrogen availability (15 points)
        max_score += 15
        if soil_data.get("nitrogen"):
            nitrogen = soil_data["nitrogen"]
            required = crop_data["nitrogen"]
            if nitrogen >= required:
                score += 15
            elif nitrogen >= required * 0.8:
                score += 10
            elif nitrogen >= required * 0.6:
                score += 5
        
        # Sustainability bonus (10 points)
        max_score += 10
        score += crop_data["sustainability"]
        
        return (score / max_score) if max_score > 0 else 0
    
    def generate_reasoning(self, crop_name: str, crop_data: Dict, 
                          soil_data: Dict, weather_data: Dict, 
                          score: float, season: str) -> str:
        """Generate human-readable reasoning for recommendation"""
        reasons = []
        
        # Season match
        if season in crop_data["season"]:
            reasons.append(f"Current {season} season is ideal for {crop_name}")
        
        # pH suitability
        if soil_data.get("ph"):
            ph = soil_data["ph"]
            ph_min, ph_max = crop_data["ph_range"]
            if ph_min <= ph <= ph_max:
                reasons.append(f"Soil pH ({ph:.1f}) is optimal")
            else:
                reasons.append(f"Soil pH ({ph:.1f}) may need adjustment")
        
        # Temperature
        if weather_data.get("temperature"):
            temp = weather_data["temperature"]
            temp_min, temp_max = crop_data["temp_range"]
            if temp_min <= temp <= temp_max:
                reasons.append(f"Temperature ({temp}°C) is favorable")
        
        # Water requirement
        reasons.append(f"{crop_data['water']} water requirement")
        
        # Profitability
        profit = crop_data["profit_per_hectare"]
        reasons.append(f"Expected profit: ₹{profit:,}/hectare")
        
        return ". ".join(reasons) + "."
    
    def get_market_demand(self, crop_name: str) -> str:
        """Get market demand status (would integrate with real market APIs)"""
        # High demand crops
        high_demand = ["Wheat", "Rice", "Potato", "Tomato", "Onion"]
        medium_demand = ["Maize", "Cotton", "Sugarcane"]
        
        if crop_name in high_demand:
            return "High"
        elif crop_name in medium_demand:
            return "Medium"
        else:
            return "Low"
    
    def recommend_crops(self, soil_data: Dict, weather_data: Dict, 
                       season: str = None) -> List[CropRecommendation]:
        """Generate crop recommendations based on conditions"""
        
        if not season:
            season = self.get_current_season()
        
        recommendations = []
        
        for crop_name, crop_data in self.crop_database.items():
            # Calculate suitability score
            score = self.calculate_crop_score(crop_data, soil_data, weather_data, season)
            
            # Only recommend crops with decent scores
            if score >= 0.5:
                reasoning = self.generate_reasoning(
                    crop_name, crop_data, soil_data, weather_data, score, season
                )
                
                recommendation = CropRecommendation(
                    crop_name=crop_name,
                    confidence_score=round(score, 2),
                    expected_yield=crop_data["yield_per_hectare"],
                    estimated_profit=crop_data["profit_per_hectare"],
                    sustainability_score=crop_data["sustainability"],
                    water_requirement=crop_data["water"],
                    duration_days=crop_data["duration"],
                    market_demand=self.get_market_demand(crop_name),
                    reasoning=reasoning
                )
                
                recommendations.append(recommendation)
        
        # Sort by confidence score
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Return top 5 recommendations
        return recommendations[:5]

# Singleton instance
recommender_service = CropRecommenderService()