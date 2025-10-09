# routes/maintenance.py
from fastapi import APIRouter, HTTPException
from database import users_collection
from models.user import UserResponse
from firebase_admin import auth
router = APIRouter(tags=["Maintenance"])

# Get all users
@router.get("/all-users")
def get_all_users():
    users_cursor = users_collection.find({})
    users = []
    for user in users_cursor:
        user.pop("_id", None)  # remove MongoDB _id
        users.append(UserResponse(**user))
    return {"users": users}

# Delete all users
@router.delete("/delete-all-users")
def delete_all_users():
    result = users_collection.delete_many({})
    return {"deleted_count": result.deleted_count}

# Delete single user by UID
@router.delete("/delete-user/{uid}")
def delete_user(uid: str):
    result = users_collection.delete_one({"uid": uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted_count": result.deleted_count}

@router.get("/all-firebase-users")
def get_all_users():
    users_list = []
    page = auth.list_users()
    for user in page.users:
        users_list.append({
            "uid": user.uid,
            "email": user.email,
            "name": user.display_name,
            "phone": user.phone_number
        })
    return {"users": users_list}

@router.delete("/delete-firebase-user/{uid}")
def delete_user(uid: str):
    try:
        auth.delete_user(uid)
        return {"success": True, "message": f"User {uid} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))