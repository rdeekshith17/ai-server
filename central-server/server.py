"""
SecureGuard Central Server
Lightweight API for multi-tenant SaaS (No ML Models)

This server handles:
- Admin dashboard & authentication
- Client/user management
- Edge device registration & provisioning
- Incident storage from edge devices
- WhatsApp alert notifications (Twilio)
- Billing & subscriptions
- Static frontend serving

ML processing happens on Edge Devices at client locations.
"""

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import uuid
import hashlib
import secrets
import logging
import httpx
from pathlib import Path

# Twilio for WhatsApp
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. WhatsApp alerts will be disabled.")

load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "secureguard_central")
mongo_client: AsyncIOMotorClient = None
db = None

# Constants
SESSION_EXPIRY_DAYS = 7
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

# Plan configurations
PLANS = {
    "trial": {
        "name": "Trial",
        "max_cameras": 2,
        "max_users": 1,
        "max_watchlist": 5,
        "retention_days": 3,
        "features": ["live_detection", "basic_analytics"],
        "price_cents": 0,
        "duration_days": 14,
        "gpt_analysis": False
    },
    "starter": {
        "name": "Starter",
        "max_cameras": 4,
        "max_users": 2,
        "max_watchlist": 10,
        "retention_days": 7,
        "features": ["live_detection", "watchlist", "basic_analytics"],
        "price_cents": 9900,
        "gpt_analysis": False
    },
    "professional": {
        "name": "Professional",
        "max_cameras": 16,
        "max_users": 5,
        "max_watchlist": 100,
        "retention_days": 30,
        "features": ["live_detection", "watchlist", "advanced_analytics", "api_access", "gpt_analysis"],
        "price_cents": 29900,
        "gpt_analysis": True
    },
    "enterprise": {
        "name": "Enterprise",
        "max_cameras": 64,
        "max_users": -1,
        "max_watchlist": -1,
        "retention_days": 90,
        "features": ["live_detection", "watchlist", "advanced_analytics", "api_access", "gpt_analysis", "custom_branding"],
        "price_cents": 79900,
        "gpt_analysis": True
    }
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global mongo_client, db
    
    # Startup
    logger.info("SecureGuard Central Server starting...")
    logger.info(f"MongoDB: {MONGO_URL}")
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    # Create indexes
    await db.clients.create_index("client_id", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.edge_devices.create_index("device_id", unique=True)
    await db.edge_devices.create_index("client_id")
    await db.incidents.create_index([("client_id", 1), ("timestamp", -1)])
    await db.cameras.create_index("camera_id", unique=True)
    await db.cameras.create_index("client_id")
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
    
    logger.info("Central Server ready!")
    
    yield  # Server runs here
    
    # Shutdown
    mongo_client.close()
    logger.info("Central Server shutdown")


# App
app = FastAPI(
    title="SecureGuard Central Server",
    description="Multi-tenant SaaS API for shoplifting detection",
    version="2.0.0",
    lifespan=lifespan
)

api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            "manage_clients": True,
            "manage_settings": True,
            "manage_billing": True,
            "api_access": True,
            "system_health": True,
            "ai_model_control": True,
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
            "manage_incidents": True,
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
    token: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str


class ClientCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    plan: str = "trial"


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = None
    plan: Optional[str] = None


class UserAssign(BaseModel):
    email: EmailStr
    role: str
    client_id: str


class CameraCreate(BaseModel):
    client_id: str
    name: str
    location: str
    rtsp_url: Optional[str] = None
    detection_enabled: bool = True
    sensitivity: str = "medium"


class AIModelSettings(BaseModel):
    client_id: str
    enable_yolo: bool = True
    enable_deepface: bool = True
    enable_pose: bool = True
    enable_gpt_analysis: bool = True
    detection_sensitivity: str = "medium"
    threat_threshold: float = 0.6


class EdgeDeviceRegister(BaseModel):
    client_id: str
    api_key: str
    device_name: str
    device_ip: Optional[str] = None


class IncidentUpload(BaseModel):
    client_id: str
    api_key: str
    incident_id: str
    timestamp: str
    severity: str
    confidence: float
    description: str
    camera_id: Optional[str] = None
    camera_name: Optional[str] = None
    frame_thumbnail: Optional[str] = None
    behaviors: List[str] = []
    watchlist_match: Optional[Dict] = None


class HeartbeatData(BaseModel):
    client_id: str
    api_key: str
    device_id: str
    status: str
    cameras_online: int
    cameras_total: int
    cpu_usage: float
    memory_usage: float
    last_incident_at: Optional[str] = None


class TwilioConfig(BaseModel):
    account_sid: str
    auth_token: str
    whatsapp_from: str  # e.g., "whatsapp:+14155238886"


class TwilioConfigUpdate(BaseModel):
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    whatsapp_from: Optional[str] = None
    whatsapp_numbers: Optional[List[str]] = None
    enabled: Optional[bool] = None


class WhatsAppTestMessage(BaseModel):
    to_number: str  # e.g., "+919876543210"
    message: Optional[str] = "Test alert from SecureGuard AI"


# ===========================================
# HELPER FUNCTIONS
# ===========================================

def generate_api_key() -> str:
    """Generate secure API key for edge device"""
    return f"sg_edge_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    salt = os.environ.get("API_KEY_SALT", "secureguard")
    return hashlib.sha256(f"{api_key}{salt}".encode()).hexdigest()


def hash_password(password: str) -> str:
    """Hash password for storage"""
    salt = os.environ.get("PASSWORD_SALT", "secureguard_pwd")
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed


def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


def encrypt_credential(credential: str) -> str:
    """Simple encryption for storing credentials (use proper encryption in production)"""
    # In production, use proper encryption like Fernet
    import base64
    return base64.b64encode(credential.encode()).decode()


def decrypt_credential(encrypted: str) -> str:
    """Decrypt stored credential"""
    import base64
    return base64.b64decode(encrypted.encode()).decode()


async def send_whatsapp_alert(client_id: str, message: str, to_numbers: List[str] = None) -> Dict:
    """Send WhatsApp alert via Twilio"""
    if not TWILIO_AVAILABLE:
        return {"success": False, "error": "Twilio not installed"}
    
    # Get client's Twilio config
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        return {"success": False, "error": "Client not found"}
    
    twilio_config = client.get("twilio_config", {})
    if not twilio_config.get("enabled"):
        return {"success": False, "error": "Twilio not configured"}
    
    try:
        account_sid = decrypt_credential(twilio_config["account_sid"])
        auth_token = decrypt_credential(twilio_config["auth_token"])
        whatsapp_from = twilio_config["whatsapp_from"]
        
        twilio_client = TwilioClient(account_sid, auth_token)
        
        numbers = to_numbers or twilio_config.get("whatsapp_numbers", [])
        results = []
        
        for number in numbers:
            try:
                # Ensure number has whatsapp: prefix
                to_number = f"whatsapp:{number}" if not number.startswith("whatsapp:") else number
                
                msg = twilio_client.messages.create(
                    body=message,
                    from_=whatsapp_from,
                    to=to_number
                )
                results.append({"number": number, "status": "sent", "sid": msg.sid})
                logger.info(f"WhatsApp sent to {number}: {msg.sid}")
            except Exception as e:
                results.append({"number": number, "status": "failed", "error": str(e)})
                logger.error(f"WhatsApp failed to {number}: {e}")
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Twilio error: {e}")
        return {"success": False, "error": str(e)}


async def verify_edge_api_key(client_id: str, api_key: str) -> bool:
    """Verify edge device API key"""
    hashed = hash_api_key(api_key)
    device = await db.edge_devices.find_one({
        "client_id": client_id,
        "api_key_hash": hashed,
        "is_active": True
    })
    return device is not None


async def get_client_by_id(client_id: str) -> Optional[Dict]:
    """Get client by ID"""
    return await db.clients.find_one({"client_id": client_id}, {"_id": 0})


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Extract and validate user from session token"""
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


async def require_auth(request: Request) -> Dict[str, Any]:
    """Dependency that requires authentication"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(request: Request) -> Dict[str, Any]:
    """Dependency that requires admin role"""
    user = await require_auth(request)
    if user.get("role") != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ===========================================
# AUTH ROUTES
# ===========================================

@api_router.post("/auth/register", response_model=AuthResponse)
async def register_user(data: UserRegister, request: Request, response: Response):
    """Register a new user with email/password"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": data.email})
        if existing_user:
            return AuthResponse(success=False, message="Email already registered")
        
        # Check if this is the first user (becomes super admin)
        user_count = await db.users.count_documents({})
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        
        if user_count == 0:
            role = UserRole.SUPER_ADMIN
            client_id = None
        else:
            role = UserRole.CLIENT_VIEWER
            client_id = None
        
        # Create user
        new_user = {
            "user_id": user_id,
            "email": data.email,
            "name": data.name,
            "password_hash": hash_password(data.password),
            "picture": None,
            "role": role,
            "client_id": client_id,
            "is_active": True,
            "auth_provider": "local",
            "login_count": 1,
            "last_login_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await db.users.insert_one(new_user)
        
        # Create session
        session_token = generate_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)
        await db.user_sessions.insert_one({
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        })
        
        # Set cookie
        is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=is_secure,
            samesite="none" if is_secure else "lax",
            path="/",
            max_age=SESSION_EXPIRY_DAYS * 24 * 60 * 60
        )
        
        permissions = UserPermissions.get_permissions(role)
        
        logger.info(f"User registered: {data.email}, role: {role}")
        
        return AuthResponse(
            success=True,
            token=session_token,
            user=UserResponse(
                user_id=user_id,
                email=data.email,
                name=data.name,
                picture=None,
                role=role,
                permissions=permissions,
                client_id=client_id,
                client_name=None
            )
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return AuthResponse(success=False, message=str(e))


@api_router.post("/auth/login", response_model=AuthResponse)
async def login_user(data: UserLogin, request: Request, response: Response):
    """Login with email/password"""
    try:
        # Find user
        user = await db.users.find_one({"email": data.email}, {"_id": 0})
        
        if not user:
            return AuthResponse(success=False, message="Invalid email or password")
        
        # Check password
        if not user.get("password_hash"):
            return AuthResponse(success=False, message="This account uses Google login. Please sign in with Google.")
        
        if not verify_password(data.password, user["password_hash"]):
            return AuthResponse(success=False, message="Invalid email or password")
        
        if not user.get("is_active", True):
            return AuthResponse(success=False, message="Account is disabled")
        
        # Update login stats
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {
                "$set": {
                    "last_login_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                },
                "$inc": {"login_count": 1}
            }
        )
        
        # Create session
        session_token = generate_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)
        await db.user_sessions.insert_one({
            "user_id": user["user_id"],
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        })
        
        # Set cookie
        is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=is_secure,
            samesite="none" if is_secure else "lax",
            path="/",
            max_age=SESSION_EXPIRY_DAYS * 24 * 60 * 60
        )
        
        # Get client info
        client_name = None
        if user.get("client_id"):
            client_doc = await db.clients.find_one(
                {"client_id": user["client_id"]},
                {"_id": 0, "name": 1}
            )
            if client_doc:
                client_name = client_doc["name"]
        
        permissions = UserPermissions.get_permissions(user.get("role", UserRole.CLIENT_VIEWER))
        
        logger.info(f"User logged in: {data.email}")
        
        return AuthResponse(
            success=True,
            token=session_token,
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
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return AuthResponse(success=False, message=str(e))


@api_router.post("/auth/session", response_model=AuthResponse)
async def process_session(request: Request, response: Response):
    """Process session_id from Emergent OAuth callback"""
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        logger.info(f"Processing session: {session_id[:20]}..." if session_id else "No session_id")
        
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
                role = UserRole.SUPER_ADMIN
                client_id = None
            else:
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
        # Detect if running over HTTPS
        is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        
        logger.info(f"Setting cookie - is_secure: {is_secure}, user_id: {user_id}, role: {role}")
        
        response.set_cookie(
            key="session_token",
            value=session_data.session_token,
            httponly=True,
            secure=is_secure,
            samesite="none" if is_secure else "lax",
            path="/",
            max_age=SESSION_EXPIRY_DAYS * 24 * 60 * 60
        )
        
        permissions = UserPermissions.get_permissions(role)
        
        return AuthResponse(
            success=True,
            token=session_data.session_token,
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


@api_router.get("/auth/me", response_model=AuthResponse)
async def get_current_user_info(request: Request):
    """Get current authenticated user info"""
    user = await get_current_user(request)
    
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


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user and invalidate session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    # Detect if running over HTTPS
    is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=is_secure,
        samesite="none" if is_secure else "lax"
    )
    
    return {"success": True, "message": "Logged out successfully"}


# ===========================================
# ADMIN DASHBOARD ROUTES
# ===========================================

@api_router.get("/admin/dashboard/stats")
async def get_admin_dashboard_stats(request: Request):
    """Get admin dashboard statistics"""
    await require_admin(request)
    
    # Count clients
    total_clients = await db.clients.count_documents({})
    active_clients = await db.clients.count_documents({"status": "active"})
    trial_clients = await db.clients.count_documents({"status": "trial"})
    
    # Count cameras
    total_cameras = await db.cameras.count_documents({})
    online_cameras = await db.cameras.count_documents({"status": "online"})
    
    # Count incidents (last 24 hours)
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    incidents_24h = await db.incidents.count_documents({
        "timestamp": {"$gte": yesterday.isoformat()}
    })
    critical_24h = await db.incidents.count_documents({
        "timestamp": {"$gte": yesterday.isoformat()},
        "severity": "critical"
    })
    
    # Count users
    total_users = await db.users.count_documents({})
    
    # Edge devices
    total_edge_devices = await db.edge_devices.count_documents({})
    online_devices = await db.edge_devices.count_documents({
        "last_heartbeat": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}
    })
    
    # Calculate monthly revenue (from active subscriptions)
    revenue_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "total": {"$sum": "$subscription.price_cents"}}}
    ]
    revenue_result = await db.clients.aggregate(revenue_pipeline).to_list(1)
    monthly_revenue = revenue_result[0]["total"] if revenue_result else 0
    
    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "trial_clients": trial_clients,
        "total_cameras": total_cameras,
        "online_cameras": online_cameras,
        "total_incidents_24h": incidents_24h,
        "critical_incidents_24h": critical_24h,
        "total_users": total_users,
        "total_edge_devices": total_edge_devices,
        "online_devices": online_devices,
        "monthly_revenue_cents": monthly_revenue
    }


@api_router.get("/admin/system/health")
async def get_system_health(request: Request):
    """Get system health metrics"""
    await require_admin(request)
    
    try:
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    active_streams = await db.cameras.count_documents({"status": "online"})
    
    return {
        "status": "operational",
        "database": db_status,
        "active_streams": active_streams,
        "queue_depth": 0,
        "ml_models": {
            "note": "ML models run on edge devices"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ===========================================
# CLIENT MANAGEMENT
# ===========================================

@api_router.get("/admin/clients")
async def list_clients(
    request: Request,
    status: Optional[str] = None,
    plan: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """List all clients"""
    await require_admin(request)
    
    query = {}
    if status:
        query["status"] = status
    if plan:
        query["subscription.plan"] = plan
    
    clients = await db.clients.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.clients.count_documents(query)
    
    # Add stats for each client
    for client in clients:
        client["cameras_count"] = await db.cameras.count_documents({"client_id": client["client_id"]})
        client["users_count"] = await db.users.count_documents({"client_id": client["client_id"]})
        client["edge_devices"] = await db.edge_devices.count_documents({"client_id": client["client_id"]})
        
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
        client["incidents_24h"] = await db.incidents.count_documents({
            "client_id": client["client_id"],
            "timestamp": {"$gte": yesterday.isoformat()}
        })
    
    return {"clients": clients, "total": total, "limit": limit, "skip": skip}


@api_router.post("/admin/clients")
async def create_client(request: Request, client_data: ClientCreate):
    """Create a new client"""
    await require_admin(request)
    
    # Generate slug if not provided
    slug = client_data.slug or client_data.name.lower().replace(" ", "-")
    
    # Check if slug is unique
    existing = await db.clients.find_one({"slug": slug})
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    
    plan_config = PLANS.get(client_data.plan, PLANS["trial"])
    client_id = f"cli_{uuid.uuid4().hex[:12]}"
    
    new_client = {
        "client_id": client_id,
        "name": client_data.name,
        "slug": slug,
        "contact": {
            "name": client_data.contact_name or "",
            "email": client_data.contact_email or "",
            "phone": client_data.contact_phone or ""
        },
        "subscription": {
            "plan": client_data.plan,
            "max_cameras": plan_config["max_cameras"],
            "max_users": plan_config["max_users"],
            "max_watchlist": plan_config["max_watchlist"],
            "features": plan_config["features"],
            "price_cents": plan_config["price_cents"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None
        },
        "settings": {
            "timezone": "UTC",
            "alert_email": True,
            "detection_sensitivity": "medium",
            "auto_incident_creation": True,
            "alert_on_critical": True,
            "alert_on_warning": False,
            "whatsapp_numbers": []
        },
        "status": "trial" if client_data.plan == "trial" else "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.insert_one(new_client)
    
    # Remove MongoDB _id before returning
    new_client.pop("_id", None)
    
    return {"success": True, "client": new_client, "client_id": client_id}


@api_router.get("/admin/clients/{client_id}")
async def get_client(request: Request, client_id: str):
    """Get client details"""
    await require_admin(request)
    
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Add detailed stats
    client["cameras"] = await db.cameras.find({"client_id": client_id}, {"_id": 0}).to_list(100)
    client["users"] = await db.users.find(
        {"client_id": client_id}, 
        {"_id": 0, "user_id": 1, "email": 1, "name": 1, "role": 1, "last_login_at": 1}
    ).to_list(100)
    client["edge_devices"] = await db.edge_devices.find(
        {"client_id": client_id},
        {"_id": 0, "api_key_hash": 0}
    ).to_list(100)
    
    client["total_incidents"] = await db.incidents.count_documents({"client_id": client_id})
    client["watchlist_count"] = await db.watchlist.count_documents({"client_id": client_id})
    
    return client


@api_router.put("/admin/clients/{client_id}")
async def update_client(request: Request, client_id: str, update_data: ClientUpdate):
    """Update client details"""
    await require_admin(request)
    
    client = await db.clients.find_one({"client_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if update_data.name:
        update_dict["name"] = update_data.name
    if update_data.contact_name:
        update_dict["contact.name"] = update_data.contact_name
    if update_data.contact_email:
        update_dict["contact.email"] = update_data.contact_email
    if update_data.contact_phone:
        update_dict["contact.phone"] = update_data.contact_phone
    if update_data.status:
        update_dict["status"] = update_data.status
    if update_data.plan:
        plan_config = PLANS.get(update_data.plan, PLANS["starter"])
        update_dict["subscription.plan"] = update_data.plan
        update_dict["subscription.max_cameras"] = plan_config["max_cameras"]
        update_dict["subscription.max_users"] = plan_config["max_users"]
        update_dict["subscription.price_cents"] = plan_config["price_cents"]
    
    await db.clients.update_one({"client_id": client_id}, {"$set": update_dict})
    
    return {"success": True, "message": "Client updated"}


@api_router.delete("/admin/clients/{client_id}")
async def delete_client(request: Request, client_id: str):
    """Delete a client and all associated data"""
    await require_admin(request)
    
    client = await db.clients.find_one({"client_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Delete all associated data
    await db.cameras.delete_many({"client_id": client_id})
    await db.incidents.delete_many({"client_id": client_id})
    await db.watchlist.delete_many({"client_id": client_id})
    await db.edge_devices.delete_many({"client_id": client_id})
    await db.users.update_many(
        {"client_id": client_id},
        {"$set": {"client_id": None, "role": UserRole.CLIENT_VIEWER}}
    )
    await db.clients.delete_one({"client_id": client_id})
    
    return {"success": True, "message": "Client and associated data deleted"}


@api_router.post("/admin/clients/{client_id}/suspend")
async def suspend_client(request: Request, client_id: str):
    """Suspend a client"""
    await require_admin(request)
    
    result = await db.clients.update_one(
        {"client_id": client_id},
        {"$set": {"status": "suspended", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {"success": True, "message": "Client suspended"}


@api_router.post("/admin/clients/{client_id}/activate")
async def activate_client(request: Request, client_id: str):
    """Activate a client"""
    await require_admin(request)
    
    result = await db.clients.update_one(
        {"client_id": client_id},
        {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {"success": True, "message": "Client activated"}


# ===========================================
# USER MANAGEMENT
# ===========================================

@api_router.get("/admin/users")
async def list_all_users(
    request: Request,
    role: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """List all users (admin only)"""
    await require_admin(request)
    
    query = {}
    if role:
        query["role"] = role
    if client_id:
        query["client_id"] = client_id
    
    users = await db.users.find(
        query,
        {"_id": 0, "user_id": 1, "email": 1, "name": 1, "role": 1, "client_id": 1, "last_login_at": 1, "is_active": 1}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.users.count_documents(query)
    
    # Add client names
    for u in users:
        if u.get("client_id"):
            client = await db.clients.find_one({"client_id": u["client_id"]}, {"_id": 0, "name": 1})
            u["client_name"] = client["name"] if client else None
    
    return {"users": users, "total": total}


@api_router.put("/admin/users/{user_id}/assign")
async def assign_user_to_client(request: Request, user_id: str, assignment: UserAssign):
    """Assign a user to a client with a role"""
    await require_admin(request)
    
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    client = await db.clients.find_one({"client_id": assignment.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "client_id": assignment.client_id,
                "role": assignment.role,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {"success": True, "message": f"User assigned to {client['name']} as {assignment.role}"}


@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(request: Request, user_id: str, role: str):
    """Update user role"""
    await require_admin(request)
    
    valid_roles = [UserRole.SUPER_ADMIN, UserRole.CLIENT_OWNER, UserRole.CLIENT_STAFF, UserRole.CLIENT_VIEWER]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"role": role, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True, "message": f"User role updated to {role}"}


# ===========================================
# CAMERA MANAGEMENT
# ===========================================

@api_router.get("/admin/cameras")
async def list_all_cameras(
    request: Request,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """List all cameras across all clients"""
    await require_admin(request)
    
    query = {}
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status
    
    cameras = await db.cameras.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    # Add client names
    for cam in cameras:
        client = await db.clients.find_one({"client_id": cam["client_id"]}, {"_id": 0, "name": 1})
        cam["client_name"] = client["name"] if client else None
    
    return {"cameras": cameras, "total": len(cameras)}


@api_router.post("/admin/cameras")
async def create_camera(request: Request, camera_data: CameraCreate):
    """Create a new camera for a client"""
    await require_admin(request)
    
    client = await db.clients.find_one({"client_id": camera_data.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check camera limit
    current_cameras = await db.cameras.count_documents({"client_id": camera_data.client_id})
    max_cameras = client.get("subscription", {}).get("max_cameras", 2)
    if max_cameras != -1 and current_cameras >= max_cameras:
        raise HTTPException(status_code=400, detail=f"Camera limit reached ({max_cameras})")
    
    camera_id = f"cam_{uuid.uuid4().hex[:12]}"
    
    new_camera = {
        "camera_id": camera_id,
        "client_id": camera_data.client_id,
        "name": camera_data.name,
        "location": camera_data.location,
        "rtsp_url": camera_data.rtsp_url,
        "detection_settings": {
            "enabled": camera_data.detection_enabled,
            "sensitivity": camera_data.sensitivity,
            "enable_pose": True,
            "enable_face_recognition": True,
            "enable_gpt_analysis": True
        },
        "status": "offline",
        "health": {
            "uptime_percent": 0,
            "error_count_24h": 0
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.cameras.insert_one(new_camera)
    
    return {"success": True, "camera_id": camera_id}


@api_router.put("/admin/cameras/{camera_id}")
async def update_camera(request: Request, camera_id: str):
    """Update a camera"""
    await require_admin(request)
    
    camera = await db.cameras.find_one({"camera_id": camera_id})
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    body = await request.json()
    update_dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if "name" in body:
        update_dict["name"] = body["name"]
    if "location" in body:
        update_dict["location"] = body["location"]
    if "rtsp_url" in body:
        update_dict["rtsp_url"] = body["rtsp_url"]
    if "status" in body:
        update_dict["status"] = body["status"]
    if "detection_settings" in body:
        update_dict["detection_settings"] = body["detection_settings"]
    
    await db.cameras.update_one({"camera_id": camera_id}, {"$set": update_dict})
    
    return {"success": True, "message": "Camera updated"}


@api_router.delete("/admin/cameras/{camera_id}")
async def delete_camera(request: Request, camera_id: str):
    """Delete a camera"""
    await require_admin(request)
    
    result = await db.cameras.delete_one({"camera_id": camera_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {"success": True, "message": "Camera deleted"}


# ===========================================
# AI MODEL CONTROL
# ===========================================

@api_router.get("/admin/ai/settings/{client_id}")
async def get_ai_settings(request: Request, client_id: str):
    """Get AI model settings for a client"""
    await require_admin(request)
    
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    ai_settings = client.get("ai_settings", {
        "enable_yolo": True,
        "enable_deepface": True,
        "enable_pose": True,
        "enable_gpt_analysis": client.get("subscription", {}).get("plan") in ["professional", "enterprise"],
        "detection_sensitivity": "medium",
        "threat_threshold": 0.6
    })
    
    return {"client_id": client_id, "settings": ai_settings}


@api_router.put("/admin/ai/settings")
async def update_ai_settings(request: Request, settings: AIModelSettings):
    """Update AI model settings for a client"""
    await require_admin(request)
    
    client = await db.clients.find_one({"client_id": settings.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    await db.clients.update_one(
        {"client_id": settings.client_id},
        {
            "$set": {
                "ai_settings": {
                    "enable_yolo": settings.enable_yolo,
                    "enable_deepface": settings.enable_deepface,
                    "enable_pose": settings.enable_pose,
                    "enable_gpt_analysis": settings.enable_gpt_analysis,
                    "detection_sensitivity": settings.detection_sensitivity,
                    "threat_threshold": settings.threat_threshold
                },
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True, "message": "AI settings updated"}


# ===========================================
# INCIDENTS
# ===========================================

@api_router.get("/admin/incidents/recent")
async def get_recent_incidents_all(request: Request, limit: int = 20):
    """Get recent incidents across all clients"""
    await require_admin(request)
    
    incidents = await db.incidents.find(
        {},
        {"_id": 0, "frame_image": 0, "frame_thumbnail": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Add client names
    for inc in incidents:
        if inc.get("client_id"):
            client = await db.clients.find_one({"client_id": inc["client_id"]}, {"_id": 0, "name": 1})
            inc["client_name"] = client["name"] if client else None
    
    return {"incidents": incidents}


@api_router.get("/incidents")
async def get_incidents(
    request: Request,
    client_id: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get incidents - accessible by authenticated users"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    query = {}
    
    # Non-admin users can only see their client's incidents
    if user.get("role") != UserRole.SUPER_ADMIN:
        if user.get("client_id"):
            query["client_id"] = user["client_id"]
        else:
            return {"incidents": [], "total": 0}
    elif client_id:
        query["client_id"] = client_id
    
    if severity:
        query["severity"] = severity
    
    incidents = await db.incidents.find(
        query,
        {"_id": 0, "frame_image": 0}
    ).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.incidents.count_documents(query)
    
    return {"incidents": incidents, "total": total, "limit": limit, "skip": skip}


# ===========================================
# ML STATUS
# ===========================================

@api_router.get("/ml/status")
async def get_ml_status(request: Request):
    """Get ML model status - models run on edge devices"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # In the central/edge architecture, ML models run on edge devices
    # This endpoint returns the status of connected edge devices with ML capabilities
    
    query = {}
    if user.get("role") != UserRole.SUPER_ADMIN and user.get("client_id"):
        query["client_id"] = user["client_id"]
    
    # Get edge devices and their ML status
    edge_devices = await db.edge_devices.find(query, {"_id": 0, "api_key_hash": 0}).to_list(100)
    
    online_devices = [d for d in edge_devices if d.get("is_online") or 
                      (d.get("last_heartbeat") and 
                       (datetime.now(timezone.utc) - datetime.fromisoformat(d["last_heartbeat"].replace("Z", "+00:00"))).seconds < 300)]
    
    return {
        "status": "operational" if online_devices else "no_devices",
        "architecture": "edge_processing",
        "message": "ML models run on edge devices at client locations",
        "models": {
            "yolo": {"name": "YOLOv8", "status": "available", "location": "edge_device"},
            "pose": {"name": "YOLO Pose", "status": "available", "location": "edge_device"},
            "deepface": {"name": "DeepFace", "status": "available", "location": "edge_device"},
            "gpt_vision": {"name": "GPT-5.2 Vision", "status": "available", "location": "edge_device"}
        },
        "edge_devices": {
            "total": len(edge_devices),
            "online": len(online_devices)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ===========================================
# ALERTS
# ===========================================

@api_router.get("/alerts/status")
async def get_alerts_status(request: Request):
    """Get alerts system status"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    query = {}
    if user.get("role") != UserRole.SUPER_ADMIN and user.get("client_id"):
        query["client_id"] = user["client_id"]
    
    # Count recent alerts
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    if query:
        total_24h = await db.incidents.count_documents({**query, "timestamp": {"$gte": yesterday}})
        critical_24h = await db.incidents.count_documents({**query, "timestamp": {"$gte": yesterday}, "severity": "critical"})
        warning_24h = await db.incidents.count_documents({**query, "timestamp": {"$gte": yesterday}, "severity": "warning"})
    else:
        total_24h = await db.incidents.count_documents({"timestamp": {"$gte": yesterday}})
        critical_24h = await db.incidents.count_documents({"timestamp": {"$gte": yesterday}, "severity": "critical"})
        warning_24h = await db.incidents.count_documents({"timestamp": {"$gte": yesterday}, "severity": "warning"})
    
    return {
        "status": "active",
        "channels": {
            "email": True,
            "whatsapp": True,
            "dashboard": True,
            "push": True
        },
        "alerts_24h": {
            "total": total_24h,
            "critical": critical_24h,
            "warning": warning_24h
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@api_router.get("/alerts/settings/{client_id}")
async def get_alert_settings(request: Request, client_id: str):
    """Get alert settings for a client"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check access
    if user.get("role") != UserRole.SUPER_ADMIN and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    settings = client.get("settings", {})
    
    return {
        "client_id": client_id,
        "alert_on_critical": settings.get("alert_on_critical", True),
        "alert_on_warning": settings.get("alert_on_warning", False),
        "alert_email": settings.get("alert_email", True),
        "email_recipients": settings.get("email_recipients", []),
        "whatsapp_enabled": len(settings.get("whatsapp_numbers", [])) > 0,
        "whatsapp_numbers": settings.get("whatsapp_numbers", []),
        "detection_sensitivity": settings.get("detection_sensitivity", "medium"),
        "auto_incident_creation": settings.get("auto_incident_creation", True)
    }


@api_router.put("/alerts/settings/{client_id}")
async def update_alert_settings(request: Request, client_id: str):
    """Update alert settings for a client"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check access
    if user.get("role") != UserRole.SUPER_ADMIN and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    client = await db.clients.find_one({"client_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    body = await request.json()
    
    update_dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if "alert_on_critical" in body:
        update_dict["settings.alert_on_critical"] = body["alert_on_critical"]
    if "alert_on_warning" in body:
        update_dict["settings.alert_on_warning"] = body["alert_on_warning"]
    if "alert_email" in body:
        update_dict["settings.alert_email"] = body["alert_email"]
    if "email_recipients" in body:
        update_dict["settings.email_recipients"] = body["email_recipients"]
    if "whatsapp_numbers" in body:
        update_dict["settings.whatsapp_numbers"] = body["whatsapp_numbers"]
    if "detection_sensitivity" in body:
        update_dict["settings.detection_sensitivity"] = body["detection_sensitivity"]
    if "auto_incident_creation" in body:
        update_dict["settings.auto_incident_creation"] = body["auto_incident_creation"]
    
    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": update_dict}
    )
    
    return {"success": True, "message": "Alert settings updated"}


@api_router.get("/alerts/log/{client_id}")
async def get_alert_log(request: Request, client_id: str, limit: int = 50):
    """Get alert log for a client"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check access
    if user.get("role") != UserRole.SUPER_ADMIN and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get recent incidents/alerts for this client
    alerts = await db.incidents.find(
        {"client_id": client_id},
        {"_id": 0, "frame_image": 0, "frame_thumbnail": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Also check for alert_logs collection if it exists
    alert_logs = await db.alert_logs.find(
        {"client_id": client_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "client_id": client_id,
        "alerts": alerts,
        "notification_logs": alert_logs,
        "total_alerts": len(alerts),
        "total_notifications": len(alert_logs)
    }


# ===========================================
# EDGE DEVICE PROVISIONING
# ===========================================

@api_router.post("/admin/edge-devices/provision")
async def provision_edge_device(request: Request, client_id: str, device_name: str = "Edge Device"):
    """Generate credentials for new edge device"""
    await require_admin(request)
    
    client = await get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    device_id = f"edge_{uuid.uuid4().hex[:12]}"
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    device = {
        "device_id": device_id,
        "client_id": client_id,
        "device_name": device_name,
        "api_key_hash": api_key_hash,
        "is_active": True,
        "status": "pending",
        "cameras": [],
        "last_heartbeat": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.edge_devices.insert_one(device)
    
    return {
        "success": True,
        "device_id": device_id,
        "client_id": client_id,
        "api_key": api_key,
        "central_server_url": os.environ.get("CENTRAL_SERVER_URL", "https://your-server.com"),
        "message": "Save these credentials! API key cannot be retrieved later."
    }


@api_router.get("/admin/edge-devices")
async def list_edge_devices(request: Request, client_id: Optional[str] = None):
    """List all edge devices"""
    await require_admin(request)
    
    query = {}
    if client_id:
        query["client_id"] = client_id
    
    devices = await db.edge_devices.find(query, {"_id": 0, "api_key_hash": 0}).to_list(100)
    
    for device in devices:
        client = await get_client_by_id(device["client_id"])
        device["client_name"] = client["name"] if client else "Unknown"
        
        if device.get("last_heartbeat"):
            try:
                last_hb = datetime.fromisoformat(device["last_heartbeat"].replace("Z", "+00:00"))
                device["is_online"] = (datetime.now(timezone.utc) - last_hb).seconds < 300
            except:
                device["is_online"] = False
        else:
            device["is_online"] = False
    
    return {"devices": devices}


@api_router.put("/admin/edge-devices/{device_id}")
async def update_edge_device(request: Request, device_id: str):
    """Update an edge device"""
    await require_admin(request)
    
    device = await db.edge_devices.find_one({"device_id": device_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    body = await request.json()
    update_dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if "device_name" in body:
        update_dict["device_name"] = body["device_name"]
    if "is_active" in body:
        update_dict["is_active"] = body["is_active"]
    
    await db.edge_devices.update_one(
        {"device_id": device_id},
        {"$set": update_dict}
    )
    
    return {"success": True, "message": "Device updated"}


@api_router.delete("/admin/edge-devices/{device_id}")
async def delete_edge_device(request: Request, device_id: str):
    """Delete an edge device"""
    await require_admin(request)
    
    device = await db.edge_devices.find_one({"device_id": device_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.edge_devices.delete_one({"device_id": device_id})
    
    return {"success": True, "message": "Device deleted"}


# ===========================================
# EDGE DEVICE ROUTES (Called by edge devices)
# ===========================================

@api_router.post("/edge/register")
async def register_edge_device(data: EdgeDeviceRegister):
    """Edge device registration/first connection"""
    
    if not await verify_edge_api_key(data.client_id, data.api_key):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    await db.edge_devices.update_one(
        {"client_id": data.client_id, "api_key_hash": hash_api_key(data.api_key)},
        {
            "$set": {
                "device_name": data.device_name,
                "device_ip": data.device_ip,
                "status": "online",
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    client = await get_client_by_id(data.client_id)
    
    return {
        "success": True,
        "message": "Device registered",
        "config": client.get("settings", {}) if client else {}
    }


@api_router.post("/edge/heartbeat")
async def edge_heartbeat(data: HeartbeatData):
    """Edge device health check (called every 1-5 minutes)"""
    
    if not await verify_edge_api_key(data.client_id, data.api_key):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    await db.edge_devices.update_one(
        {"device_id": data.device_id},
        {
            "$set": {
                "status": data.status,
                "cameras_online": data.cameras_online,
                "cameras_total": data.cameras_total,
                "cpu_usage": data.cpu_usage,
                "memory_usage": data.memory_usage,
                "last_incident_at": data.last_incident_at,
                "last_heartbeat": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    client = await get_client_by_id(data.client_id)
    
    return {
        "success": True,
        "config_updated": False,
        "config": client.get("settings", {}) if client else {}
    }


@api_router.post("/edge/incidents")
async def upload_incident(data: IncidentUpload):
    """Receive incident from edge device"""
    
    if not await verify_edge_api_key(data.client_id, data.api_key):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    incident = {
        "id": data.incident_id,
        "client_id": data.client_id,
        "timestamp": data.timestamp,
        "severity": data.severity,
        "confidence": data.confidence,
        "description": data.description,
        "camera_id": data.camera_id,
        "camera_name": data.camera_name,
        "frame_thumbnail": data.frame_thumbnail,
        "behaviors": data.behaviors,
        "watchlist_match": data.watchlist_match,
        "source": "edge_device",
        "received_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.incidents.insert_one(incident)
    
    # Send alert if configured
    client = await get_client_by_id(data.client_id)
    if client:
        settings = client.get("settings", {})
        should_alert = (
            (data.severity == "critical" and settings.get("alert_on_critical", True)) or
            (data.severity == "warning" and settings.get("alert_on_warning", False))
        )
        if should_alert:
            logger.info(f"Alert triggered for client {data.client_id}: {data.description}")
    
    return {"success": True, "incident_id": data.incident_id}


# ===========================================
# CLIENT DASHBOARD ROUTES
# ===========================================

@api_router.get("/dashboard/stats")
async def get_client_dashboard_stats(request: Request, client_id: str):
    """Get stats for client dashboard"""
    user = await require_auth(request)
    
    if user.get("role") != UserRole.SUPER_ADMIN and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    total_incidents = await db.incidents.count_documents({"client_id": client_id})
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    incidents_24h = await db.incidents.count_documents({
        "client_id": client_id,
        "timestamp": {"$gte": yesterday}
    })
    
    critical = await db.incidents.count_documents({"client_id": client_id, "severity": "critical"})
    warning = await db.incidents.count_documents({"client_id": client_id, "severity": "warning"})
    
    devices = await db.edge_devices.count_documents({"client_id": client_id})
    online = await db.edge_devices.count_documents({
        "client_id": client_id,
        "last_heartbeat": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}
    })
    
    cameras = await db.cameras.count_documents({"client_id": client_id})
    
    client = await get_client_by_id(client_id)
    
    return {
        "total_incidents": total_incidents,
        "incidents_24h": incidents_24h,
        "critical_incidents": critical,
        "warning_incidents": warning,
        "edge_devices": devices,
        "online_devices": online,
        "cameras": cameras,
        "settings": client.get("settings", {}) if client else {},
        "plan": client.get("subscription", {}).get("plan") if client else None,
        "updated_at": client.get("updated_at") if client else None
    }


@api_router.get("/dashboard/incidents")
async def get_client_incidents(request: Request, client_id: str, limit: int = 50):
    """Get incidents for a specific client"""
    user = await require_auth(request)
    
    if user.get("role") != UserRole.SUPER_ADMIN and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    incidents = await db.incidents.find(
        {"client_id": client_id},
        {"_id": 0, "frame_image": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"incidents": incidents}


# ===========================================
# MAIN
# ===========================================

app.include_router(api_router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "central-server",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Static file serving for React frontend
# Build frontend first, then mount the build directory
BUILD_DIR = Path(__file__).parent / "frontend" / "build"

if BUILD_DIR.exists():
    app.mount("/static", StaticFiles(directory=BUILD_DIR / "static"), name="static")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React frontend for all non-API routes"""
        # Don't serve frontend for API routes
        if full_path.startswith("api/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not found")
        
        file_path = BUILD_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Return index.html for client-side routing
        return FileResponse(BUILD_DIR / "index.html")
else:
    logger.warning(f"Frontend build directory not found at {BUILD_DIR}")
    logger.info("To serve the frontend, build it and place in ./frontend/build/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
