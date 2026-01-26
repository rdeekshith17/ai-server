"""
Alert Service for SecureGuard Multi-Tenant Platform
Handles WhatsApp/SMS notifications via Twilio
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import os
import logging

logger = logging.getLogger(__name__)

alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])

# Twilio configuration - User will add these credentials later
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # Twilio sandbox number

# Initialize Twilio client only if credentials are available
twilio_client = None
try:
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("Twilio client initialized successfully")
except ImportError:
    logger.warning("Twilio library not installed. Run: pip install twilio")
except Exception as e:
    logger.error(f"Failed to initialize Twilio client: {e}")


# ===========================================
# MODELS
# ===========================================

class AlertSettings(BaseModel):
    """Alert settings for a client"""
    enabled: bool = False
    alert_on_critical: bool = True
    alert_on_warning: bool = False
    whatsapp_numbers: List[str] = []
    email_addresses: List[str] = []
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None    # "07:00"
    cooldown_minutes: int = 5  # Minimum time between alerts for same camera


class AlertSettingsUpdate(BaseModel):
    """Update alert settings"""
    client_id: str
    enabled: Optional[bool] = None
    alert_on_critical: Optional[bool] = None
    alert_on_warning: Optional[bool] = None
    whatsapp_numbers: Optional[List[str]] = None
    email_addresses: Optional[List[str]] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    cooldown_minutes: Optional[int] = None


class TestAlertRequest(BaseModel):
    """Test alert request"""
    client_id: str
    phone_number: str


# ===========================================
# HELPER FUNCTIONS
# ===========================================

async def send_whatsapp_alert(to_number: str, message: str) -> dict:
    """
    Send WhatsApp message via Twilio
    Returns: {"success": bool, "error": str or None, "message_sid": str or None}
    """
    if not twilio_client:
        return {
            "success": False, 
            "error": "Twilio not configured. Add TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to backend/.env",
            "message_sid": None
        }
    
    try:
        # Format number for WhatsApp
        whatsapp_to = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number
        
        message_result = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=message,
            to=whatsapp_to
        )
        
        logger.info(f"WhatsApp alert sent to {to_number}: {message_result.sid}")
        return {"success": True, "error": None, "message_sid": message_result.sid}
    
    except Exception as e:
        logger.error(f"Failed to send WhatsApp alert to {to_number}: {e}")
        return {"success": False, "error": str(e), "message_sid": None}


async def send_incident_alert(db: AsyncIOMotorDatabase, incident: dict, client_id: str):
    """
    Send alert for an incident based on client settings
    Called from the incident creation flow
    """
    # Get client settings
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        logger.warning(f"Client not found for alert: {client_id}")
        return
    
    alert_settings = client.get("alert_settings", {})
    
    # Check if alerts are enabled
    if not alert_settings.get("enabled", False):
        return
    
    # Check severity threshold
    severity = incident.get("severity", "safe")
    if severity == "critical" and not alert_settings.get("alert_on_critical", True):
        return
    if severity == "warning" and not alert_settings.get("alert_on_warning", False):
        return
    if severity == "safe":
        return  # Never alert on safe
    
    # Check quiet hours
    quiet_start = alert_settings.get("quiet_hours_start")
    quiet_end = alert_settings.get("quiet_hours_end")
    if quiet_start and quiet_end:
        now = datetime.now(timezone.utc)
        current_time = now.strftime("%H:%M")
        if quiet_start <= current_time or current_time <= quiet_end:
            logger.info(f"Skipping alert during quiet hours for client {client_id}")
            return
    
    # Check cooldown (prevent alert spam)
    camera_id = incident.get("camera_id")
    if camera_id:
        cooldown_minutes = alert_settings.get("cooldown_minutes", 5)
        last_alert = await db.alert_log.find_one(
            {
                "client_id": client_id,
                "camera_id": camera_id,
                "created_at": {"$gte": datetime.now(timezone.utc).isoformat()}
            },
            sort=[("created_at", -1)]
        )
        if last_alert:
            # Skip if within cooldown period
            logger.info(f"Skipping alert due to cooldown for camera {camera_id}")
            return
    
    # Build alert message
    message = build_alert_message(incident, client.get("name", "Unknown"))
    
    # Send WhatsApp alerts
    whatsapp_numbers = alert_settings.get("whatsapp_numbers", [])
    for number in whatsapp_numbers:
        result = await send_whatsapp_alert(number, message)
        
        # Log the alert
        await db.alert_log.insert_one({
            "client_id": client_id,
            "incident_id": incident.get("id"),
            "camera_id": camera_id,
            "channel": "whatsapp",
            "recipient": number,
            "success": result["success"],
            "error": result.get("error"),
            "message_sid": result.get("message_sid"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })


def build_alert_message(incident: dict, client_name: str) -> str:
    """Build formatted alert message"""
    severity = incident.get("severity", "unknown").upper()
    confidence = incident.get("confidence", 0) * 100
    description = incident.get("description", "Suspicious activity detected")
    location = incident.get("camera_location", "Unknown location")
    
    emoji = "🚨" if severity == "CRITICAL" else "⚠️"
    
    message = f"""
{emoji} *SECUREGUARD ALERT* {emoji}

*Severity:* {severity}
*Client:* {client_name}
*Location:* {location}
*Confidence:* {confidence:.0f}%

*Details:*
{description[:200]}...

View full incident in dashboard.
"""
    return message.strip()


# ===========================================
# ALERT ROUTES
# ===========================================

def create_alerts_routes(db: AsyncIOMotorDatabase) -> APIRouter:
    """Create alerts router with database dependency"""
    
    @alerts_router.get("/settings/{client_id}")
    async def get_alert_settings(client_id: str):
        """Get alert settings for a client"""
        client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Return settings with defaults
        default_settings = AlertSettings().dict()
        settings = client.get("alert_settings", default_settings)
        
        return {
            "client_id": client_id,
            "settings": settings,
            "twilio_configured": twilio_client is not None
        }
    
    @alerts_router.put("/settings")
    async def update_alert_settings(settings: AlertSettingsUpdate):
        """Update alert settings for a client"""
        client = await db.clients.find_one({"client_id": settings.client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Build update dict with only provided fields
        update_dict = {}
        if settings.enabled is not None:
            update_dict["alert_settings.enabled"] = settings.enabled
        if settings.alert_on_critical is not None:
            update_dict["alert_settings.alert_on_critical"] = settings.alert_on_critical
        if settings.alert_on_warning is not None:
            update_dict["alert_settings.alert_on_warning"] = settings.alert_on_warning
        if settings.whatsapp_numbers is not None:
            update_dict["alert_settings.whatsapp_numbers"] = settings.whatsapp_numbers
        if settings.email_addresses is not None:
            update_dict["alert_settings.email_addresses"] = settings.email_addresses
        if settings.quiet_hours_start is not None:
            update_dict["alert_settings.quiet_hours_start"] = settings.quiet_hours_start
        if settings.quiet_hours_end is not None:
            update_dict["alert_settings.quiet_hours_end"] = settings.quiet_hours_end
        if settings.cooldown_minutes is not None:
            update_dict["alert_settings.cooldown_minutes"] = settings.cooldown_minutes
        
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.clients.update_one(
            {"client_id": settings.client_id},
            {"$set": update_dict}
        )
        
        return {"success": True, "message": "Alert settings updated"}
    
    @alerts_router.post("/test")
    async def send_test_alert(request: TestAlertRequest):
        """Send a test WhatsApp alert"""
        if not twilio_client:
            return {
                "success": False,
                "error": "Twilio not configured. Add TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to backend/.env"
            }
        
        # Get client name
        client = await db.clients.find_one({"client_id": request.client_id}, {"_id": 0, "name": 1})
        client_name = client.get("name", "Test Client") if client else "Test Client"
        
        test_incident = {
            "severity": "critical",
            "confidence": 0.95,
            "description": "This is a TEST ALERT from SecureGuard. If you received this, WhatsApp alerts are working correctly!",
            "camera_location": "Test Camera"
        }
        
        message = build_alert_message(test_incident, client_name)
        result = await send_whatsapp_alert(request.phone_number, message)
        
        # Log the test alert
        await db.alert_log.insert_one({
            "client_id": request.client_id,
            "incident_id": "test",
            "channel": "whatsapp",
            "recipient": request.phone_number,
            "success": result["success"],
            "error": result.get("error"),
            "message_sid": result.get("message_sid"),
            "is_test": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return result
    
    @alerts_router.get("/log/{client_id}")
    async def get_alert_log(client_id: str, limit: int = 50):
        """Get alert history for a client"""
        logs = await db.alert_log.find(
            {"client_id": client_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return {"logs": logs, "total": len(logs)}
    
    @alerts_router.get("/status")
    async def get_alert_service_status():
        """Get alert service configuration status"""
        return {
            "twilio_configured": twilio_client is not None,
            "twilio_account_sid": TWILIO_ACCOUNT_SID[:8] + "..." if TWILIO_ACCOUNT_SID else None,
            "whatsapp_from": TWILIO_WHATSAPP_FROM if twilio_client else None,
            "setup_instructions": {
                "step1": "Create a Twilio account at https://www.twilio.com/",
                "step2": "Enable WhatsApp Sandbox in Twilio Console",
                "step3": "Add TWILIO_ACCOUNT_SID to backend/.env",
                "step4": "Add TWILIO_AUTH_TOKEN to backend/.env",
                "step5": "Optionally set TWILIO_WHATSAPP_FROM for production WhatsApp number"
            }
        }
    
    return alerts_router
