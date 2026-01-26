"""
Authentication Service for Multi-Tenant Platform
"""
import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings
JWT_SECRET = os.environ.get("JWT_SECRET", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security
security = HTTPBearer(auto_error=False)


class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self, db):
        self.db = db
    
    # ===========================================
    # PASSWORD HASHING
    # ===========================================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storing"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    # ===========================================
    # API KEY MANAGEMENT
    # ===========================================
    
    @staticmethod
    def generate_api_key() -> Tuple[str, str]:
        """Generate a new API key and its hash"""
        # Format: sg_live_xxxxxxxxxxxxxxxxxxxx
        raw_key = f"sg_live_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, key_hash
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for comparison"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    # ===========================================
    # JWT TOKEN MANAGEMENT
    # ===========================================
    
    @staticmethod
    def create_access_token(
        user_id: str,
        client_id: str,
        role: str,
        permissions: list,
        is_admin: bool = False
    ) -> str:
        """Create a JWT access token"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "client_id": client_id,
            "role": role,
            "permissions": permissions,
            "is_admin": is_admin,
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": expire
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str, client_id: str) -> str:
        """Create a JWT refresh token"""
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "client_id": client_id,
            "type": "refresh",
            "iat": datetime.now(timezone.utc),
            "exp": expire
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
    # ===========================================
    # USER AUTHENTICATION
    # ===========================================
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user by email and password"""
        user = await self.db.users.find_one(
            {"email": email.lower(), "is_active": True},
            {"_id": 0}
        )
        
        if not user:
            return None
        
        if not self.verify_password(password, user["password_hash"]):
            return None
        
        # Update last login
        await self.db.users.update_one(
            {"user_id": user["user_id"]},
            {
                "$set": {"last_login_at": datetime.now(timezone.utc).isoformat()},
                "$inc": {"login_count": 1}
            }
        )
        
        return user
    
    async def authenticate_api_key(self, api_key: str) -> Optional[Dict]:
        """Authenticate using API key"""
        key_hash = self.hash_api_key(api_key)
        
        # Find client with this API key
        client = await self.db.clients.find_one(
            {
                "api_keys": {
                    "$elemMatch": {
                        "key_hash": key_hash,
                        "is_active": True
                    }
                },
                "status": "active"
            },
            {"_id": 0}
        )
        
        if not client:
            return None
        
        # Find the specific key to get permissions
        api_key_info = None
        for key in client.get("api_keys", []):
            if key["key_hash"] == key_hash:
                api_key_info = key
                break
        
        if not api_key_info:
            return None
        
        # Update last used timestamp
        await self.db.clients.update_one(
            {"client_id": client["client_id"], "api_keys.key_hash": key_hash},
            {"$set": {"api_keys.$.last_used_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {
            "client_id": client["client_id"],
            "client_name": client["name"],
            "key_id": api_key_info["key_id"],
            "permissions": api_key_info.get("permissions", ["read"]),
            "is_api_key": True
        }
    
    # ===========================================
    # TOKEN GENERATION
    # ===========================================
    
    async def login(self, email: str, password: str) -> Dict:
        """Login and return tokens"""
        user = await self.authenticate_user(email, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Get client info
        client = await self.db.clients.find_one(
            {"client_id": user["client_id"]},
            {"_id": 0, "api_keys": 0}
        )
        
        if not client:
            raise HTTPException(status_code=401, detail="Client not found")
        
        if client["status"] not in ["active", "trial"]:
            raise HTTPException(status_code=403, detail=f"Account is {client['status']}")
        
        # Get permissions list
        permissions = []
        user_permissions = user.get("permissions", {})
        for perm, enabled in user_permissions.items():
            if enabled:
                permissions.append(perm)
        
        # Check if super admin
        is_admin = user.get("role") == "super_admin"
        
        # Create tokens
        access_token = self.create_access_token(
            user_id=user["user_id"],
            client_id=user["client_id"],
            role=user["role"],
            permissions=permissions,
            is_admin=is_admin
        )
        
        refresh_token = self.create_refresh_token(
            user_id=user["user_id"],
            client_id=user["client_id"]
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "permissions": permissions
            },
            "client": {
                "client_id": client["client_id"],
                "name": client["name"],
                "plan": client["subscription"]["plan"],
                "status": client["status"]
            }
        }
    
    async def refresh_tokens(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        payload = self.decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user = await self.db.users.find_one(
            {"user_id": payload["sub"], "is_active": True},
            {"_id": 0}
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Get permissions list
        permissions = []
        user_permissions = user.get("permissions", {})
        for perm, enabled in user_permissions.items():
            if enabled:
                permissions.append(perm)
        
        is_admin = user.get("role") == "super_admin"
        
        access_token = self.create_access_token(
            user_id=user["user_id"],
            client_id=user["client_id"],
            role=user["role"],
            permissions=permissions,
            is_admin=is_admin
        )
        
        new_refresh_token = self.create_refresh_token(
            user_id=user["user_id"],
            client_id=user["client_id"]
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }


# ===========================================
# DEPENDENCY INJECTION
# ===========================================

class CurrentUser:
    """Current authenticated user context"""
    def __init__(
        self,
        user_id: str,
        client_id: str,
        role: str,
        permissions: list,
        is_admin: bool = False,
        is_api_key: bool = False
    ):
        self.user_id = user_id
        self.client_id = client_id
        self.role = role
        self.permissions = permissions
        self.is_admin = is_admin
        self.is_api_key = is_api_key
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        if self.is_admin:
            return True
        return permission in self.permissions
    
    def require_permission(self, permission: str):
        """Raise exception if user doesn't have permission"""
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission} required"
            )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> CurrentUser:
    """
    Dependency to get current authenticated user from JWT or API key.
    Inject into route handlers with: current_user: CurrentUser = Depends(get_current_user)
    """
    from server import db  # Import here to avoid circular imports
    
    # Try API key first
    if x_api_key:
        auth_service = AuthService(db)
        api_auth = await auth_service.authenticate_api_key(x_api_key)
        if api_auth:
            return CurrentUser(
                user_id=api_auth["key_id"],
                client_id=api_auth["client_id"],
                role="api_only",
                permissions=api_auth["permissions"],
                is_admin=False,
                is_api_key=True
            )
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Try JWT
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = credentials.credentials
    payload = AuthService.decode_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    return CurrentUser(
        user_id=payload["sub"],
        client_id=payload["client_id"],
        role=payload["role"],
        permissions=payload.get("permissions", []),
        is_admin=payload.get("is_admin", False),
        is_api_key=False
    )


async def get_admin_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency to ensure user is a platform admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_permission(permission: str):
    """Decorator-style dependency to require a specific permission"""
    async def check_permission(current_user: CurrentUser = Depends(get_current_user)):
        current_user.require_permission(permission)
        return current_user
    return check_permission
