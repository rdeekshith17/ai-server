"""
Authentication Service for SecureGuard Multi-Tenant Platform
Uses Emergent Google OAuth for social login
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid
import httpx
import logging

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Constants
SESSION_EXPIRY_DAYS = 7
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


# ===========================================
# MODELS
# ===========================================

class UserRole:
    SUPER_ADMIN = "super_admin"
    CLIENT_OWNER = "client_owner"
    CLIENT_STAFF = "client_staff"
    CLIENT_VIEWER = "client_viewer"

class UserPermissions:
    """Role-based permissions mapping"""
    PERMISSIONS = {
        UserRole.SUPER_ADMIN: {
            "view_dashboard": True,
            "view_live": True,
            "view_incidents": True,
            "manage_incidents": True,
            "manage_cameras": True,
            "manage_watchlist": True,
            "view_analytics": True,
            "manage_users": True,
            "manage_clients": True,  # Admin only
            "manage_settings": True,
            "manage_billing": True,
            "api_access": True,
            "system_health": True,  # Admin only
            "ai_model_control": True,  # Admin only
        },
        UserRole.CLIENT_OWNER: {
            "view_dashboard": True,
            "view_live": True,
            "view_incidents": True,
            "manage_incidents": True,
            "manage_cameras": True,
            "manage_watchlist": True,
            "view_analytics": True,
            "manage_users": True,
            "manage_clients": False,
            "manage_settings": True,
            "manage_billing": True,
            "api_access": True,
            "system_health": False,
            "ai_model_control": True,
        },
        UserRole.CLIENT_STAFF: {
            "view_dashboard": True,
            "view_live": True,
            "view_incidents": True,
            "manage_incidents": True,  # Can acknowledge alerts
            "manage_cameras": False,
            "manage_watchlist": False,
            "view_analytics": True,
            "manage_users": False,
            "manage_clients": False,
            "manage_settings": False,
            "manage_billing": False,
            "api_access": False,
            "system_health": False,
            "ai_model_control": False,
        },
        UserRole.CLIENT_VIEWER: {
            "view_dashboard": True,
            "view_live": True,
            "view_incidents": True,
            "manage_incidents": False,
            "manage_cameras": False,
            "manage_watchlist": False,
            "view_analytics": True,
            "manage_users": False,
            "manage_clients": False,
            "manage_settings": False,
            "manage_billing": False,
            "api_access": False,
            "system_health": False,
            "ai_model_control": False,
        },
    }
    
    @classmethod
    def get_permissions(cls, role: str) -> Dict[str, bool]:
        return cls.PERMISSIONS.get(role, cls.PERMISSIONS[UserRole.CLIENT_VIEWER])


class SessionData(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    session_token: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str
    permissions: Dict[str, bool]
    client_id: Optional[str] = None
    client_name: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    user: Optional[UserResponse] = None
    message: Optional[str] = None


# ===========================================
# DEPENDENCY: Get current user
# ===========================================

async def get_current_user(request: Request, db: AsyncIOMotorDatabase) -> Optional[Dict[str, Any]]:
    """
    Extract and validate user from session token.
    Checks cookies first, then Authorization header.
    """
    session_token = None
    
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        return None
    
    # Find session in database
    session = await db.user_sessions.find_one(
        {
            "session_token": session_token,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        },
        {"_id": 0}
    )
    
    if not session:
        return None
    
    # Get user data
    user = await db.users.find_one(
        {"user_id": session["user_id"]},
        {"_id": 0}
    )
    
    if not user:
        return None
    
    # Get client info if user has client_id
    client = None
    if user.get("client_id"):
        client = await db.clients.find_one(
            {"client_id": user["client_id"]},
            {"_id": 0, "client_id": 1, "name": 1, "status": 1}
        )
    
    return {
        **user,
        "session_token": session_token,
        "client": client
    }


async def require_auth(request: Request, db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Dependency that requires authentication"""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(request: Request, db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Dependency that requires admin role"""
    user = await require_auth(request, db)
    if user.get("role") != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def check_permission(user: Dict[str, Any], permission: str) -> bool:
    """Check if user has specific permission"""
    permissions = UserPermissions.get_permissions(user.get("role", UserRole.CLIENT_VIEWER))
    return permissions.get(permission, False)


# ===========================================
# AUTH ROUTES
# ===========================================

def create_auth_routes(db: AsyncIOMotorDatabase) -> APIRouter:
    """Create auth router with database dependency"""
    
    @auth_router.post("/session", response_model=AuthResponse)
    async def process_session(request: Request, response: Response):
        """
        Process session_id from Emergent OAuth callback.
        Exchange session_id for session_token and user data.
        """
        try:
            body = await request.json()
            session_id = body.get("session_id")
            
            if not session_id:
                return AuthResponse(success=False, message="Missing session_id")
            
            # Exchange session_id with Emergent Auth
            async with httpx.AsyncClient() as client:
                auth_response = await client.get(
                    EMERGENT_AUTH_URL,
                    headers={"X-Session-ID": session_id}
                )
                
                if auth_response.status_code != 200:
                    logger.error(f"Emergent auth failed: {auth_response.text}")
                    return AuthResponse(success=False, message="Authentication failed")
                
                session_data = SessionData(**auth_response.json())
            
            # Check if user exists
            existing_user = await db.users.find_one(
                {"email": session_data.email},
                {"_id": 0}
            )
            
            if existing_user:
                # Update existing user
                user_id = existing_user["user_id"]
                await db.users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "name": session_data.name,
                            "picture": session_data.picture,
                            "last_login_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        },
                        "$inc": {"login_count": 1}
                    }
                )
                role = existing_user.get("role", UserRole.CLIENT_VIEWER)
                client_id = existing_user.get("client_id")
            else:
                # Create new user - first user becomes super admin
                user_count = await db.users.count_documents({})
                user_id = f"usr_{uuid.uuid4().hex[:12]}"
                
                if user_count == 0:
                    # First user is super admin
                    role = UserRole.SUPER_ADMIN
                    client_id = None
                else:
                    # Default to client viewer (admin will assign proper role)
                    role = UserRole.CLIENT_VIEWER
                    client_id = None
                
                new_user = {
                    "user_id": user_id,
                    "email": session_data.email,
                    "name": session_data.name,
                    "picture": session_data.picture,
                    "role": role,
                    "client_id": client_id,
                    "is_active": True,
                    "login_count": 1,
                    "last_login_at": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                await db.users.insert_one(new_user)
            
            # Create session
            expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)
            await db.user_sessions.insert_one({
                "user_id": user_id,
                "session_token": session_data.session_token,
                "expires_at": expires_at,
                "created_at": datetime.now(timezone.utc)
            })
            
            # Get client info
            client_name = None
            if client_id:
                client_doc = await db.clients.find_one(
                    {"client_id": client_id},
                    {"_id": 0, "name": 1}
                )
                if client_doc:
                    client_name = client_doc["name"]
            
            # Set httpOnly cookie
            response.set_cookie(
                key="session_token",
                value=session_data.session_token,
                httponly=True,
                secure=True,
                samesite="none",
                path="/",
                max_age=SESSION_EXPIRY_DAYS * 24 * 60 * 60
            )
            
            permissions = UserPermissions.get_permissions(role)
            
            return AuthResponse(
                success=True,
                user=UserResponse(
                    user_id=user_id,
                    email=session_data.email,
                    name=session_data.name,
                    picture=session_data.picture,
                    role=role,
                    permissions=permissions,
                    client_id=client_id,
                    client_name=client_name
                )
            )
            
        except Exception as e:
            logger.error(f"Session processing error: {e}")
            return AuthResponse(success=False, message=str(e))
    
    @auth_router.get("/me", response_model=AuthResponse)
    async def get_current_user_info(request: Request):
        """Get current authenticated user info"""
        user = await get_current_user(request, db)
        
        if not user:
            return AuthResponse(success=False, message="Not authenticated")
        
        client_name = None
        if user.get("client"):
            client_name = user["client"].get("name")
        
        permissions = UserPermissions.get_permissions(user.get("role", UserRole.CLIENT_VIEWER))
        
        return AuthResponse(
            success=True,
            user=UserResponse(
                user_id=user["user_id"],
                email=user["email"],
                name=user["name"],
                picture=user.get("picture"),
                role=user.get("role", UserRole.CLIENT_VIEWER),
                permissions=permissions,
                client_id=user.get("client_id"),
                client_name=client_name
            )
        )
    
    @auth_router.post("/logout")
    async def logout(request: Request, response: Response):
        """Logout user and invalidate session"""
        session_token = request.cookies.get("session_token")
        
        if session_token:
            # Delete session from database
            await db.user_sessions.delete_one({"session_token": session_token})
        
        # Clear cookie
        response.delete_cookie(
            key="session_token",
            path="/",
            secure=True,
            samesite="none"
        )
        
        return {"success": True, "message": "Logged out successfully"}
    
    return auth_router
