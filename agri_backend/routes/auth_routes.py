# routes/auth_routes.py
from fastapi import APIRouter, HTTPException, Depends, status
from models.user import UserResponse, LoginRequest, SignupRequest
from database import get_database
from datetime import datetime
from firebase_admin import auth
import logging

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# Helper function for signup/login
async def decode_firebase_token(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return {
            "success": True,
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False)
        }
    except Exception as e:
        logger.error(f"❌ Token decode failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/signup")
async def signup(signup_data: SignupRequest, db=Depends(get_database)):
    """
    Create a new user if UID does not exist
    """
    token_result = await decode_firebase_token(signup_data.id_token)
    if not token_result["success"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    uid = token_result["uid"]
    email = token_result["email"]

    # Check if UID already exists
    existing_user = await db.users.find_one({"uid": uid})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    # Optional: enforce unique email
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")

    # Create new user
    user_data = {
        "uid": uid,
        "email": email,
        "name": signup_data.name,
        "phone": signup_data.phone,
        "location": signup_data.location,
        "farm_size": signup_data.farm_size,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_active": True
    }

    await db.users.insert_one(user_data)
    logger.info(f"✅ New user created: {uid}")

    return {
        "success": True,
        "message": "User created successfully",
        "user": UserResponse(**user_data)
    }


@router.post("/login")
async def login(login_data: LoginRequest, db=Depends(get_database)):
    """
    Login with Firebase ID token
    """
    token_result = await decode_firebase_token(login_data.id_token)
    if not token_result["success"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    uid = token_result["uid"]

    # Get user by UID
    user = await db.users.find_one({"uid": uid})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please signup first."
        )

    logger.info(f"✅ Login successful for user: {uid}")

    return {
        "success": True,
        "message": "Login successful",
        "user": UserResponse(**user)
    }
