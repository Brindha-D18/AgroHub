import os
import google.generativeai as genai
from typing import Optional, Dict, List
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            logger.warning("GEMINI_API_KEY not found, using mock responses")
            self.model = None
        
        # System prompt for agriculture context
        self.system_prompt = """You are an expert AI Agricultural Assistant for Indian farmers. 

Your role:
- Provide accurate, practical farming advice
- Consider Tamil and Indian agricultural context, seasons, and crops
- Use simple language, avoid overly technical jargon
- Be encouraging and supportive
- Provide actionable recommendations
- Consider local market conditions and prices in INR

Guidelines:
- Always prioritize farmer safety and sustainable practices
- Recommend organic/natural solutions when possible
- Provide cost-effective solutions
- Consider small-scale farming realities
- Be aware of Indian agricultural seasons (Kharif, Rabi, Zaid)
- Use Indian units (acres, quintals, etc.)

For crop diseases:
- Ask for image if not provided
- Describe symptoms clearly
- Provide treatment options with costs
- Mention prevention strategies

Format responses with:
- Clear headings using **bold**
- Bullet points for lists
- Step-by-step instructions when needed
- Emoji for visual appeal (but use sparingly)"""

    def generate_response(
        self, 
        message: str, 
        user_context: Optional[Dict] = None,
        image: Optional[bytes] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Generate AI response using Gemini
        """
        try:
            if not self.model:
                return self._generate_mock_response(message, user_context)
            
            # Build context-aware prompt
            context_info = self._build_context(user_context)
            full_prompt = f"{self.system_prompt}\n\n{context_info}\n\nUser Question: {message}"
            
            # Handle image + text query
            if image:
                img = Image.open(io.BytesIO(image))
                response = self.model.generate_content([full_prompt, img])
            else:
                response = self.model.generate_content(full_prompt)
            
            # Extract response
            response_text = response.text
            
            # Generate suggestions based on query
            suggestions = self._generate_suggestions(message, response_text)
            
            # Extract metadata
            metadata = self._extract_metadata(response_text, user_context)
            
            return {
                "response": response_text,
                "suggestions": suggestions,
                "metadata": metadata,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return self._generate_fallback_response(message, user_context)
    
    def _build_context(self, user_context: Optional[Dict]) -> str:
        """Build context information for better responses"""
        if not user_context:
            return ""
        
        context_parts = ["**Farmer Context:**"]
        
        if user_context.get("village"):
            context_parts.append(f"- Location: {user_context['village']}, {user_context.get('state', '')}")
        
        if user_context.get("district"):
            context_parts.append(f"- District: {user_context['district']}")
        
        if user_context.get("land_size"):
            context_parts.append(f"- Farm Size: {user_context['land_size']} acres")
        
        # Add current season
        from services.recommender import recommender_service
        season = recommender_service.get_current_season()
        context_parts.append(f"- Current Season: {season}")
        
        return "\n".join(context_parts)
    
    def _generate_suggestions(self, message: str, response: str) -> List[str]:
        """Generate follow-up suggestions"""
        message_lower = message.lower()
        
        suggestions = []
        
        if any(word in message_lower for word in ['crop', 'plant', 'grow', 'recommend']):
            suggestions = [
                "What is the best irrigation schedule?",
                "How to prepare soil for planting?",
                "What fertilizers should I use?"
            ]
        elif any(word in message_lower for word in ['disease', 'pest', 'problem', 'leaf']):
            suggestions = [
                "How can I prevent this in future?",
                "What organic treatments are available?",
                "How much will treatment cost?"
            ]
        elif any(word in message_lower for word in ['price', 'market', 'sell']):
            suggestions = [
                "When is the best time to sell?",
                "Which crops have highest demand?",
                "How to get better prices?"
            ]
        elif any(word in message_lower for word in ['water', 'irrigation', 'rain']):
            suggestions = [
                "How to save water?",
                "What is drip irrigation cost?",
                "How to check soil moisture?"
            ]
        else:
            suggestions = [
                "What crops should I grow?",
                "How is the weather forecast?",
                "What are current market prices?"
            ]
        
        return suggestions[:3]  # Return top 3
    
    def _extract_metadata(self, response: str, user_context: Optional[Dict]) -> Dict:
        """Extract metadata from response"""
        metadata = {
            "language": user_context.get("language", "en") if user_context else "en",
            "response_length": len(response),
            "has_recommendations": any(word in response.lower() for word in ['recommend', 'suggest', 'advise'])
        }
        return metadata
    
    def _generate_mock_response(self, message: str, user_context: Optional[Dict]) -> Dict:
        """Generate mock response when API key is not available"""
        location = f"{user_context.get('village', 'your area')}, {user_context.get('state', '')}" if user_context else "your area"
        
        mock_responses = {
            "crop": f"""**Crop Recommendations for {location}**

Based on current conditions, here are the best crops:

🌾 **Top 3 Recommendations:**

1. **Wheat**
   - Expected Yield: 4.5 tons/hectare
   - Profit: ₹65,000/hectare
   - Duration: 120 days
   - Why: Perfect for current Rabi season

2. **Potato**
   - Expected Yield: 25 tons/hectare
   - Profit: ₹80,000/hectare
   - Duration: 90 days
   - Why: High market demand

3. **Mustard**
   - Expected Yield: 1.5 tons/hectare
   - Profit: ₹45,000/hectare
   - Duration: 120 days
   - Why: Low water requirement

**Next Steps:**
1. Prepare field with proper plowing
2. Ensure soil pH is 6-7
3. Apply basal fertilizer
4. Plan irrigation schedule

Would you like detailed growing instructions?""",
            
            "disease": """**Plant Disease Analysis**

To provide accurate diagnosis, I need a clear photo of:
📸 Affected leaves or plant parts
📸 Close-up of any spots or discoloration
📸 Overall plant condition

**Common diseases in your region:**

🦠 **Leaf Blight**
- Symptoms: Brown spots on leaves
- Treatment: Copper fungicide spray
- Cost: ₹300-500

🐛 **Aphid Infestation**
- Symptoms: Sticky leaves, small insects
- Treatment: Neem oil spray (organic)
- Cost: ₹200-300

🍄 **Root Rot**
- Symptoms: Wilting, yellowing
- Treatment: Improve drainage, reduce water
- Cost: Minimal

**Prevention Tips:**
✓ Crop rotation
✓ Proper spacing
✓ Regular monitoring
✓ Remove infected plants early

Please upload an image for specific diagnosis!""",
            
            "weather": f"""**Weather Forecast for {location}**

🌡️ **Current Conditions:**
- Temperature: 22°C (Comfortable)
- Humidity: 65%
- Rainfall: None today
- Wind: 12 km/h

📅 **7-Day Forecast:**
- Next 3 days: Clear skies
- Day 4-5: Partly cloudy
- Day 6-7: Light rain expected (15mm)

💧 **Irrigation Recommendation:**
✅ No irrigation needed for next 2 days
⏰ Plan light watering on day 3
🌧️ Rain expected, reduce irrigation after day 6

**Farming Advisory:**
- Good weather for spraying pesticides (next 2 days)
- Ideal for harvesting operations
- Prepare drainage for upcoming rain

Stay updated with daily forecasts!""",
            
            "price": f"""**Market Prices - {location} Mandi**

💰 **Today's Rates:**

🌾 **Wheat:** ₹2,850/quintal ⬆️ (+5%)
🥔 **Potato:** ₹1,200/quintal ➡️ (stable)
🌻 **Mustard:** ₹6,500/quintal ⬆️ (+8%)
🌽 **Maize:** ₹2,100/quintal ⬇️ (-2%)
🍅 **Tomato:** ₹1,800/quintal ⬆️ (+12%)
🧅 **Onion:** ₹2,400/quintal ⬆️ (+6%)

📈 **Market Trends:**
- High demand: Wheat, Tomato
- Stable prices: Potato, Maize
- Rising prices: Mustard, Onion

💡 **Selling Tips:**
✓ Best time to sell: Next week
✓ Premium for quality grading
✓ Consider nearby markets for better rates
✓ Avoid selling immediately after harvest

**Price Alert:** 
Wheat prices expected to rise by 3-5% next month due to good demand.

Would you like price predictions for specific crops?"""
        }
        
        # Match response based on keywords
        message_lower = message.lower()
        response_text = mock_responses.get("crop")  # default
        
        if any(word in message_lower for word in ['disease', 'pest', 'problem', 'leaf', 'sick']):
            response_text = mock_responses['disease']
        elif any(word in message_lower for word in ['weather', 'rain', 'temperature', 'forecast']):
            response_text = mock_responses['weather']
        elif any(word in message_lower for word in ['price', 'market', 'sell', 'rate', 'mandi']):
            response_text = mock_responses['price']
        
        suggestions = self._generate_suggestions(message, response_text)
        
        return {
            "response": response_text,
            "suggestions": suggestions,
            "metadata": {"mock": True},
            "status": "success"
        }
    
    def _generate_fallback_response(self, message: str, user_context: Optional[Dict]) -> Dict:
        """Fallback response on error"""
        return {
            "response": """I apologize, but I'm having trouble processing your request right now. 

Here's what you can do:
1. Try asking your question again
2. Check your internet connection
3. Contact local agricultural extension officer

**Common Topics I Can Help With:**
🌾 Crop recommendations
💧 Irrigation guidance
🦠 Disease identification
💰 Market prices
🌡️ Weather information

Please try asking again!""",
            "suggestions": [
                "What crops should I plant?",
                "Show me market prices",
                "How is the weather?"
            ],
            "metadata": {"error": True},
            "status": "error"
        }

# Singleton instance
gemini_service = GeminiService()