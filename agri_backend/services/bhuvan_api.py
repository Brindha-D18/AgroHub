import httpx
from typing import Optional, Dict
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class BhuvanAPIService:
    """Service for interacting with Bhuvan APIs"""
    
    BASE_URL = "https://bhuvan-app3.nrsc.gov.in/api"
    
    def __init__(self):
        # Two separate tokens
        self.geocode_token = os.getenv("BHUVAN_GEOCODE_TOKEN", "")
        self.lulc_token = os.getenv("BHUVAN_LULC_TOKEN", "")
        
        if not self.geocode_token:
            logger.warning("BHUVAN_GEOCODE_TOKEN not set. Geocode will use fallback data.")
        if not self.lulc_token:
            logger.warning("BHUVAN_LULC_TOKEN not set. LULC will use fallback data.")
            
    async def get_village_geocode(self, village: str, state: str) -> Optional[Dict]:
        """
        Get latitude and longitude for a village
        Returns: {"lat": float, "lon": float, "village": str}"""
        headers = {"Authorization": f"Bearer {self.geocode_token}", "Content-Type": "application/json"}
        if not self.geocode_token:
            logger.info(f"No Geocode token - using fallback geocode for {village}, {state}")
            return self._get_fallback_geocode(village, state)
           
        try:
            # If no token, use fallback immediately
           
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Bhuvan Geocode API endpoint
                url = f"{self.BASE_URL}/geocode"
                params = {
                    "village": village,
                    "state": state,
                    "format": "json"
                }
                
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                if data and len(data) > 0:
                    result = data[0]
                    return {
                        "lat": float(result.get("lat", 0)),
                        "lon": float(result.get("lon", 0)),
                        "village": result.get("display_name", village),
                        "district": result.get("district", ""),
                        "state": result.get("state", state)
                    }
                
                logger.warning(f"No geocode found for {village}, {state}")
                return self._get_fallback_geocode(village, state)
                
        except httpx.HTTPError as e:
            logger.error(f"Bhuvan geocode API error: {str(e)}")
            # Fallback to dummy coordinates for development
            return self._get_fallback_geocode(village, state)
        except Exception as e:
            logger.error(f"Unexpected error in geocode: {str(e)}")
            return self._get_fallback_geocode(village, state)
    
    async def get_lulc_data(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get Land Use Land Cover data for coordinates
        Returns soil type, land classification, vegetation index
        """
        headers = {"Authorization": f"Bearer {self.lulc_token}", "Content-Type": "application/json"}
        
        if not self.lulc_token:
            logger.info(f"No LULC token - using fallback LULC for {lat}, {lon}")
            return self._get_fallback_lulc(lat, lon)
        
        try:
            # If no token, use fallback immediately
            
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Bhuvan LULC WMS/WFS service
                url = f"{self.BASE_URL}/lulc/query"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "buffer": 500,  # 500m buffer
                    "format": "json"
                }
                
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "soil_type": data.get("soil_type", "loamy"),
                    "land_use": data.get("land_use", "agricultural"),
                    "vegetation_index": data.get("ndvi", 0.5),
                    "soil_moisture": data.get("moisture", "medium"),
                    "elevation": data.get("elevation", 300)
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Bhuvan LULC API error: {str(e)}")
            return self._get_fallback_lulc(lat, lon)
        except Exception as e:
            logger.error(f"Unexpected error in LULC: {str(e)}")
            return self._get_fallback_lulc(lat, lon)
    
    async def get_soil_properties(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get detailed soil properties (pH, nutrients, texture)
        Uses SoilGrids API as fallback if Bhuvan doesn't provide
        """
        try:
            # Try Bhuvan first
            lulc_data = await self.get_lulc_data(lat, lon)
            
            # Enrich with SoilGrids data
            soil_grid_data = await self._get_soilgrids_data(lat, lon)
            
            if lulc_data and soil_grid_data:
                return {
                    **lulc_data,
                    "ph": soil_grid_data.get("ph", 6.5),
                    "organic_carbon": soil_grid_data.get("organic_carbon", 1.5),
                    "nitrogen": soil_grid_data.get("nitrogen", "medium"),
                    "phosphorus": soil_grid_data.get("phosphorus", "medium"),
                    "potassium": soil_grid_data.get("potassium", "medium")
                }
            
            return lulc_data or soil_grid_data or self._get_fallback_soil_properties()
            
        except Exception as e:
            logger.error(f"Error getting soil properties: {str(e)}")
            return self._get_fallback_soil_properties()
    
    async def _get_soilgrids_data(self, lat: float, lon: float) -> Optional[Dict]:
        """Get data from SoilGrids API (ISRIC)"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
                params = {
                    "lon": lon,
                    "lat": lat,
                    "property": ["phh2o", "soc", "nitrogen"],
                    "depth": "0-5cm",
                    "value": "mean"
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                properties = data.get("properties", {})
                layers = properties.get("layers", [])
                
                result = {}
                for layer in layers:
                    name = layer.get("name")
                    depths = layer.get("depths", [])
                    if depths:
                        value = depths[0].get("values", {}).get("mean", 0)
                        
                        if name == "phh2o":
                            result["ph"] = value / 10  # Convert to pH scale
                        elif name == "soc":
                            result["organic_carbon"] = value / 10
                        elif name == "nitrogen":
                            result["nitrogen"] = "high" if value > 2000 else "medium" if value > 1000 else "low"
                
                logger.info(f"SoilGrids data retrieved for {lat}, {lon}")
                return result
                
        except Exception as e:
            logger.error(f"SoilGrids API error: {str(e)}")
            return {}
    
    def _get_fallback_geocode(self, village: str, state: str) -> Dict:
        """Fallback geocode data for development"""
        # Common state coordinates (approximate centers)
        state_coords = {
            "punjab": (30.9010, 75.8573),
            "haryana": (29.0588, 76.0856),
            "uttar pradesh": (26.8467, 80.9462),
            "madhya pradesh": (22.9734, 78.6569),
            "rajasthan": (27.0238, 74.2179),
            "maharashtra": (19.7515, 75.7139),
            "karnataka": (15.3173, 75.7139),
            "tamil nadu": (11.1271, 78.6569),
            "andhra pradesh": (15.9129, 79.7400),
            "telangana": (18.1124, 79.0193),
            "delhi": (28.7041, 77.1025),
            "bihar": (25.0961, 85.3131),
            "west bengal": (22.9868, 87.8550),
            "odisha": (20.9517, 85.0985),
            "kerala": (10.8505, 76.2711),
            "gujarat": (22.2587, 71.1924)
        }
        
        coords = state_coords.get(state.lower(), (20.5937, 78.9629))  # India center
        
        logger.info(f"Using fallback geocode for {village}, {state}: {coords}")
        
        return {
            "lat": coords[0],
            "lon": coords[1],
            "village": village,
            "district": "Unknown",
            "state": state,
            "fallback": True
        }
    
    def _get_fallback_lulc(self, lat: float, lon: float) -> Dict:
        """Fallback LULC data based on region"""
        logger.info(f"Using fallback LULC data for {lat}, {lon}")
        
        return {
            "soil_type": "loamy",
            "land_use": "agricultural",
            "vegetation_index": 0.6,
            "soil_moisture": "medium",
            "elevation": 300,
            "fallback": True
        }
    
    def _get_fallback_soil_properties(self) -> Dict:
        """Fallback soil properties"""
        logger.info("Using fallback soil properties")
        
        return {
            "soil_type": "loamy",
            "ph": 6.8,
            "organic_carbon": 1.2,
            "nitrogen": "medium",
            "phosphorus": "medium",
            "potassium": "medium",
            "soil_moisture": "medium",
            "fallback": True
        }

# Singleton instance
bhuvan_service = BhuvanAPIService()