from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import base64
import cv2
import tempfile
import asyncio
import numpy as np
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

# ML Model imports
from ultralytics import YOLO
import warnings
warnings.filterwarnings('ignore')

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]

# LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# ============================================
# ML MODELS INITIALIZATION
# ============================================
# YOLO model for person detection and tracking
yolo_model = None
deepface_initialized = False

def get_yolo_model():
    """Lazy load YOLO model"""
    global yolo_model
    if yolo_model is None:
        try:
            yolo_model = YOLO('yolov8n.pt')  # Nano model for speed
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
    return yolo_model

def init_deepface():
    """Initialize DeepFace for face recognition"""
    global deepface_initialized
    if not deepface_initialized:
        try:
            # Import here to avoid loading at startup
            from deepface import DeepFace
            deepface_initialized = True
            logger.info("DeepFace initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DeepFace: {e}")
    return deepface_initialized

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class Incident(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    video_id: str
    video_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: str  # critical, warning, safe
    description: str
    confidence: float
    frame_index: int
    thumbnail_base64: Optional[str] = None
    behaviors_detected: List[str] = []
    location: str = "Unknown"
    store_type: str = "convenience"

class VideoAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, processing, completed, failed
    total_frames: int = 0
    analyzed_frames: int = 0
    incidents_count: int = 0
    duration_seconds: float = 0
    store_type: str = "convenience"

class AnalyticsData(BaseModel):
    total_videos: int = 0
    total_incidents: int = 0
    critical_alerts: int = 0
    warnings: int = 0
    safe_analyses: int = 0
    average_confidence: float = 0.0
    incidents_by_hour: dict = {}
    incidents_by_type: dict = {}

class WatchlistPerson(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    alias: Optional[str] = None
    description: Optional[str] = None
    photo_base64: str
    threat_level: str = "high"  # high, medium, low
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: Optional[datetime] = None
    notes: Optional[str] = None
    is_active: bool = True

# ============================================
# LIVE CAMERA FEED SECTION - TO BE IMPLEMENTED
# ============================================
# TODO: Add live camera feed integration
# 
# To add RTSP camera support:
# 1. Create a CameraFeed model with fields: id, name, rtsp_url, location, is_active
# 2. Add endpoints: POST /api/cameras (add camera), GET /api/cameras (list), DELETE /api/cameras/{id}
# 3. Create a background task that:
#    - Connects to RTSP stream using cv2.VideoCapture(rtsp_url)
#    - Extracts frames at intervals (e.g., every 2-5 seconds)
#    - Runs analyze_frame_with_gpt() on each frame
#    - Checks against watchlist
#    - Creates incidents if suspicious activity detected
# 4. Add WebSocket endpoint for real-time frame streaming to frontend
#
# Example RTSP URL formats:
# - rtsp://username:password@ip_address:554/stream1
# - rtsp://ip_address:554/live/ch00_0
# ============================================

# Helper functions
def extract_frames_from_video(video_path: str, max_frames: int = 10) -> List[tuple]:
    """Extract frames from video at regular intervals"""
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_path}")
        return frames
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    # Calculate frame interval
    interval = max(1, total_frames // max_frames)
    
    frame_idx = 0
    extracted_count = 0
    
    while cap.isOpened() and extracted_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % interval == 0:
            # Resize frame for faster processing
            frame = cv2.resize(frame, (640, 480))
            # Convert to base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            frames.append((frame_idx, frame_base64, frame_idx / fps if fps > 0 else 0))
            extracted_count += 1
        
        frame_idx += 1
    
    cap.release()
    return frames, total_frames, duration

async def analyze_frame_with_gpt(frame_base64: str, frame_idx: int, video_name: str) -> dict:
    """Analyze a single frame using GPT-5.2 Vision"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"analysis-{uuid.uuid4()}",
            system_message="""You are an advanced security AI trained to detect shoplifting and suspicious behavior in retail environments (liquor stores, convenience stores, gas stations).

Analyze the image and look for:
1. Concealment behavior (hiding items in clothing, bags, pockets)
2. Unusual item handling (removing security tags, switching labels)
3. Coordinated group activity (distracting staff, blocking cameras)
4. Loitering near high-value items
5. Nervous behavior (looking around frequently, avoiding staff)
6. Unusual clothing (oversized coats in warm weather, bulging pockets)
7. Quick grabbing motions
8. Avoiding checkout areas

Respond in this exact JSON format:
{
    "is_suspicious": true/false,
    "severity": "critical" | "warning" | "safe",
    "confidence": 0.0-1.0,
    "description": "Brief description of what you see",
    "behaviors_detected": ["list", "of", "behaviors"],
    "reasoning": "Explain why this is or isn't suspicious"
}"""
        ).with_model("openai", "gpt-5.2")

        image_content = ImageContent(image_base64=frame_base64)
        
        user_message = UserMessage(
            text=f"Analyze this security camera frame from {video_name} for potential shoplifting or suspicious activity.",
            file_contents=[image_content]
        )
        
        response = await chat.send_message(user_message)
        
        # Parse JSON response
        import json
        # Clean response - extract JSON if wrapped in markdown
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        result['frame_index'] = frame_idx
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing frame {frame_idx}: {str(e)}")
        return {
            "is_suspicious": False,
            "severity": "safe",
            "confidence": 0.0,
            "description": f"Analysis failed: {str(e)}",
            "behaviors_detected": [],
            "reasoning": "Error during analysis",
            "frame_index": frame_idx
        }

# Routes
@api_router.get("/")
async def root():
    return {"message": "Shoplifting Detection API v1.0"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks

@api_router.post("/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    store_type: str = Form("convenience")
):
    """Upload a video file for analysis"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Create video analysis record
        video_id = str(uuid.uuid4())
        video_doc = {
            "id": video_id,
            "filename": file.filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "total_frames": 0,
            "analyzed_frames": 0,
            "incidents_count": 0,
            "duration_seconds": 0,
            "store_type": store_type,
            "content_type": file.content_type
        }
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Extract video info
        cap = cv2.VideoCapture(tmp_path)
        if cap.isOpened():
            video_doc["total_frames"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            video_doc["duration_seconds"] = video_doc["total_frames"] / fps if fps > 0 else 0
        cap.release()
        
        # Store temp path for later analysis
        video_doc["temp_path"] = tmp_path
        
        await db.videos.insert_one(video_doc)
        
        return {
            "id": video_id,
            "filename": file.filename,
            "status": "pending",
            "total_frames": video_doc["total_frames"],
            "duration_seconds": video_doc["duration_seconds"],
            "message": "Video uploaded successfully. Call /api/videos/analyze to start analysis."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/videos/{video_id}/analyze")
async def analyze_video(video_id: str, max_frames: int = 8):
    """Analyze an uploaded video for shoplifting behavior"""
    try:
        # Get video record
        video = await db.videos.find_one({"id": video_id}, {"_id": 0})
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if video.get("status") == "processing":
            return {"message": "Video is already being analyzed", "status": "processing"}
        
        # Update status to processing
        await db.videos.update_one(
            {"id": video_id},
            {"$set": {"status": "processing"}}
        )
        
        tmp_path = video.get("temp_path")
        if not tmp_path or not os.path.exists(tmp_path):
            raise HTTPException(status_code=400, detail="Video file not found. Please re-upload.")
        
        # Extract frames
        frames_data, total_frames, duration = extract_frames_from_video(tmp_path, max_frames)
        
        if not frames_data:
            await db.videos.update_one(
                {"id": video_id},
                {"$set": {"status": "failed"}}
            )
            raise HTTPException(status_code=400, detail="Could not extract frames from video")
        
        incidents = []
        analyzed_count = 0
        
        # Analyze each frame
        for frame_idx, frame_base64, timestamp in frames_data:
            result = await analyze_frame_with_gpt(frame_base64, frame_idx, video.get("filename", "video"))
            analyzed_count += 1
            
            # Update progress
            await db.videos.update_one(
                {"id": video_id},
                {"$set": {"analyzed_frames": analyzed_count}}
            )
            
            # If suspicious, create incident
            if result.get("is_suspicious") or result.get("severity") in ["critical", "warning"]:
                incident = {
                    "id": str(uuid.uuid4()),
                    "video_id": video_id,
                    "video_name": video.get("filename", "Unknown"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "severity": result.get("severity", "warning"),
                    "description": result.get("description", "Suspicious activity detected"),
                    "confidence": result.get("confidence", 0.5),
                    "frame_index": frame_idx,
                    "frame_time_seconds": timestamp,
                    "thumbnail_base64": frame_base64[:100] + "..." if frame_base64 else None,  # Truncate for storage
                    "behaviors_detected": result.get("behaviors_detected", []),
                    "reasoning": result.get("reasoning", ""),
                    "location": "Main Floor",
                    "store_type": video.get("store_type", "convenience")
                }
                incidents.append(incident)
                await db.incidents.insert_one(incident)
        
        # Update video status
        await db.videos.update_one(
            {"id": video_id},
            {
                "$set": {
                    "status": "completed",
                    "analyzed_frames": analyzed_count,
                    "incidents_count": len(incidents)
                }
            }
        )
        
        # Clean up temp file
        try:
            os.remove(tmp_path)
            await db.videos.update_one(
                {"id": video_id},
                {"$unset": {"temp_path": ""}}
            )
        except:
            pass
        
        return {
            "video_id": video_id,
            "status": "completed",
            "frames_analyzed": analyzed_count,
            "incidents_detected": len(incidents),
            "incidents": [
                {
                    "id": i["id"],
                    "severity": i["severity"],
                    "description": i["description"],
                    "confidence": i["confidence"],
                    "behaviors": i["behaviors_detected"]
                } for i in incidents
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        await db.videos.update_one(
            {"id": video_id},
            {"$set": {"status": "failed"}}
        )
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/videos")
async def get_videos():
    """Get all uploaded videos"""
    videos = await db.videos.find({}, {"_id": 0, "temp_path": 0}).sort("uploaded_at", -1).to_list(100)
    return {"videos": videos}

@api_router.get("/videos/{video_id}")
async def get_video(video_id: str):
    """Get a specific video"""
    video = await db.videos.find_one({"id": video_id}, {"_id": 0, "temp_path": 0})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@api_router.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    """Delete a video and its incidents"""
    video = await db.videos.find_one({"id": video_id})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete temp file if exists
    if video.get("temp_path") and os.path.exists(video["temp_path"]):
        try:
            os.remove(video["temp_path"])
        except:
            pass
    
    await db.videos.delete_one({"id": video_id})
    await db.incidents.delete_many({"video_id": video_id})
    
    return {"message": "Video and related incidents deleted"}

@api_router.get("/incidents")
async def get_incidents(
    severity: Optional[str] = None,
    store_type: Optional[str] = None,
    limit: int = 50
):
    """Get all incidents with optional filtering"""
    query = {}
    if severity:
        query["severity"] = severity
    if store_type:
        query["store_type"] = store_type
    
    incidents = await db.incidents.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"incidents": incidents, "total": len(incidents)}

@api_router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get a specific incident"""
    incident = await db.incidents.find_one({"id": incident_id}, {"_id": 0})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@api_router.delete("/incidents/{incident_id}")
async def delete_incident(incident_id: str):
    """Delete an incident"""
    result = await db.incidents.delete_one({"id": incident_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": "Incident deleted"}

@api_router.get("/analytics")
async def get_analytics():
    """Get analytics data"""
    try:
        # Count totals
        total_videos = await db.videos.count_documents({})
        total_incidents = await db.incidents.count_documents({})
        critical_alerts = await db.incidents.count_documents({"severity": "critical"})
        warnings = await db.incidents.count_documents({"severity": "warning"})
        safe_analyses = await db.videos.count_documents({"status": "completed"}) - (critical_alerts + warnings)
        
        # Get average confidence
        pipeline = [
            {"$group": {"_id": None, "avg_confidence": {"$avg": "$confidence"}}}
        ]
        confidence_result = await db.incidents.aggregate(pipeline).to_list(1)
        avg_confidence = confidence_result[0]["avg_confidence"] if confidence_result else 0.0
        
        # Incidents by behavior type
        behavior_pipeline = [
            {"$unwind": "$behaviors_detected"},
            {"$group": {"_id": "$behaviors_detected", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        behavior_result = await db.incidents.aggregate(behavior_pipeline).to_list(10)
        incidents_by_type = {item["_id"]: item["count"] for item in behavior_result}
        
        # Incidents by store type
        store_pipeline = [
            {"$group": {"_id": "$store_type", "count": {"$sum": 1}}}
        ]
        store_result = await db.incidents.aggregate(store_pipeline).to_list(10)
        incidents_by_store = {item["_id"]: item["count"] for item in store_result}
        
        # Recent trend (last 7 days)
        from datetime import timedelta
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        return {
            "total_videos": total_videos,
            "total_incidents": total_incidents,
            "critical_alerts": critical_alerts,
            "warnings": warnings,
            "safe_analyses": max(0, safe_analyses),
            "average_confidence": round(avg_confidence * 100, 1) if avg_confidence else 0,
            "incidents_by_type": incidents_by_type,
            "incidents_by_store": incidents_by_store,
            "detection_rate": round((total_incidents / max(1, total_videos)) * 100, 1)
        }
        
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return {
            "total_videos": 0,
            "total_incidents": 0,
            "critical_alerts": 0,
            "warnings": 0,
            "safe_analyses": 0,
            "average_confidence": 0,
            "incidents_by_type": {},
            "incidents_by_store": {},
            "detection_rate": 0
        }

@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get real-time dashboard statistics"""
    try:
        total_videos = await db.videos.count_documents({})
        processing_videos = await db.videos.count_documents({"status": "processing"})
        total_incidents = await db.incidents.count_documents({})
        critical_count = await db.incidents.count_documents({"severity": "critical"})
        warning_count = await db.incidents.count_documents({"severity": "warning"})
        
        # Get recent incidents
        recent_incidents = await db.incidents.find(
            {}, 
            {"_id": 0, "thumbnail_base64": 0}
        ).sort("timestamp", -1).to_list(5)
        
        # Get recent videos
        recent_videos = await db.videos.find(
            {},
            {"_id": 0, "temp_path": 0}
        ).sort("uploaded_at", -1).to_list(5)
        
        return {
            "total_videos": total_videos,
            "processing_videos": processing_videos,
            "total_incidents": total_incidents,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "safe_count": max(0, total_videos - critical_count - warning_count),
            "recent_incidents": recent_incidents,
            "recent_videos": recent_videos,
            "system_status": "online",
            "ai_status": "active" if EMERGENT_LLM_KEY else "offline"
        }
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return {
            "total_videos": 0,
            "processing_videos": 0,
            "total_incidents": 0,
            "critical_count": 0,
            "warning_count": 0,
            "safe_count": 0,
            "recent_incidents": [],
            "recent_videos": [],
            "system_status": "error",
            "ai_status": "offline"
        }

# ============================================
# WATCHLIST ENDPOINTS
# ============================================

@api_router.post("/watchlist")
async def add_to_watchlist(
    name: str = Form(...),
    photo: UploadFile = File(...),
    alias: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    threat_level: str = Form("high"),
    notes: Optional[str] = Form(None)
):
    """Add a person to the watchlist"""
    try:
        # Validate image type
        if not photo.content_type or not photo.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and encode image
        content = await photo.read()
        photo_base64 = base64.b64encode(content).decode('utf-8')
        
        person_id = str(uuid.uuid4())
        person_doc = {
            "id": person_id,
            "name": name,
            "alias": alias,
            "description": description,
            "photo_base64": photo_base64,
            "threat_level": threat_level,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "last_seen": None,
            "notes": notes,
            "is_active": True
        }
        
        await db.watchlist.insert_one(person_doc)
        
        # Return without photo_base64 for response size
        return {
            "id": person_id,
            "name": name,
            "alias": alias,
            "threat_level": threat_level,
            "message": "Person added to watchlist successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Watchlist add error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/watchlist")
async def get_watchlist(active_only: bool = True):
    """Get all people in the watchlist"""
    query = {"is_active": True} if active_only else {}
    # Exclude full photo for list view, include thumbnail info
    people = await db.watchlist.find(query, {"_id": 0}).sort("added_at", -1).to_list(100)
    
    # Add photo preview indicator
    for person in people:
        person["has_photo"] = bool(person.get("photo_base64"))
        # Truncate photo for list view
        if person.get("photo_base64"):
            person["photo_preview"] = person["photo_base64"][:100] + "..."
            del person["photo_base64"]
    
    return {"watchlist": people, "total": len(people)}

@api_router.get("/watchlist/{person_id}")
async def get_watchlist_person(person_id: str):
    """Get a specific person from watchlist with full photo"""
    person = await db.watchlist.find_one({"id": person_id}, {"_id": 0})
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person

@api_router.put("/watchlist/{person_id}")
async def update_watchlist_person(
    person_id: str,
    name: Optional[str] = Form(None),
    alias: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    threat_level: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None)
):
    """Update a person in the watchlist"""
    person = await db.watchlist.find_one({"id": person_id})
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    update_data = {}
    if name is not None: update_data["name"] = name
    if alias is not None: update_data["alias"] = alias
    if description is not None: update_data["description"] = description
    if threat_level is not None: update_data["threat_level"] = threat_level
    if notes is not None: update_data["notes"] = notes
    if is_active is not None: update_data["is_active"] = is_active
    
    if update_data:
        await db.watchlist.update_one({"id": person_id}, {"$set": update_data})
    
    return {"message": "Person updated successfully"}

@api_router.delete("/watchlist/{person_id}")
async def delete_watchlist_person(person_id: str):
    """Delete a person from the watchlist"""
    result = await db.watchlist.delete_one({"id": person_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Person removed from watchlist"}

@api_router.get("/watchlist/stats/summary")
async def get_watchlist_stats():
    """Get watchlist statistics"""
    total = await db.watchlist.count_documents({})
    active = await db.watchlist.count_documents({"is_active": True})
    high_threat = await db.watchlist.count_documents({"threat_level": "high", "is_active": True})
    medium_threat = await db.watchlist.count_documents({"threat_level": "medium", "is_active": True})
    low_threat = await db.watchlist.count_documents({"threat_level": "low", "is_active": True})
    
    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "by_threat_level": {
            "high": high_threat,
            "medium": medium_threat,
            "low": low_threat
        }
    }

async def check_watchlist_match(frame_base64: str) -> dict:
    """Check if any person in the watchlist matches the frame using GPT Vision"""
    # Get active watchlist with photos
    watchlist = await db.watchlist.find(
        {"is_active": True}, 
        {"_id": 0, "id": 1, "name": 1, "alias": 1, "photo_base64": 1, "threat_level": 1}
    ).to_list(50)
    
    if not watchlist:
        return {"match_found": False, "matches": []}
    
    try:
        # Create a prompt with watchlist context
        watchlist_descriptions = []
        for i, person in enumerate(watchlist):
            desc = f"Person {i+1}: {person['name']}"
            if person.get('alias'):
                desc += f" (alias: {person['alias']})"
            watchlist_descriptions.append(desc)
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"watchlist-check-{uuid.uuid4()}",
            system_message=f"""You are a facial recognition AI. You have a watchlist of known individuals.
            
Watchlist:
{chr(10).join(watchlist_descriptions)}

Compare the provided security camera frame against each watchlist photo.
Look for facial features, body type, clothing style, and any distinguishing characteristics.

Respond in JSON format:
{{
    "match_found": true/false,
    "matches": [
        {{
            "person_index": 1,
            "confidence": 0.0-1.0,
            "reasoning": "explanation of match"
        }}
    ]
}}

Only report matches with confidence > 0.6"""
        ).with_model("openai", "gpt-5.2")
        
        # Create image contents - frame + watchlist photos
        image_contents = [ImageContent(image_base64=frame_base64)]
        for person in watchlist[:5]:  # Limit to 5 photos to avoid token limits
            if person.get("photo_base64"):
                image_contents.append(ImageContent(image_base64=person["photo_base64"]))
        
        user_message = UserMessage(
            text="Compare the first image (security camera frame) against the following watchlist photos. Identify any matches.",
            file_contents=image_contents
        )
        
        response = await chat.send_message(user_message)
        
        # Parse response
        import json
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        # Enrich matches with person data
        if result.get("match_found") and result.get("matches"):
            enriched_matches = []
            for match in result["matches"]:
                idx = match.get("person_index", 1) - 1
                if 0 <= idx < len(watchlist):
                    enriched_matches.append({
                        "person_id": watchlist[idx]["id"],
                        "person_name": watchlist[idx]["name"],
                        "threat_level": watchlist[idx]["threat_level"],
                        "confidence": match.get("confidence", 0),
                        "reasoning": match.get("reasoning", "")
                    })
            result["matches"] = enriched_matches
        
        return result
        
    except Exception as e:
        logger.error(f"Watchlist check error: {str(e)}")
        return {"match_found": False, "matches": [], "error": str(e)}

# ============================================
# LIVE CAMERA FEED PLACEHOLDER
# ============================================
# TODO: Implement these endpoints when ready
#
# @api_router.post("/cameras")
# async def add_camera(name: str, rtsp_url: str, location: str):
#     """Add a new camera feed"""
#     pass
#
# @api_router.get("/cameras")  
# async def list_cameras():
#     """List all camera feeds"""
#     pass
#
# @api_router.delete("/cameras/{camera_id}")
# async def remove_camera(camera_id: str):
#     """Remove a camera feed"""
#     pass
#
# @api_router.post("/cameras/{camera_id}/start")
# async def start_camera_monitoring(camera_id: str):
#     """Start monitoring a camera feed"""
#     pass
#
# @api_router.post("/cameras/{camera_id}/stop")
# async def stop_camera_monitoring(camera_id: str):
#     """Stop monitoring a camera feed"""
#     pass
# ============================================

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
