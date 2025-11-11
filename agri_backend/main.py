# main.py - Simple FastAPI app
import logging
import sys

# -----------------------------
# Logging setup - MUST be first
# -----------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,  # Show INFO and above
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("💡 Logger initialized successfully")

# -----------------------------
# FastAPI & imports
# -----------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth_routes import router as auth_router
from routes.user_routes import router as user_router
from routes.recommendation_routes import router as recommendation_router
from routes.maintenance import router as maintenance_router
from database import check_db_connection
from routes.assistant_routes import router as assistant_router

# -----------------------------
# Firebase Admin initialization
# -----------------------------
try:
    import firebase_admin
    from firebase_admin import credentials

    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        logger.info("✅ Firebase Admin initialized successfully")
except Exception as e:
    logger.error(f"❌ Firebase Admin initialization failed: {str(e)}")

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(
    title="Agri Decision Support API",
    description="Simple API for agricultural decision support system",
    version="1.0.0"
)

# -----------------------------
# CORS middleware
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Include routers
# -----------------------------
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(recommendation_router)
app.include_router(maintenance_router)
app.include_router(assistant_router)

# -----------------------------
# Startup event
# -----------------------------
@app.on_event("startup")
async def startup_event():
    """Check database connection on startup"""
    if check_db_connection():
        logger.info("✅ MongoDB connected successfully")
    else:
        logger.error("❌ MongoDB connection failed")

# -----------------------------
# Endpoints
# -----------------------------
@app.get("/")
async def root():
    """Simple health check"""
    logger.info("🏠 Root endpoint called")
    return {
        "message": "🌾 Agri Decision Support API is running!",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if check_db_connection() else "disconnected"
    logger.info(f"🩺 Health check called - DB: {db_status}")
    return {
        "status": "healthy",
        "database": db_status
    }

# -----------------------------
# Run the app
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Uvicorn server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
