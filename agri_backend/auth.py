import os
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth, credentials, initialize_app
import firebase_admin
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    #firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
    
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        initialize_app(cred)
        logger.info("✅ Firebase Admin initialized successfully")
except Exception as e:
    logger.error(f"❌ Firebase Admin initialization failed: {str(e)}")
    logger.warning("⚠️  Firebase authentication may not work properly")

# Security scheme
security = HTTPBearer()

async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """
    Verify Firebase ID token from Authorization header
    Returns decoded token with user info
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    
    token = credentials.credentials
    
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(token)
        
        logger.info(f"✅ Token verified for user: {decoded_token.get('uid')}")
        
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False)
        }
        
    except auth.InvalidIdTokenError:
        logger.error("❌ Invalid Firebase ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    except auth.ExpiredIdTokenError:
        logger.error("❌ Expired Firebase ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired"
        )
    except Exception as e:
        logger.error(f"❌ Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """
    Alias for verify_firebase_token for backward compatibility
    """
    return await verify_firebase_token(credentials)
