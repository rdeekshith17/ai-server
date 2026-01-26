"""
Multi-Tenant Models for SecureGuard Enterprise Platform
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# ENUMS
# ===========================================

class PlanType(str, Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class ClientStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    CLIENT_OWNER = "client_owner"
    CLIENT_MANAGER = "client_manager"
    CLIENT_VIEWER = "client_viewer"
    API_ONLY = "api_only"

class CameraStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    DISABLED = "disabled"

class IncidentStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# ===========================================
# CLIENT (TENANT) MODELS
# ===========================================

class ContactInfo(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class Subscription(BaseModel):
    plan: PlanType = PlanType.TRIAL
    max_cameras: int = 2
    max_users: int = 1
    max_watchlist: int = 5
    features: List[str] = []
    billing_cycle: str = "monthly"
    price_cents: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

class ClientSettings(BaseModel):
    timezone: str = "UTC"
    alert_email: bool = True
    alert_sms: bool = False
    alert_webhook: Optional[str] = None
    alert_whatsapp: Optional[str] = None
    detection_sensitivity: str = "medium"
    auto_incident_creation: bool = True
    custom_branding: Optional[Dict[str, str]] = None

class APIKey(BaseModel):
    key_id: str = Field(default_factory=lambda: f"key_{uuid.uuid4().hex[:12]}")
    key_hash: str
    name: str
    permissions: List[str] = ["read"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    is_active: bool = True

class Client(BaseModel):
    """Multi-tenant client (organization)"""
    model_config = ConfigDict(extra="ignore")
    
    client_id: str = Field(default_factory=lambda: f"cli_{uuid.uuid4().hex[:12]}")
    name: str
    slug: str  # URL-friendly identifier
    contact: ContactInfo
    subscription: Subscription = Field(default_factory=Subscription)
    settings: ClientSettings = Field(default_factory=ClientSettings)
    api_keys: List[APIKey] = []
    status: ClientStatus = ClientStatus.TRIAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===========================================
# USER MODELS
# ===========================================

class UserPermissions(BaseModel):
    view_dashboard: bool = True
    view_live: bool = True
    view_incidents: bool = True
    manage_incidents: bool = False
    manage_cameras: bool = False
    manage_watchlist: bool = False
    view_analytics: bool = True
    manage_users: bool = False
    manage_settings: bool = False
    manage_billing: bool = False
    api_access: bool = False

class User(BaseModel):
    """User within a client organization"""
    model_config = ConfigDict(extra="ignore")
    
    user_id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}")
    client_id: str  # Tenant association
    email: EmailStr
    password_hash: str
    name: str
    role: UserRole = UserRole.CLIENT_VIEWER
    permissions: UserPermissions = Field(default_factory=UserPermissions)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===========================================
# STORE MODELS
# ===========================================

class Store(BaseModel):
    """Physical store location for a client"""
    model_config = ConfigDict(extra="ignore")
    
    store_id: str = Field(default_factory=lambda: f"str_{uuid.uuid4().hex[:12]}")
    client_id: str
    name: str
    store_type: str = "convenience"  # liquor, convenience, gas_station, retail
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "US"
    timezone: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===========================================
# CAMERA MODELS
# ===========================================

class DetectionZone(BaseModel):
    """Polygon defining detection area"""
    enabled: bool = True
    points: List[List[int]] = [[0, 0], [100, 0], [100, 100], [0, 100]]

class CameraDetectionSettings(BaseModel):
    enabled: bool = True
    sensitivity: str = "medium"
    detection_zone: Optional[DetectionZone] = None
    excluded_zones: List[DetectionZone] = []
    process_fps: int = 2
    enable_pose: bool = True
    enable_face_recognition: bool = True
    enable_gpt_analysis: bool = False

class CameraHealth(BaseModel):
    uptime_percent: float = 100.0
    avg_latency_ms: int = 0
    error_count_24h: int = 0
    last_error: Optional[str] = None
    frames_processed_24h: int = 0

class Camera(BaseModel):
    """RTSP camera within a client organization"""
    model_config = ConfigDict(extra="ignore")
    
    camera_id: str = Field(default_factory=lambda: f"cam_{uuid.uuid4().hex[:12]}")
    client_id: str
    store_id: Optional[str] = None
    name: str
    location: str = "Unknown"
    rtsp_url: str  # Will be encrypted in storage
    resolution: str = "1080p"
    fps: int = 15
    detection_settings: CameraDetectionSettings = Field(default_factory=CameraDetectionSettings)
    status: CameraStatus = CameraStatus.OFFLINE
    last_frame_at: Optional[datetime] = None
    health: CameraHealth = Field(default_factory=CameraHealth)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===========================================
# INCIDENT MODELS
# ===========================================

class IncidentDetails(BaseModel):
    person_description: Optional[str] = None
    items_involved: List[str] = []
    concealment_method: Optional[str] = None
    movement_towards_exit: bool = False
    behaviors: List[str] = []
    staff_theft_indicator: bool = False

class IncidentEvidence(BaseModel):
    frame_url: Optional[str] = None
    video_clip_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    frame_base64: Optional[str] = None  # Temporary storage

class WatchlistMatch(BaseModel):
    matched: bool = False
    person_id: Optional[str] = None
    person_name: Optional[str] = None
    match_confidence: float = 0.0

class MLMetadata(BaseModel):
    yolo_detections: int = 0
    pose_analysis: Optional[Dict[str, Any]] = None
    gpt_analysis: Optional[Dict[str, Any]] = None
    processing_time_ms: int = 0
    models_used: List[str] = []

class Incident(BaseModel):
    """Security incident detected by the system"""
    model_config = ConfigDict(extra="ignore")
    
    incident_id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:12]}")
    client_id: str
    camera_id: str
    store_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: SeverityLevel = SeverityLevel.WARNING
    confidence: float = 0.0
    detection_type: str = "theft"  # theft, watchlist_match, staff_theft, suspicious
    description: str = ""
    details: IncidentDetails = Field(default_factory=IncidentDetails)
    evidence: IncidentEvidence = Field(default_factory=IncidentEvidence)
    watchlist_match: WatchlistMatch = Field(default_factory=WatchlistMatch)
    ml_metadata: MLMetadata = Field(default_factory=MLMetadata)
    status: IncidentStatus = IncidentStatus.NEW
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===========================================
# WATCHLIST MODELS
# ===========================================

class WatchlistPerson(BaseModel):
    """Person in a client's watchlist"""
    model_config = ConfigDict(extra="ignore")
    
    person_id: str = Field(default_factory=lambda: f"wlp_{uuid.uuid4().hex[:12]}")
    client_id: str
    name: str
    alias: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    photo_base64: Optional[str] = None
    threat_level: str = "high"  # high, medium, low
    last_seen_at: Optional[datetime] = None
    last_seen_camera_id: Optional[str] = None
    sighting_count: int = 0
    notes: Optional[str] = None
    is_active: bool = True
    added_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===========================================
# REQUEST/RESPONSE MODELS
# ===========================================

class ClientCreate(BaseModel):
    name: str
    slug: str
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    plan: PlanType = PlanType.TRIAL

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[ContactInfo] = None
    settings: Optional[ClientSettings] = None
    status: Optional[ClientStatus] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRole = UserRole.CLIENT_VIEWER

class CameraCreate(BaseModel):
    name: str
    location: str
    rtsp_url: str
    store_id: Optional[str] = None
    detection_settings: Optional[CameraDetectionSettings] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]
    client: Dict[str, Any]


# ===========================================
# ADMIN MODELS
# ===========================================

class AdminDashboardStats(BaseModel):
    total_clients: int = 0
    active_clients: int = 0
    total_cameras: int = 0
    online_cameras: int = 0
    total_incidents_24h: int = 0
    critical_incidents_24h: int = 0
    total_users: int = 0
    monthly_revenue_cents: int = 0

class ClientSummary(BaseModel):
    client_id: str
    name: str
    plan: str
    status: str
    cameras_count: int
    incidents_24h: int
    last_activity: Optional[datetime]
