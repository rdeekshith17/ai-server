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
yolo_pose_model = None
deepface_initialized = False

# Live feed state management
live_feeds = {}  # Store active camera feeds

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

def get_yolo_pose_model():
    """Lazy load YOLO pose model for skeleton detection"""
    global yolo_pose_model
    if yolo_pose_model is None:
        try:
            yolo_pose_model = YOLO('yolov8n-pose.pt')  # Pose estimation model
            logger.info("YOLO Pose model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO Pose model: {e}")
    return yolo_pose_model

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

# ============================================
# DECISION ENGINE
# ============================================
class DecisionEngine:
    """AI Decision Engine for threat assessment"""
    
    ACTIVITY_THRESHOLDS = {
        "item_in_pocket": 0.7,
        "concealment": 0.6,
        "loitering": 0.5,
        "exit_movement": 0.6,
        "staff_theft": 0.7
    }
    
    THREAT_LEVELS = {
        "critical": 0.8,
        "warning": 0.5,
        "safe": 0.0
    }
    
    @staticmethod
    def analyze_pose(keypoints: List, bbox: List) -> Dict:
        """Analyze pose keypoints for suspicious behavior"""
        activities = []
        confidence_scores = {}
        
        if not keypoints or len(keypoints) < 17:
            return {"activities": [], "scores": {}, "threat_level": "safe"}
        
        # Keypoint indices (COCO format):
        # 0: nose, 5-6: shoulders, 7-8: elbows, 9-10: wrists
        # 11-12: hips, 13-14: knees, 15-16: ankles
        
        try:
            # Extract key body parts
            left_wrist = keypoints[9] if len(keypoints) > 9 else None
            right_wrist = keypoints[10] if len(keypoints) > 10 else None
            left_hip = keypoints[11] if len(keypoints) > 11 else None
            right_hip = keypoints[12] if len(keypoints) > 12 else None
            left_shoulder = keypoints[5] if len(keypoints) > 5 else None
            right_shoulder = keypoints[6] if len(keypoints) > 6 else None
            
            # Check for hands near pocket area (item in pocket detection)
            if left_wrist and left_hip:
                dist_left = abs(left_wrist[1] - left_hip[1])
                if dist_left < 50:  # Close to hip
                    activities.append("item_in_pocket")
                    confidence_scores["item_in_pocket"] = min(0.85 + (50 - dist_left) / 100, 0.95)
            
            if right_wrist and right_hip:
                dist_right = abs(right_wrist[1] - right_hip[1])
                if dist_right < 50:
                    if "item_in_pocket" not in activities:
                        activities.append("item_in_pocket")
                        confidence_scores["item_in_pocket"] = min(0.85 + (50 - dist_right) / 100, 0.95)
                    else:
                        confidence_scores["item_in_pocket"] = min(confidence_scores["item_in_pocket"] + 0.1, 0.98)
            
            # Check for concealment behavior (hands near torso)
            if left_wrist and right_wrist and left_shoulder and right_shoulder:
                torso_center_y = (left_shoulder[1] + right_shoulder[1]) / 2
                if abs(left_wrist[1] - torso_center_y) < 80 or abs(right_wrist[1] - torso_center_y) < 80:
                    activities.append("concealment_posture")
                    confidence_scores["concealment_posture"] = 0.75
            
            # Determine standing vs walking based on leg positions
            left_knee = keypoints[13] if len(keypoints) > 13 else None
            right_knee = keypoints[14] if len(keypoints) > 14 else None
            
            if left_knee and right_knee:
                knee_diff = abs(left_knee[0] - right_knee[0])
                if knee_diff > 30:
                    activities.append("walking")
                    confidence_scores["walking"] = min(0.7 + knee_diff / 200, 0.95)
                else:
                    activities.append("standing")
                    confidence_scores["standing"] = 0.8
            
        except Exception as e:
            logger.error(f"Pose analysis error: {e}")
        
        # Calculate threat level
        threat_score = 0.0
        if "item_in_pocket" in activities:
            threat_score += confidence_scores.get("item_in_pocket", 0) * 0.5
        if "concealment_posture" in activities:
            threat_score += confidence_scores.get("concealment_posture", 0) * 0.3
        
        threat_level = "safe"
        if threat_score >= DecisionEngine.THREAT_LEVELS["critical"]:
            threat_level = "critical"
        elif threat_score >= DecisionEngine.THREAT_LEVELS["warning"]:
            threat_level = "warning"
        
        return {
            "activities": activities,
            "scores": confidence_scores,
            "threat_level": threat_level,
            "threat_score": round(threat_score, 2)
        }
    
    @staticmethod
    def classify_overall_behavior(detections: List[Dict]) -> Dict:
        """Classify overall scene behavior"""
        total_persons = len(detections)
        suspicious_count = 0
        activities_summary = {}
        
        for det in detections:
            if det.get("threat_level") in ["critical", "warning"]:
                suspicious_count += 1
            for activity in det.get("activities", []):
                activities_summary[activity] = activities_summary.get(activity, 0) + 1
        
        scene_status = "normal"
        if suspicious_count > 0:
            scene_status = "alert"
        if suspicious_count >= 2 or any(d.get("threat_level") == "critical" for d in detections):
            scene_status = "critical"
        
        return {
            "total_persons": total_persons,
            "suspicious_count": suspicious_count,
            "scene_status": scene_status,
            "activities_summary": activities_summary
        }

decision_engine = DecisionEngine()

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

class CameraFeed(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    source: str  # RTSP URL, video file path, or "webcam"
    location: str = "Main Floor"
    store_type: str = "convenience"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============================================
# LIVE FEED PROCESSING FUNCTIONS
# ============================================

def process_frame_with_detection(frame: np.ndarray, draw_overlay: bool = True) -> Dict[str, Any]:
    """
    Process a single frame with YOLO detection and pose estimation.
    Returns detection results and optionally the annotated frame.
    """
    results = {
        "detections": [],
        "frame_annotated": None,
        "scene_analysis": {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Get YOLO models
        detection_model = get_yolo_model()
        pose_model = get_yolo_pose_model()
        
        annotated_frame = frame.copy() if draw_overlay else None
        height, width = frame.shape[:2]
        
        # Run person detection
        if detection_model:
            det_results = detection_model(frame, verbose=False, classes=[0])  # class 0 = person
            
            for det_result in det_results:
                boxes = det_result.boxes
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    confidence = float(box.conf[0])
                    
                    if confidence < 0.5:
                        continue
                    
                    detection = {
                        "id": i,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(confidence, 2),
                        "activities": [],
                        "activity_scores": {},
                        "threat_level": "safe",
                        "keypoints": []
                    }
                    
                    # Determine position
                    center_x = (x1 + x2) / 2
                    if center_x < width * 0.25:
                        detection["position"] = "left_edge"
                    elif center_x > width * 0.75:
                        detection["position"] = "right_edge"
                    else:
                        detection["position"] = "center"
                    
                    results["detections"].append(detection)
        
        # Run pose estimation
        if pose_model and results["detections"]:
            pose_results = pose_model(frame, verbose=False)
            
            for pose_result in pose_results:
                if hasattr(pose_result, 'keypoints') and pose_result.keypoints is not None:
                    keypoints_data = pose_result.keypoints.data
                    
                    for idx, kpts in enumerate(keypoints_data):
                        if idx < len(results["detections"]):
                            kpts_list = kpts.cpu().numpy().tolist()
                            results["detections"][idx]["keypoints"] = kpts_list
                            
                            # Analyze pose with decision engine
                            pose_analysis = decision_engine.analyze_pose(
                                kpts_list, 
                                results["detections"][idx]["bbox"]
                            )
                            results["detections"][idx].update({
                                "activities": pose_analysis["activities"],
                                "activity_scores": pose_analysis["scores"],
                                "threat_level": pose_analysis["threat_level"],
                                "threat_score": pose_analysis.get("threat_score", 0)
                            })
        
        # Draw overlays if requested
        if draw_overlay and annotated_frame is not None:
            annotated_frame = draw_detection_overlay(annotated_frame, results["detections"])
            
            # Encode annotated frame
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            results["frame_annotated"] = base64.b64encode(buffer).decode('utf-8')
        
        # Scene-level analysis
        results["scene_analysis"] = decision_engine.classify_overall_behavior(results["detections"])
        
    except Exception as e:
        logger.error(f"Frame processing error: {e}")
        results["error"] = str(e)
    
    return results

def draw_detection_overlay(frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
    """Draw bounding boxes, pose skeleton, and activity labels on frame"""
    
    # Colors (BGR)
    COLORS = {
        "safe": (0, 255, 0),      # Green
        "warning": (0, 165, 255),  # Orange
        "critical": (0, 0, 255),   # Red
        "skeleton": (255, 0, 255), # Magenta
        "label_bg": (40, 40, 40)   # Dark gray
    }
    
    SKELETON_CONNECTIONS = [
        (0, 1), (0, 2), (1, 3), (2, 4),  # Head
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
        (5, 11), (6, 12), (11, 12),  # Torso
        (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
    ]
    
    KEYPOINT_COLORS = [
        (255, 0, 128),   # Nose - Pink
        (255, 0, 128),   # Left Eye
        (255, 0, 128),   # Right Eye
        (255, 0, 128),   # Left Ear
        (255, 0, 128),   # Right Ear
        (255, 128, 0),   # Left Shoulder - Orange
        (255, 128, 0),   # Right Shoulder
        (0, 255, 128),   # Left Elbow - Green
        (0, 255, 128),   # Right Elbow
        (0, 255, 255),   # Left Wrist - Yellow
        (0, 255, 255),   # Right Wrist
        (255, 0, 0),     # Left Hip - Blue
        (255, 0, 0),     # Right Hip
        (128, 0, 255),   # Left Knee - Purple
        (128, 0, 255),   # Right Knee
        (255, 255, 0),   # Left Ankle - Cyan
        (255, 255, 0)    # Right Ankle
    ]
    
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        threat_level = det.get("threat_level", "safe")
        box_color = COLORS.get(threat_level, COLORS["safe"])
        
        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        
        # Draw pose skeleton
        keypoints = det.get("keypoints", [])
        if keypoints and len(keypoints) >= 17:
            # Draw keypoints
            for i, kpt in enumerate(keypoints[:17]):
                if len(kpt) >= 2:
                    px, py = int(kpt[0]), int(kpt[1])
                    conf = kpt[2] if len(kpt) > 2 else 1.0
                    if conf > 0.3 and px > 0 and py > 0:
                        color = KEYPOINT_COLORS[i] if i < len(KEYPOINT_COLORS) else (255, 255, 255)
                        cv2.circle(frame, (px, py), 4, color, -1)
            
            # Draw skeleton connections
            for conn in SKELETON_CONNECTIONS:
                if conn[0] < len(keypoints) and conn[1] < len(keypoints):
                    pt1 = keypoints[conn[0]]
                    pt2 = keypoints[conn[1]]
                    if len(pt1) >= 2 and len(pt2) >= 2:
                        x1_k, y1_k = int(pt1[0]), int(pt1[1])
                        x2_k, y2_k = int(pt2[0]), int(pt2[1])
                        conf1 = pt1[2] if len(pt1) > 2 else 1.0
                        conf2 = pt2[2] if len(pt2) > 2 else 1.0
                        if conf1 > 0.3 and conf2 > 0.3 and x1_k > 0 and y1_k > 0 and x2_k > 0 and y2_k > 0:
                            cv2.line(frame, (x1_k, y1_k), (x2_k, y2_k), COLORS["skeleton"], 2)
        
        # Draw activity labels
        label_y = y1 - 10
        activities = det.get("activities", [])
        scores = det.get("activity_scores", {})
        
        for activity in activities:
            score = scores.get(activity, 0)
            label = f"{activity.replace('_', ' ').title()}: {score*100:.1f}%"
            
            # Determine label color based on activity
            if activity in ["item_in_pocket", "concealment_posture"]:
                label_color = COLORS["critical"]
            elif activity == "walking":
                label_color = (255, 200, 0)  # Blue-ish
            else:
                label_color = COLORS["safe"]
            
            # Draw label background
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, label_y - text_h - 5), (x1 + text_w + 10, label_y + 5), label_color, -1)
            cv2.putText(frame, label, (x1 + 5, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            label_y -= (text_h + 12)
        
        # Draw threat indicator
        if threat_level != "safe":
            threat_label = f"THREAT: {threat_level.upper()}"
            cv2.putText(frame, threat_label, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
    
    # Draw scene status
    return frame

# ============================================
# ML DETECTION FUNCTIONS
# ============================================

def detect_persons_yolo(frame: np.ndarray) -> Dict[str, Any]:
    """
    Use YOLO to detect persons in frame
    Returns: dict with person count, bounding boxes, and tracking info
    """
    try:
        model = get_yolo_model()
        if model is None:
            return {"persons": [], "count": 0, "error": "YOLO model not loaded"}
        
        # Run inference
        results = model(frame, verbose=False, classes=[0])  # class 0 = person
        
        persons = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                
                # Calculate center and size
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                width = x2 - x1
                height = y2 - y1
                
                # Determine position in frame
                frame_h, frame_w = frame.shape[:2]
                position = "center"
                if center_x < frame_w * 0.33:
                    position = "left"
                elif center_x > frame_w * 0.66:
                    position = "right"
                
                # Calculate area ratio - convert numpy types to Python native
                area_ratio = float((width * height) / (frame_w * frame_h))
                
                persons.append({
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": round(float(confidence), 2),
                    "center": [int(center_x), int(center_y)],
                    "size": [int(width), int(height)],
                    "position": position,
                    "area_ratio": round(area_ratio, 4)
                })
        
        return {
            "persons": persons,
            "count": len(persons),
            "frame_size": [int(frame.shape[1]), int(frame.shape[0])]
        }
    except Exception as e:
        logger.error(f"YOLO detection error: {e}")
        return {"persons": [], "count": 0, "error": str(e)}

def detect_faces_deepface(frame: np.ndarray) -> List[Dict]:
    """
    Detect faces in frame using DeepFace
    Returns: list of detected faces with embeddings
    """
    try:
        from deepface import DeepFace
        
        # Detect faces
        faces = DeepFace.extract_faces(
            frame, 
            detector_backend='opencv',
            enforce_detection=False
        )
        
        detected_faces = []
        for face in faces:
            if face.get('confidence', 0) > 0.5:
                facial_area = face.get('facial_area', {})
                detected_faces.append({
                    "bbox": [
                        facial_area.get('x', 0),
                        facial_area.get('y', 0),
                        facial_area.get('x', 0) + facial_area.get('w', 0),
                        facial_area.get('y', 0) + facial_area.get('h', 0)
                    ],
                    "confidence": round(face.get('confidence', 0), 2)
                })
        
        return detected_faces
    except Exception as e:
        logger.error(f"DeepFace detection error: {e}")
        return []

async def compare_face_with_watchlist(frame: np.ndarray, watchlist_photos: List[Dict]) -> List[Dict]:
    """
    Compare detected faces against watchlist using DeepFace
    Returns: list of matches with person info and confidence
    """
    matches = []
    
    try:
        from deepface import DeepFace
        
        # Save frame temporarily
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            cv2.imwrite(tmp.name, frame)
            frame_path = tmp.name
        
        for person in watchlist_photos:
            try:
                # Decode watchlist photo
                photo_data = base64.b64decode(person['photo_base64'])
                photo_array = np.frombuffer(photo_data, np.uint8)
                watchlist_img = cv2.imdecode(photo_array, cv2.IMREAD_COLOR)
                
                if watchlist_img is None:
                    continue
                
                # Save watchlist photo temporarily
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp2:
                    cv2.imwrite(tmp2.name, watchlist_img)
                    watchlist_path = tmp2.name
                
                # Compare faces
                result = DeepFace.verify(
                    frame_path, 
                    watchlist_path,
                    model_name='VGG-Face',
                    enforce_detection=False
                )
                
                if result.get('verified', False):
                    matches.append({
                        "person_id": person['id'],
                        "person_name": person['name'],
                        "threat_level": person['threat_level'],
                        "confidence": round(1 - result.get('distance', 1), 2),
                        "match_type": "face_recognition"
                    })
                
                # Cleanup
                os.remove(watchlist_path)
                
            except Exception as e:
                logger.debug(f"Face comparison error for {person.get('name')}: {e}")
                continue
        
        # Cleanup
        os.remove(frame_path)
        
    except Exception as e:
        logger.error(f"Watchlist comparison error: {e}")
    
    return matches

def analyze_suspicious_behavior(persons: List[Dict], frame_history: List = None) -> Dict:
    """
    Analyze detected persons for suspicious behavior patterns
    Uses person positions, movements, and grouping
    """
    suspicious_indicators = []
    risk_score = 0.0
    
    if not persons:
        return {"indicators": [], "risk_score": 0.0, "behaviors": [], "person_count": 0}
    
    # Check for multiple persons (potential coordinated theft)
    if len(persons) >= 3:
        suspicious_indicators.append("multiple_persons_detected")
        risk_score += 0.2
    
    # Check for persons near edges (potential exit preparation)
    edge_persons = [p for p in persons if p.get('position') in ['left', 'right']]
    if edge_persons:
        suspicious_indicators.append("persons_near_exits")
        risk_score += 0.15
    
    # Check for large person detection (close to camera - potential concealment)
    large_persons = [p for p in persons if float(p.get('area_ratio', 0)) > 0.15]
    if large_persons:
        suspicious_indicators.append("close_proximity_detected")
        risk_score += 0.1
    
    # Detect clustering (group activity)
    if len(persons) >= 2:
        centers = [p.get('center', [0, 0]) for p in persons]
        for i, c1 in enumerate(centers):
            for j, c2 in enumerate(centers[i+1:], i+1):
                distance = float(np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2))
                if distance < 150:  # Close together
                    suspicious_indicators.append("group_clustering")
                    risk_score += 0.15
                    break
    
    behaviors = []
    if "multiple_persons_detected" in suspicious_indicators:
        behaviors.append("Coordinated group activity possible")
    if "persons_near_exits" in suspicious_indicators:
        behaviors.append("Persons positioned near exits")
    if "close_proximity_detected" in suspicious_indicators:
        behaviors.append("Close proximity to camera/merchandise")
    if "group_clustering" in suspicious_indicators:
        behaviors.append("Group clustering detected")
    
    return {
        "indicators": suspicious_indicators,
        "risk_score": float(min(risk_score, 1.0)),
        "behaviors": behaviors,
        "person_count": len(persons)
    }

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

async def analyze_frame_comprehensive(frame_base64: str, frame_idx: int, video_name: str, check_watchlist: bool = True) -> dict:
    """
    Comprehensive frame analysis using:
    1. YOLO - Person detection and tracking
    2. DeepFace - Face recognition against watchlist
    3. GPT-5.2 Vision - Behavior analysis
    """
    import json
    
    # Decode frame
    frame_data = base64.b64decode(frame_base64)
    frame_array = np.frombuffer(frame_data, np.uint8)
    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    
    results = {
        "frame_index": frame_idx,
        "analysis_methods": [],
        "is_suspicious": False,
        "severity": "safe",
        "confidence": 0.0,
        "description": "",
        "behaviors_detected": [],
        "reasoning": "",
        "ml_detections": {}
    }
    
    # 1. YOLO Person Detection
    try:
        yolo_results = detect_persons_yolo(frame)
        results["ml_detections"]["yolo"] = yolo_results
        results["analysis_methods"].append("YOLO")
        
        # Analyze behavior patterns from YOLO
        if yolo_results.get("count", 0) > 0:
            behavior_analysis = analyze_suspicious_behavior(yolo_results.get("persons", []))
            results["ml_detections"]["behavior_analysis"] = behavior_analysis
            
            if behavior_analysis.get("risk_score", 0) > 0.3:
                results["behaviors_detected"].extend(behavior_analysis.get("behaviors", []))
                results["confidence"] = max(results["confidence"], behavior_analysis.get("risk_score", 0))
    except Exception as e:
        logger.error(f"YOLO analysis error: {e}")
        results["ml_detections"]["yolo"] = {"error": str(e)}
    
    # 2. DeepFace Watchlist Check
    watchlist_matches = []
    if check_watchlist:
        try:
            # Get active watchlist
            watchlist = await db.watchlist.find(
                {"is_active": True}, 
                {"_id": 0, "id": 1, "name": 1, "photo_base64": 1, "threat_level": 1}
            ).to_list(20)
            
            if watchlist:
                watchlist_matches = await compare_face_with_watchlist(frame, watchlist)
                results["ml_detections"]["face_recognition"] = {
                    "matches": watchlist_matches,
                    "watchlist_checked": len(watchlist)
                }
                results["analysis_methods"].append("DeepFace")
                
                if watchlist_matches:
                    results["is_suspicious"] = True
                    results["severity"] = "critical"
                    results["confidence"] = max(results["confidence"], 0.9)
                    for match in watchlist_matches:
                        results["behaviors_detected"].append(
                            f"WATCHLIST MATCH: {match['person_name']} ({match['threat_level']} threat)"
                        )
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            results["ml_detections"]["face_recognition"] = {"error": str(e)}
    
    # 3. GPT-5.2 Vision Analysis
    try:
        gpt_result = await analyze_frame_with_gpt(frame_base64, frame_idx, video_name)
        results["ml_detections"]["gpt_vision"] = gpt_result
        results["analysis_methods"].append("GPT-5.2")
        
        # Merge GPT results
        if gpt_result.get("is_suspicious") or gpt_result.get("severity") in ["critical", "warning"]:
            results["is_suspicious"] = True
            if gpt_result.get("severity") == "critical":
                results["severity"] = "critical"
            elif results["severity"] != "critical":
                results["severity"] = gpt_result.get("severity", "warning")
        
        results["confidence"] = max(results["confidence"], gpt_result.get("confidence", 0))
        results["description"] = gpt_result.get("description", "")
        results["reasoning"] = gpt_result.get("reasoning", "")
        
        # Add GPT detected behaviors
        gpt_behaviors = gpt_result.get("behaviors_detected", [])
        for behavior in gpt_behaviors:
            if behavior not in results["behaviors_detected"]:
                results["behaviors_detected"].append(behavior)
                
    except Exception as e:
        logger.error(f"GPT analysis error: {e}")
        results["ml_detections"]["gpt_vision"] = {"error": str(e)}
    
    # Final severity determination
    if watchlist_matches:
        results["severity"] = "critical"
        results["description"] = f"WATCHLIST ALERT: {', '.join([m['person_name'] for m in watchlist_matches])} detected. " + results.get("description", "")
    
    return results

async def analyze_frame_with_gpt(frame_base64: str, frame_idx: int, video_name: str) -> dict:
    """Analyze a single frame using GPT-5.2 Vision for retail theft detection"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"analysis-{uuid.uuid4()}",
            system_message="""You are an advanced retail security AI specialized in detecting shoplifting, employee theft, and suspicious behavior in liquor stores, convenience stores, and gas stations.

## CUSTOMER THEFT DETECTION - Look for:

### Object Concealment Actions:
1. **Bag Concealment**: Customer placing items into personal bags, backpacks, purses, shopping bags from other stores
2. **Coat/Jacket Concealment**: Items being slipped into coat pockets, inside jacket, under coat
3. **Body Concealment**: Items tucked into waistband, under shirt, in pants, between body and arm
4. **Cart/Basket Switching**: Items moved to bottom of cart, hidden under other items

### Specific Items to Track (High-Value Retail):
- Liquor bottles, wine, spirits
- Beer, energy drinks
- Cigarettes, tobacco products, vapes
- Chocolates, candy bars
- Premium juices, beverages
- Electronics, batteries
- Cosmetics, personal care items
- Over-the-counter medicines

### Movement Patterns:
1. **Exit Direction**: Person moving towards exit after handling merchandise
2. **Checkout Avoidance**: Walking past registers without paying
3. **Quick Exit**: Rushing towards door after concealment
4. **Lookout Behavior**: Checking for staff/cameras while handling items

### Coordinated Theft Indicators:
- One person distracting staff while another conceals
- Group blocking camera views
- Passing items between people

## EMPLOYEE/STAFF THEFT DETECTION:

1. **Cash Theft**: Staff placing money in pocket, voiding transactions
2. **Product Theft**: Employees hiding items in personal belongings
3. **Sweethearting**: Not scanning items for friends/family
4. **Register Manipulation**: Suspicious cash handling

## RESPONSE FORMAT (JSON):
{
    "is_suspicious": true/false,
    "severity": "critical" | "warning" | "safe",
    "confidence": 0.0-1.0,
    "description": "Detailed description of what you observe",
    "person_description": "Physical description of suspect (clothing, appearance)",
    "items_involved": ["list of items being handled or concealed"],
    "concealment_method": "bag/coat/body/none",
    "movement_towards_exit": true/false,
    "behaviors_detected": ["specific actions observed"],
    "staff_theft_indicators": true/false,
    "reasoning": "Detailed explanation of why this is suspicious"
}

Be thorough but avoid false positives. Normal shopping behavior (picking up items, examining products, using shopping cart) is NOT suspicious unless combined with concealment actions."""
        ).with_model("openai", "gpt-5.2")

        image_content = ImageContent(image_base64=frame_base64)
        
        user_message = UserMessage(
            text=f"Analyze this security camera frame from {video_name}. Identify any shoplifting, concealment, staff theft, or suspicious activity. Track items being handled and any movement towards exits.",
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
async def analyze_video(video_id: str, max_frames: int = 8, use_ml: bool = True):
    """
    Analyze an uploaded video for shoplifting behavior
    Uses combined ML approach: YOLO + DeepFace + GPT-5.2 Vision
    """
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
            {"$set": {"status": "processing", "analysis_mode": "comprehensive" if use_ml else "gpt_only"}}
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
        ml_summary = {
            "yolo_detections": 0,
            "faces_detected": 0,
            "watchlist_matches": 0,
            "gpt_analyses": 0
        }
        
        # Analyze each frame
        for frame_idx, frame_base64, timestamp in frames_data:
            # Use comprehensive analysis with all ML models
            if use_ml:
                result = await analyze_frame_comprehensive(
                    frame_base64, 
                    frame_idx, 
                    video.get("filename", "video"),
                    check_watchlist=True
                )
                
                # Track ML usage
                ml_detections = result.get("ml_detections", {})
                if ml_detections.get("yolo", {}).get("count", 0) > 0:
                    ml_summary["yolo_detections"] += ml_detections["yolo"]["count"]
                if ml_detections.get("face_recognition", {}).get("matches"):
                    ml_summary["watchlist_matches"] += len(ml_detections["face_recognition"]["matches"])
                if "gpt_vision" in ml_detections:
                    ml_summary["gpt_analyses"] += 1
            else:
                result = await analyze_frame_with_gpt(frame_base64, frame_idx, video.get("filename", "video"))
                ml_summary["gpt_analyses"] += 1
            
            analyzed_count += 1
            
            # Update progress
            await db.videos.update_one(
                {"id": video_id},
                {"$set": {"analyzed_frames": analyzed_count}}
            )
            
            # If suspicious, create incident
            if result.get("is_suspicious") or result.get("severity") in ["critical", "warning"]:
                # Get GPT analysis details
                gpt_result = result.get("ml_detections", {}).get("gpt_vision", {})
                
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
                    # Store full frame image for incident display
                    "frame_image": frame_base64,
                    "behaviors_detected": result.get("behaviors_detected", []),
                    "reasoning": result.get("reasoning", ""),
                    "location": "Main Floor",
                    "store_type": video.get("store_type", "convenience"),
                    "analysis_methods": result.get("analysis_methods", ["GPT-5.2"]),
                    # Enhanced detection details
                    "person_description": gpt_result.get("person_description", ""),
                    "items_involved": gpt_result.get("items_involved", []),
                    "concealment_method": gpt_result.get("concealment_method", "none"),
                    "movement_towards_exit": gpt_result.get("movement_towards_exit", False),
                    "staff_theft": gpt_result.get("staff_theft_indicators", False),
                    # YOLO detection data
                    "persons_detected": result.get("ml_detections", {}).get("yolo", {}).get("count", 0),
                    "person_positions": result.get("ml_detections", {}).get("yolo", {}).get("persons", [])
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
                    "incidents_count": len(incidents),
                    "ml_summary": ml_summary
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
            "ml_summary": ml_summary,
            "analysis_methods": ["YOLO", "DeepFace", "GPT-5.2"] if use_ml else ["GPT-5.2"],
            "incidents": [
                {
                    "id": i["id"],
                    "severity": i["severity"],
                    "description": i["description"],
                    "confidence": i["confidence"],
                    "behaviors": i["behaviors_detected"],
                    "methods": i.get("analysis_methods", [])
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

@api_router.get("/ml/status")
async def get_ml_status():
    """Get status of all ML models"""
    status = {
        "yolo": {
            "loaded": yolo_model is not None,
            "model": "YOLOv8n",
            "purpose": "Person detection and tracking"
        },
        "yolo_pose": {
            "loaded": yolo_pose_model is not None,
            "model": "YOLOv8n-pose",
            "purpose": "Pose estimation and activity detection"
        },
        "deepface": {
            "initialized": deepface_initialized,
            "model": "VGG-Face",
            "purpose": "Face recognition for watchlist matching"
        },
        "gpt_vision": {
            "available": EMERGENT_LLM_KEY is not None,
            "model": "GPT-5.2 Vision",
            "purpose": "Behavior analysis and scene understanding"
        },
        "decision_engine": {
            "active": True,
            "purpose": "Real-time threat assessment"
        }
    }
    
    # Try to initialize models
    if not status["yolo"]["loaded"]:
        try:
            get_yolo_model()
            status["yolo"]["loaded"] = yolo_model is not None
        except:
            pass
    
    return status

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
    include_image: bool = False,
    limit: int = 50
):
    """Get all incidents with optional filtering"""
    query = {}
    if severity:
        query["severity"] = severity
    if store_type:
        query["store_type"] = store_type
    
    # Exclude large frame_image by default for list view
    projection = {"_id": 0}
    if not include_image:
        projection["frame_image"] = 0
    
    incidents = await db.incidents.find(query, projection).sort("timestamp", -1).to_list(limit)
    
    # Add has_image flag
    for incident in incidents:
        if not include_image:
            incident["has_image"] = await db.incidents.count_documents(
                {"id": incident["id"], "frame_image": {"$exists": True, "$ne": None}}
            ) > 0
    
    return {"incidents": incidents, "total": len(incidents)}

@api_router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get a specific incident with full details including frame image"""
    incident = await db.incidents.find_one({"id": incident_id}, {"_id": 0})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@api_router.get("/incidents/{incident_id}/image")
async def get_incident_image(incident_id: str):
    """Get just the frame image for an incident"""
    incident = await db.incidents.find_one(
        {"id": incident_id}, 
        {"_id": 0, "frame_image": 1}
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    frame_image = incident.get("frame_image")
    if not frame_image:
        raise HTTPException(status_code=404, detail="No image available for this incident")
    
    return {"image": frame_image}

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
# LIVE FEED ENDPOINTS
# ============================================

@api_router.post("/cameras")
async def add_camera(
    name: str = Form(...),
    source: str = Form(...),
    location: str = Form("Main Floor"),
    store_type: str = Form("convenience")
):
    """Add a new camera feed"""
    camera_id = str(uuid.uuid4())
    camera_doc = {
        "id": camera_id,
        "name": name,
        "source": source,
        "location": location,
        "store_type": store_type,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_frame_at": None,
        "status": "inactive"
    }
    
    await db.cameras.insert_one(camera_doc)
    
    return {
        "id": camera_id,
        "name": name,
        "source": source,
        "message": "Camera added successfully"
    }

@api_router.get("/cameras")
async def list_cameras():
    """List all camera feeds"""
    cameras = await db.cameras.find({}, {"_id": 0}).to_list(50)
    return {"cameras": cameras, "total": len(cameras)}

@api_router.get("/cameras/{camera_id}")
async def get_camera(camera_id: str):
    """Get a specific camera"""
    camera = await db.cameras.find_one({"id": camera_id}, {"_id": 0})
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@api_router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    """Delete a camera feed"""
    result = await db.cameras.delete_one({"id": camera_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Remove from live feeds if active
    if camera_id in live_feeds:
        del live_feeds[camera_id]
    
    return {"message": "Camera deleted"}

@api_router.post("/live/process-frame")
async def process_live_frame(
    frame: UploadFile = File(...),
    camera_id: Optional[str] = Form(None),
    draw_overlay: bool = Form(True)
):
    """Process a single frame from live feed with real-time detection"""
    try:
        # Read frame
        content = await frame.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        # Process frame with detection
        result = process_frame_with_detection(img, draw_overlay=draw_overlay)
        
        # Store in live feed state
        if camera_id:
            live_feeds[camera_id] = {
                "last_result": result,
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            await db.cameras.update_one(
                {"id": camera_id},
                {"$set": {"last_frame_at": datetime.now(timezone.utc).isoformat(), "status": "active"}}
            )
        
        # Create incident if critical threat detected
        if result.get("scene_analysis", {}).get("scene_status") == "critical":
            for det in result.get("detections", []):
                if det.get("threat_level") == "critical":
                    incident = {
                        "id": str(uuid.uuid4()),
                        "video_id": camera_id or "live_feed",
                        "video_name": f"Live Feed - {camera_id or 'Unknown'}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "severity": "critical",
                        "description": f"Live detection: {', '.join(det.get('activities', []))}",
                        "confidence": det.get("threat_score", 0.8),
                        "frame_index": 0,
                        "frame_time_seconds": 0,
                        "frame_image": result.get("frame_annotated"),
                        "behaviors_detected": det.get("activities", []),
                        "reasoning": "Real-time threat detection by Decision Engine",
                        "location": "Live Camera",
                        "store_type": "convenience",
                        "analysis_methods": ["YOLO", "Pose Estimation", "Decision Engine"],
                        "persons_detected": len(result.get("detections", [])),
                        "concealment_method": "body" if "item_in_pocket" in det.get("activities", []) else "none",
                        "staff_theft": False,
                        "movement_towards_exit": det.get("position") in ["left_edge", "right_edge"]
                    }
                    await db.incidents.insert_one(incident)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live frame processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/live/process-video-frame")
async def process_video_frame(video_id: str, frame_number: int = 0):
    """Process a specific frame from an uploaded video with live detection overlay"""
    try:
        video = await db.videos.find_one({"id": video_id}, {"_id": 0})
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        tmp_path = video.get("temp_path")
        if not tmp_path or not os.path.exists(tmp_path):
            raise HTTPException(status_code=400, detail="Video file not found")
        
        # Open video and get frame
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_number >= total_frames:
            frame_number = total_frames - 1
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise HTTPException(status_code=400, detail="Could not read frame")
        
        # Process frame
        result = process_frame_with_detection(frame, draw_overlay=True)
        result["frame_number"] = frame_number
        result["total_frames"] = total_frames
        result["video_id"] = video_id
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video frame processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/live/feed/{camera_id}")
async def get_live_feed_status(camera_id: str):
    """Get the latest detection results for a camera feed"""
    if camera_id not in live_feeds:
        return {"status": "inactive", "message": "No active feed for this camera"}
    
    return {
        "status": "active",
        **live_feeds[camera_id]
    }

@api_router.get("/live/demo-frame")
async def get_demo_frame():
    """Generate a demo frame with simulated detection for testing"""
    # Create a demo frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40)  # Dark gray background
    
    # Add some rectangles to simulate a store
    cv2.rectangle(frame, (50, 100), (200, 400), (60, 60, 60), -1)  # Shelf 1
    cv2.rectangle(frame, (250, 100), (400, 400), (60, 60, 60), -1)  # Shelf 2
    cv2.rectangle(frame, (450, 100), (600, 400), (60, 60, 60), -1)  # Shelf 3
    
    # Add text
    cv2.putText(frame, "DEMO FEED - Connect camera for real detection", 
                (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
    
    # Encode frame
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    frame_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return {
        "frame_annotated": frame_base64,
        "detections": [],
        "scene_analysis": {
            "total_persons": 0,
            "suspicious_count": 0,
            "scene_status": "normal",
            "activities_summary": {}
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_demo": True
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
