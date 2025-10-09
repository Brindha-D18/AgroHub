# database.py - Simple MongoDB connection
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URL)
db = client.agri_app

# Collections
users_collection = db.users
crops_collection = db.crops

# Simple helper to check connection
def get_database():
    """Return the MongoDB database object"""
    return db
def check_db_connection():
    try:
        client.admin.command('ping')
        print("✅ MongoDB connected successfully")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False