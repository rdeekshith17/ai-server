from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import base64
import cv2
import tempfile
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]

# LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

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
            image_contents=[image_content]
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
