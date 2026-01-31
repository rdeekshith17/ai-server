"""
SecureGuard Central Server
Lightweight API for multi-tenant SaaS (No ML Models)

This server handles:
- Admin dashboard & authentication
- Client/user management
- Edge device registration & provisioning
- Incident storage from edge devices
- WhatsApp alert notifications
- Billing & subscriptions

ML processing happens on Edge Devices at client locations.
"""

from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os
import uuid
import hashlib
import secrets
import logging

load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "secureguard_central")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# App
app = FastAPI(
    title="SecureGuard Central Server",
    description="Multi-tenant SaaS API for shoplifting detection",
    version="2.0.0"
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

class ClientCreate(BaseModel):
    name: str
    contact_email: EmailStr
    plan: str = "starter"


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
    frame_thumbnail: Optional[str] = None  # Base64 thumbnail (small)
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


# ===========================================
# ADMIN ROUTES
# ===========================================

@api_router.get("/admin/dashboard/stats")
async def get_admin_stats():
    """Get platform-wide statistics"""
    total_clients = await db.clients.count_documents({})
    active_clients = await db.clients.count_documents({"status": "active"})
    total_edge_devices = await db.edge_devices.count_documents({})
    online_devices = await db.edge_devices.count_documents({
        "last_heartbeat": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}
    })
    
    # Incidents last 24h
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    incidents_24h = await db.incidents.count_documents({"timestamp": {"$gte": yesterday}})
    critical_24h = await db.incidents.count_documents({
        "timestamp": {"$gte": yesterday},
        "severity": "critical"
    })
    
    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "total_edge_devices": total_edge_devices,
        "online_devices": online_devices,
        "incidents_24h": incidents_24h,
        "critical_24h": critical_24h
    }


@api_router.get("/admin/clients")
async def list_clients(limit: int = 50, skip: int = 0):
    """List all clients"""
    clients = await db.clients.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Add edge device count for each client
    for client in clients:
        client["edge_devices"] = await db.edge_devices.count_documents({"client_id": client["client_id"]})
        client["incidents_24h"] = await db.incidents.count_documents({
            "client_id": client["client_id"],
            "timestamp": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}
        })
    
    return {"clients": clients, "total": await db.clients.count_documents({})}


@api_router.post("/admin/clients")
async def create_client(data: ClientCreate):
    """Create new client"""
    client_id = f"cli_{uuid.uuid4().hex[:12]}"
    
    client = {
        "client_id": client_id,
        "name": data.name,
        "contact_email": data.contact_email,
        "plan": data.plan,
        "status": "active",
        "settings": {
            "alert_on_critical": True,
            "alert_on_warning": False,
            "detection_sensitivity": "medium",
            "whatsapp_numbers": []
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.insert_one(client)
    
    return {"success": True, "client_id": client_id, "client": client}


@api_router.post("/admin/edge-devices/provision")
async def provision_edge_device(client_id: str, device_name: str = "Edge Device"):
    """Generate credentials for new edge device"""
    
    # Verify client exists
    client = await get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Generate credentials
    device_id = f"edge_{uuid.uuid4().hex[:12]}"
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    device = {
        "device_id": device_id,
        "client_id": client_id,
        "device_name": device_name,
        "api_key_hash": api_key_hash,
        "is_active": True,
        "status": "pending",  # Will be "online" after first heartbeat
        "cameras": [],
        "last_heartbeat": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.edge_devices.insert_one(device)
    
    # Return credentials (API key only shown once!)
    return {
        "success": True,
        "device_id": device_id,
        "client_id": client_id,
        "api_key": api_key,  # IMPORTANT: Only shown once!
        "central_server_url": os.environ.get("CENTRAL_SERVER_URL", "https://api.yourdomain.com"),
        "message": "Save these credentials! API key cannot be retrieved later."
    }


@api_router.get("/admin/edge-devices")
async def list_edge_devices(client_id: Optional[str] = None):
    """List all edge devices"""
    query = {}
    if client_id:
        query["client_id"] = client_id
    
    devices = await db.edge_devices.find(query, {"_id": 0, "api_key_hash": 0}).to_list(100)
    
    # Add client names
    for device in devices:
        client = await get_client_by_id(device["client_id"])
        device["client_name"] = client["name"] if client else "Unknown"
        
        # Check if online (heartbeat in last 5 min)
        if device.get("last_heartbeat"):
            last_hb = datetime.fromisoformat(device["last_heartbeat"].replace("Z", "+00:00"))
            device["is_online"] = (datetime.now(timezone.utc) - last_hb).seconds < 300
        else:
            device["is_online"] = False
    
    return {"devices": devices}


# ===========================================
# EDGE DEVICE ROUTES (Called by edge devices)
# ===========================================

@api_router.post("/edge/register")
async def register_edge_device(data: EdgeDeviceRegister):
    """Edge device registration/first connection"""
    
    if not await verify_edge_api_key(data.client_id, data.api_key):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update device info
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
    
    # Get client config to send back
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
    
    # Update heartbeat
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
    
    # Return any pending config updates
    client = await get_client_by_id(data.client_id)
    
    return {
        "success": True,
        "config_updated": False,  # Set True if config changed
        "config": client.get("settings", {}) if client else {}
    }


@api_router.post("/edge/incidents")
async def upload_incident(data: IncidentUpload):
    """Receive incident from edge device"""
    
    if not await verify_edge_api_key(data.client_id, data.api_key):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Store incident
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
        
        if should_alert and settings.get("whatsapp_numbers"):
            # TODO: Send WhatsApp alert
            logger.info(f"Would send alert for incident {data.incident_id}")
    
    return {"success": True, "incident_id": data.incident_id}


@api_router.get("/edge/config/{client_id}")
async def get_edge_config(client_id: str, api_key: str):
    """Get latest config for edge device"""
    
    if not await verify_edge_api_key(client_id, api_key):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    client = await get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get watchlist for this client
    watchlist = await db.watchlist.find(
        {"client_id": client_id},
        {"_id": 0, "photo_encoding": 1, "name": 1, "threat_level": 1}
    ).to_list(100)
    
    return {
        "settings": client.get("settings", {}),
        "watchlist": watchlist,
        "updated_at": client.get("updated_at")
    }


# ===========================================
# CLIENT DASHBOARD ROUTES
# ===========================================

@api_router.get("/dashboard/stats")
async def get_client_dashboard_stats(client_id: str):
    """Get stats for client dashboard"""
    
    # Count incidents
    total_incidents = await db.incidents.count_documents({"client_id": client_id})
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    incidents_24h = await db.incidents.count_documents({
        "client_id": client_id,
        "timestamp": {"$gte": yesterday}
    })
    
    critical = await db.incidents.count_documents({"client_id": client_id, "severity": "critical"})
    warning = await db.incidents.count_documents({"client_id": client_id, "severity": "warning"})
    
    # Edge devices
    devices = await db.edge_devices.count_documents({"client_id": client_id})
    online = await db.edge_devices.count_documents({
        "client_id": client_id,
        "last_heartbeat": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}
    })
    
    return {
        "total_incidents": total_incidents,
        "incidents_24h": incidents_24h,
        "critical_incidents": critical,
        "warning_incidents": warning,
        "edge_devices": devices,
        "devices_online": online
    }


@api_router.get("/incidents")
async def get_incidents(client_id: str, limit: int = 50, severity: Optional[str] = None):
    """Get incidents for client"""
    
    query = {"client_id": client_id}
    if severity:
        query["severity"] = severity
    
    incidents = await db.incidents.find(
        query,
        {"_id": 0}
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


@app.on_event("startup")
async def startup():
    logger.info("SecureGuard Central Server starting...")
    logger.info(f"MongoDB: {MONGO_URL}")
    
    # Create indexes
    await db.clients.create_index("client_id", unique=True)
    await db.edge_devices.create_index("device_id", unique=True)
    await db.edge_devices.create_index("client_id")
    await db.incidents.create_index([("client_id", 1), ("timestamp", -1)])
    
    logger.info("Central Server ready!")


@app.on_event("shutdown")
async def shutdown():
    client.close()
    logger.info("Central Server shutdown")
