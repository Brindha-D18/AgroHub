from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from typing import Optional
from pydantic import BaseModel
import logging
import json

from services.gemini_service import gemini_service
from auth import get_current_user
from models.user import User
from database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

class ChatRequest(BaseModel):
    message: str
    user_context: Optional[dict] = None
    chat_history: Optional[list] = None

class ChatResponse(BaseModel):
    response: str
    suggestions: list
    metadata: dict
    status: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    message: str = Form(...),
    user_context: str = Form(None),
    image: Optional[UploadFile] = File(None),
    #current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Chat with AI assistant (Gemini)
    Supports text and image inputs
    """
    try:
        # Parse user context
        context = None
        if user_context:
            try:
                context = json.loads(user_context)
            except:
                logger.warning("Failed to parse user_context")
        
        # Read image if provided
        image_bytes = None
        if image:
            image_bytes = await image.read()
            logger.info(f"Received image: {image.filename}, size: {len(image_bytes)} bytes")
        
        # Generate AI response
        result = gemini_service.generate_response(
            message=message,
            user_context=context,
            image=image_bytes
        )
        
        # Store chat in database for history
        chat_record = {
            "user_id": "test",
            "message": message,
            "response": result["response"],
            "has_image": image is not None,
            "suggestions": result.get("suggestions", []),
            "metadata": result.get("metadata", {}),
            "timestamp": None  # Will be set by database
        }
        
        try:
            await db.chat_history.insert_one(chat_record)
        except Exception as e:
            logger.error(f"Failed to store chat history: {e}")
        
        return ChatResponse(
            response=result["response"],
            suggestions=result.get("suggestions", []),
            metadata=result.get("metadata", {}),
            status=result.get("status", "success")
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )

@router.get("/chat/history")
async def get_chat_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get user's chat history
    """
    try:
        cursor = db.chat_history.find(
            {"user_id": str(current_user.id)}
        ).sort("timestamp", -1).limit(limit)
        
        history = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for item in history:
            item["id"] = str(item.pop("_id"))
        
        return {
            "status": "success",
            "data": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch chat history"
        )

@router.delete("/chat/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Clear user's chat history
    """
    try:
        result = await db.chat_history.delete_many(
            {"user_id": str(current_user.id)}
        )
        
        return {
            "status": "success",
            "message": f"Deleted {result.deleted_count} chat messages"
        }
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear chat history"
        )

@router.post("/analyze-image")
async def analyze_crop_image(
    image: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze crop/plant image for disease detection
    """
    try:
        # Read image
        image_bytes = await image.read()
        
        # Prepare prompt for image analysis
        analysis_prompt = """Analyze this crop/plant image and provide:

1. **Plant/Crop Identification:**
   - What plant/crop is this?
   - Growth stage

2. **Health Assessment:**
   - Overall health status
   - Any visible issues

3. **Disease/Pest Detection:**
   - Identify any diseases or pests
   - Severity level (Mild/Moderate/Severe)

4. **Treatment Recommendations:**
   - Immediate actions needed
   - Recommended treatments (preferably organic)
   - Estimated costs in INR

5. **Prevention Tips:**
   - How to prevent this in future
   - Best practices

Please be specific and practical for Indian farmers."""

        if description:
            analysis_prompt += f"\n\nFarmer's description: {description}"
        
        # Generate AI analysis
        result = gemini_service.generate_response(
            message=analysis_prompt,
            image=image_bytes
        )
        
        return {
            "status": "success",
            "analysis": result["response"],
            "suggestions": result.get("suggestions", []),
            "metadata": result.get("metadata", {})
        }
        
    except Exception as e:
        logger.error(f"Image analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze image: {str(e)}"
        )

@router.get("/suggestions")
async def get_quick_suggestions(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get quick suggestion prompts for users
    """
    suggestions = {
        "crop": [
            "What crops should I grow this season?",
            "Best crops for my soil type",
            "High profit crops for small farms",
            "Crops with low water requirement"
        ],
        "disease": [
            "How to identify crop diseases?",
            "Common pests in my region",
            "Organic pest control methods",
            "When to spray pesticides?"
        ],
        "weather": [
            "What is the weather forecast?",
            "When will it rain next?",
            "Best time for harvesting?",
            "How to prepare for monsoon?"
        ],
        "market": [
            "What are current market prices?",
            "When should I sell my crops?",
            "Which crops have high demand?",
            "How to get better prices?"
        ],
        "irrigation": [
            "How much water do my crops need?",
            "What is drip irrigation?",
            "How to save water?",
            "When should I irrigate?"
        ],
        "general": [
            "What crops should I grow?",
            "How is the weather?",
            "Show market prices",
            "Identify this disease (upload image)",
            "Best fertilizer for my crop",
            "How to improve soil health?"
        ]
    }
    
    if category and category in suggestions:
        return {
            "status": "success",
            "category": category,
            "suggestions": suggestions[category]
        }
    
    return {
        "status": "success",
        "suggestions": suggestions
    }



class TranslateRequest(BaseModel):
    text: str
    target_language: str

@router.post("/translate")
async def translate_text(req: TranslateRequest):
    """
    Translate text to target language using Google Translate API or Gemini
    """
    try:
        language_map = {
            'en-IN': 'en',
            'hi-IN': 'hi',
            'ta-IN': 'ta',
            'te-IN': 'te',
            'bn-IN': 'bn',
            'mr-IN': 'mr',
            'gu-IN': 'gu'
        }
        
        target_lang_code = language_map.get(req.target_language, 'en')
        
        translation_prompt = f"""Translate the following text to {target_lang_code} language. 
Only provide the translation, no explanations:

Text: {req.text}

Translation:"""
        
        result = gemini_service.generate_response(
            message=translation_prompt,
            user_context=None
        )
        
        translated_text = result["response"].strip()
        
        return {
            "status": "success",
            "original_text": req.text,
            "translated_text": translated_text,
            "target_language": req.target_language
        }
        
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return {
            "status": "error",
            "original_text": req.text,
            "translated_text": req.text,
            "target_language": req.target_language,
            "error": "Translation service unavailable, showing original text"
        }
