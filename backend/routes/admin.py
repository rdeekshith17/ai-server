"""
Admin Routes for SecureGuard Multi-Tenant Platform
Handles client management, user management, system monitoring
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid
import logging

from .auth import require_admin, UserRole, UserPermissions, check_permission

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# ===========================================
# MODELS
# ===========================================

class ClientCreate(BaseModel):
    name: str
    slug: str
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    plan: str = "trial"  # trial, basic, professional, enterprise


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = None  # active, suspended, trial, cancelled
    plan: Optional[str] = None


class UserAssign(BaseModel):
    email: EmailStr
    role: str  # client_owner, client_staff, client_viewer
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


# ===========================================
# PLAN CONFIGURATIONS
# ===========================================

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
    "basic": {
        "name": "Basic",
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


# ===========================================
# ADMIN ROUTES
# ===========================================

def create_admin_routes(db: AsyncIOMotorDatabase) -> APIRouter:
    """Create admin router with database dependency"""
    
    # ===========================================
    # DASHBOARD & STATS
    # ===========================================
    
    @admin_router.get("/dashboard/stats")
    async def get_admin_dashboard_stats(request: Request):
        """Get admin dashboard statistics"""
        user = await require_admin(request, db)
        
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
            "monthly_revenue_cents": monthly_revenue
        }
    
    @admin_router.get("/system/health")
    async def get_system_health(request: Request):
        """Get system health metrics"""
        user = await require_admin(request, db)
        
        # Check database connection
        try:
            await db.command("ping")
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Get active streams count
        active_streams = await db.cameras.count_documents({"status": "online"})
        
        # Get processing queue depth (placeholder for actual queue)
        queue_depth = 0
        
        return {
            "status": "operational",
            "database": db_status,
            "active_streams": active_streams,
            "queue_depth": queue_depth,
            "ml_models": {
                "yolo": "active",
                "deepface": "active",
                "pose": "active",
                "gpt_vision": "active"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # ===========================================
    # CLIENT MANAGEMENT
    # ===========================================
    
    @admin_router.get("/clients")
    async def list_clients(
        request: Request,
        status: Optional[str] = None,
        plan: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        """List all clients"""
        user = await require_admin(request, db)
        
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
            
            # Last 24h incidents
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
            client["incidents_24h"] = await db.incidents.count_documents({
                "client_id": client["client_id"],
                "timestamp": {"$gte": yesterday.isoformat()}
            })
        
        return {"clients": clients, "total": total, "limit": limit, "skip": skip}
    
    @admin_router.post("/clients")
    async def create_client(request: Request, client_data: ClientCreate):
        """Create a new client"""
        user = await require_admin(request, db)
        
        # Check if slug is unique
        existing = await db.clients.find_one({"slug": client_data.slug})
        if existing:
            raise HTTPException(status_code=400, detail="Client slug already exists")
        
        plan_config = PLANS.get(client_data.plan, PLANS["trial"])
        client_id = f"cli_{uuid.uuid4().hex[:12]}"
        
        new_client = {
            "client_id": client_id,
            "name": client_data.name,
            "slug": client_data.slug,
            "contact": {
                "name": client_data.contact_name,
                "email": client_data.contact_email,
                "phone": client_data.contact_phone
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
                "auto_incident_creation": True
            },
            "status": "trial" if client_data.plan == "trial" else "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.clients.insert_one(new_client)
        
        # Remove MongoDB _id before returning
        del new_client["_id"] if "_id" in new_client else None
        
        return {"success": True, "client": new_client}
    
    @admin_router.get("/clients/{client_id}")
    async def get_client(request: Request, client_id: str):
        """Get client details"""
        user = await require_admin(request, db)
        
        client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Add detailed stats
        client["cameras"] = await db.cameras.find({"client_id": client_id}, {"_id": 0}).to_list(100)
        client["users"] = await db.users.find(
            {"client_id": client_id}, 
            {"_id": 0, "user_id": 1, "email": 1, "name": 1, "role": 1, "last_login_at": 1}
        ).to_list(100)
        
        # Incident stats
        client["total_incidents"] = await db.incidents.count_documents({"client_id": client_id})
        client["watchlist_count"] = await db.watchlist.count_documents({"client_id": client_id})
        
        return client
    
    @admin_router.put("/clients/{client_id}")
    async def update_client(request: Request, client_id: str, update_data: ClientUpdate):
        """Update client details"""
        user = await require_admin(request, db)
        
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
            plan_config = PLANS.get(update_data.plan, PLANS["basic"])
            update_dict["subscription.plan"] = update_data.plan
            update_dict["subscription.max_cameras"] = plan_config["max_cameras"]
            update_dict["subscription.max_users"] = plan_config["max_users"]
            update_dict["subscription.price_cents"] = plan_config["price_cents"]
        
        await db.clients.update_one({"client_id": client_id}, {"$set": update_dict})
        
        return {"success": True, "message": "Client updated"}
    
    @admin_router.delete("/clients/{client_id}")
    async def delete_client(request: Request, client_id: str):
        """Delete a client and all associated data"""
        user = await require_admin(request, db)
        
        client = await db.clients.find_one({"client_id": client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Delete all associated data
        await db.cameras.delete_many({"client_id": client_id})
        await db.incidents.delete_many({"client_id": client_id})
        await db.watchlist.delete_many({"client_id": client_id})
        await db.users.update_many(
            {"client_id": client_id},
            {"$set": {"client_id": None, "role": UserRole.CLIENT_VIEWER}}
        )
        await db.clients.delete_one({"client_id": client_id})
        
        return {"success": True, "message": "Client and associated data deleted"}
    
    @admin_router.post("/clients/{client_id}/suspend")
    async def suspend_client(request: Request, client_id: str):
        """Suspend a client"""
        user = await require_admin(request, db)
        
        result = await db.clients.update_one(
            {"client_id": client_id},
            {"$set": {"status": "suspended", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Client not found")
        
        return {"success": True, "message": "Client suspended"}
    
    @admin_router.post("/clients/{client_id}/activate")
    async def activate_client(request: Request, client_id: str):
        """Activate a client"""
        user = await require_admin(request, db)
        
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
    
    @admin_router.get("/users")
    async def list_all_users(
        request: Request,
        role: Optional[str] = None,
        client_id: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        """List all users (admin only)"""
        user = await require_admin(request, db)
        
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
    
    @admin_router.put("/users/{user_id}/assign")
    async def assign_user_to_client(request: Request, user_id: str, assignment: UserAssign):
        """Assign a user to a client with a role"""
        admin = await require_admin(request, db)
        
        # Verify user exists
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify client exists
        client = await db.clients.find_one({"client_id": assignment.client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Update user
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
    
    @admin_router.put("/users/{user_id}/role")
    async def update_user_role(request: Request, user_id: str, role: str):
        """Update user role"""
        admin = await require_admin(request, db)
        
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
    
    @admin_router.get("/cameras")
    async def list_all_cameras(
        request: Request,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ):
        """List all cameras across all clients"""
        user = await require_admin(request, db)
        
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
    
    @admin_router.post("/cameras")
    async def create_camera(request: Request, camera_data: CameraCreate):
        """Create a new camera for a client"""
        user = await require_admin(request, db)
        
        # Verify client exists
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
    
    # ===========================================
    # AI MODEL CONTROL
    # ===========================================
    
    @admin_router.get("/ai/settings/{client_id}")
    async def get_ai_settings(request: Request, client_id: str):
        """Get AI model settings for a client"""
        user = await require_admin(request, db)
        
        client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get client's AI settings or return defaults
        ai_settings = client.get("ai_settings", {
            "enable_yolo": True,
            "enable_deepface": True,
            "enable_pose": True,
            "enable_gpt_analysis": client.get("subscription", {}).get("plan") in ["professional", "enterprise"],
            "detection_sensitivity": "medium",
            "threat_threshold": 0.6
        })
        
        return {"client_id": client_id, "settings": ai_settings}
    
    @admin_router.put("/ai/settings")
    async def update_ai_settings(request: Request, settings: AIModelSettings):
        """Update AI model settings for a client"""
        user = await require_admin(request, db)
        
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
    # RECENT ACTIVITY
    # ===========================================
    
    @admin_router.get("/incidents/recent")
    async def get_recent_incidents_all(request: Request, limit: int = 20):
        """Get recent incidents across all clients"""
        user = await require_admin(request, db)
        
        incidents = await db.incidents.find(
            {},
            {"_id": 0, "frame_image": 0}  # Exclude large data
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Add client names
        for inc in incidents:
            if inc.get("client_id"):
                client = await db.clients.find_one({"client_id": inc["client_id"]}, {"_id": 0, "name": 1})
                inc["client_name"] = client["name"] if client else None
        
        return {"incidents": incidents}
    
    return admin_router
