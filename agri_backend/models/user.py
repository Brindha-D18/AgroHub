from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class CropHistoryEntry(BaseModel):
    crop_name: str
    season: str
    year: int
    yield_amount: Optional[str] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "ignore"


class User(BaseModel):
    uid: str
    email: EmailStr
    name: str
    phone: Optional[str] = None

    # Location
    village: str
    state: str
    district: Optional[str] = None
    pincode: Optional[str] = None

    # Farm details
    land_size: Optional[float] = None
    land_size_unit: str = "acres"
    irrigation_type: Optional[str] = None

    # Preferences
    language: str = "en"
    preferred_contact: str = "app"

    # Crop history
    crop_history: List[CropHistoryEntry] = []

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        extra = "ignore"


class UserCreate(BaseModel):
    uid: str
    email: EmailStr
    name: str
    phone: Optional[str] = None
    village: str
    state: str
    district: Optional[str] = None
    pincode: Optional[str] = None
    land_size: Optional[float] = None
    irrigation_type: Optional[str] = None
    language: str = "en"

    class Config:
        extra = "ignore"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    village: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    land_size: Optional[float] = None
    irrigation_type: Optional[str] = None
    language: Optional[str] = None
    preferred_contact: Optional[str] = None

    class Config:
        extra = "ignore"


class UserResponse(BaseModel):
    uid: str
    email: str
    name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    farm_size: Optional[float] = None
    role: str = "farmer"
    language: str = "en"
    preferred_contact: str = "app"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "ignore"


class LoginRequest(BaseModel):
    id_token: str

    class Config:
        extra = "ignore"


class SignupRequest(BaseModel):
    id_token: str
    email: str
    name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    farm_size: Optional[float] = None
    

    class Config:
        extra = "ignore"
