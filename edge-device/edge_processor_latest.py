"""
SecureGuard Edge Device Processor
Handles RTSP camera streams, ML detection, and incident reporting

Features:
- Multi-camera RTSP stream processing
- YOLO v8 person detection
- Pose estimation for suspicious behavior
- Face recognition against watchlist
- GPT-5.2 Vision for advanced analysis
- Automatic incident creation and upload
- Periodic frame snapshots for live view
- Stream health monitoring

Patch changelog (all 16 bugs fixed):
  LOGIC FIXES
  1.  rate_limited returns neutral sentinel instead of is_shoplifting=False
  2.  Pose-detected suspicion now fires incidents when GPT is enabled (was dead code)
  3.  Pose status filter updated to match values _analyze_pose() actually returns
  4.  Suspicious frame reset window increased from 5s → SUSPICIOUS_RESET_WINDOW (default 30s)
  5.  last_analysis_time updated before API call to prevent tight retry loop on exception
  6.  Reconnect delay now uses max(attempts, 1) to avoid zero-delay on first attempt
  7.  Crouching check fixed — was testing Y-coords backwards relative to image coordinate system
  8.  Watchlist confidence clamped to [0.0, 1.0]
  9.  sync_pending_incidents() implemented (was a stub pass)

  CODE FIXES
  10. MAX_DECODE_ERRORS now reads from env (was hardcoded, ignoring .env)
  11. SYNC/HEARTBEAT interval env vars support legacy typo spelling as fallback
  12. asyncio.get_event_loop() → asyncio.get_running_loop() (deprecated in Python 3.10+)
  13. Unused Tuple import removed
  14. threading.Lock now actually used in read_frame() for thread safety
  15. Frame read exceptions logged at DEBUG level instead of silently swallowed
  17. Ollama timeout increased 30s → 60s for Orin Nano edge hardware
  18. JPEG quality reduced 60 → 30 for faster Ollama processing on edge hardware
  19. Prompt tightened to force JSON-only response (no extra text)
  20. _parse_response() uses brace-matching extractor — handles extra text before/after JSON
  21. Incident thumbnail resized to max 640x480 + quality 40 to fix 413 payload too large
"""

import os
import sys
import cv2
import json
import time
import uuid
import base64
import asyncio
import logging
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque
import threading

import httpx
from tinydb import TinyDB, Query
from dotenv import load_dotenv

load_dotenv()

# Configuration
CENTRAL_SERVER_URL = os.environ.get("CENTRAL_SERVER_URL", "http://localhost:8001")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
API_KEY = os.environ.get("API_KEY", "")
DEVICE_NAME = os.environ.get("DEVICE_NAME", "Edge-Device-001")

# AI Provider Selection: "ollama" (free/local) or "emergent" (cloud API)
AI_PROVIDER = os.environ.get("AI_PROVIDER", "ollama").lower()
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Ollama Configuration (FREE local AI)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "moondream")  # lightweight vision model for edge devices

# Processing settings
DETECTION_INTERVAL = float(os.environ.get("DETECTION_INTERVAL", "0.5"))
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.5"))
ENABLE_POSE = os.environ.get("ENABLE_POSE_DETECTION", "true").lower() == "true"
ENABLE_FACE = os.environ.get("ENABLE_FACE_RECOGNITION", "false").lower() == "true"
ENABLE_GPT = os.environ.get("ENABLE_GPT_ANALYSIS", "true").lower() == "true"

# Shoplifting detection
INCIDENT_COOLDOWN = int(os.environ.get("INCIDENT_COOLDOWN_SECONDS", "60"))
GPT_ANALYSIS_INTERVAL = float(os.environ.get("GPT_ANALYSIS_INTERVAL", "2"))
MIN_SUSPICIOUS_FRAMES = int(os.environ.get("MIN_SUSPICIOUS_FRAMES", "3"))
SUSPICIOUS_RESET_WINDOW = int(os.environ.get("SUSPICIOUS_RESET_WINDOW", "30"))  # seconds before suspicious frame counter resets
REQUIRE_GPT_CONFIRMATION = os.environ.get("REQUIRE_GPT_CONFIRMATION", "true").lower() == "true"

# Streaming settings — support both correct spelling and legacy typo ("INTERNAL" vs "INTERVAL")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_SECONDS",
    os.environ.get("SYNC_INTERNAL_SECONDS", "60")))
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL_SECONDS",
    os.environ.get("HEARTBEAT_INTERNAL_SECONDS", "60")))
SNAPSHOT_INTERVAL = float(os.environ.get("SNAPSHOT_INTERVAL_SECONDS", "180"))

# RTSP Stability
MAX_RECONNECT_ATTEMPTS = int(os.environ.get("MAX_RECONNECT_ATTEMPTS", "9999"))
RECONNECT_DELAY = int(os.environ.get("RECONNECT_DELAY_SECONDS", "60"))
MAX_DECODE_ERRORS = int(os.environ.get("MAX_DECODE_ERRORS", "999999999"))

# Track AI model status (for admin console)
ai_model_status = {
    "yolo": {"enabled": True, "loaded": False, "status": "not_loaded"},
    "pose": {"enabled": ENABLE_POSE, "loaded": False, "status": "not_loaded"},
    "deepface": {"enabled": ENABLE_FACE, "loaded": False, "status": "not_loaded"},
    "vision_ai": {"enabled": ENABLE_GPT, "loaded": False, "status": "not_loaded", "provider": AI_PROVIDER}
}

# Logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EdgeDevice")
logger.setLevel(logging.INFO)

# Local database for offline cache
db_path = Path("./data")
db_path.mkdir(exist_ok=True)
local_db = TinyDB(db_path / "incidents.json")
config_db = TinyDB(db_path / "config.json")
snapshot_db = TinyDB(db_path / "snapshots.json")

# ML Models (lazy loaded)
yolo_model = None
pose_model = None
deepface_initialized = False


class StreamHealth:
    """Tracks health metrics for a camera stream"""
    
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.is_connected = False
        self.frames_received = 0
        self.frames_processed = 0
        self.frames_dropped = 0
        self.decode_errors = 0
        self.last_frame_time = None
        self.reconnect_count = 0
        self.fps = 0.0
        self.fps_history = deque(maxlen=30)
        self.last_fps_calc = time.time()
        
    def record_frame(self):
        self.frames_received += 1
        now = time.time()
        self.fps_history.append(now)
        self.last_frame_time = now
        
        # Calculate FPS every second
        if now - self.last_fps_calc >= 1.0:
            recent = [t for t in self.fps_history if now - t <= 1.0]
            self.fps = len(recent)
            self.last_fps_calc = now
    
    def record_error(self):
        self.decode_errors += 1
        self.frames_dropped += 1
        
    def record_reconnect(self):
        self.reconnect_count += 1
        
    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "is_connected": self.is_connected,
            "frames_received": self.frames_received,
            "frames_processed": self.frames_processed,
            "frames_dropped": self.frames_dropped,
            "decode_errors": self.decode_errors,
            "reconnect_count": self.reconnect_count,
            "fps": round(self.fps, 1),
            "last_frame_time": self.last_frame_time
        }


class CameraStream:
    """Manages RTSP camera connection with robust error handling"""
    
    def __init__(self, camera_id: str, rtsp_url: str, name: str = "Camera"):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.name = name
        self.cap = None
        self.is_running = False
        self.last_frame = None
        self.last_frame_time = None
        self.health = StreamHealth(camera_id)
        self.reconnect_attempts = 0
        self.lock = threading.Lock()
        
    def connect(self) -> bool:
        """Connect to RTSP stream with error handling"""
        try:
            # Release existing connection first
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            
            logger.info(f"Connecting to camera: {self.name} ({self.rtsp_url})")
            
            # Set RTSP transport options for better reliability
            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|buffer_size;1024000|stimeout;5000000'
            
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            
            # Set timeouts
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
            
            if self.cap.isOpened():
                # Read a test frame
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    logger.info(f"✅ Connected to camera: {self.name}")
                    self.is_running = True
                    self.health.is_connected = True
                    self.reconnect_attempts = 0
                    self.last_frame = frame
                    self.last_frame_time = time.time()
                    self.health.decode_errors = 0  # Reset errors on successful connect
                    return True
                else:
                    logger.warning(f"Camera opened but no frame: {self.name}")
            
            logger.error(f"❌ Failed to connect: {self.name}")
            self.health.is_connected = False
            return False
            
        except Exception as e:
            logger.error(f"Camera connection error ({self.name}): {e}")
            self.health.is_connected = False
            return False
    
    def schedule_reconnect(self):
        """Schedule a reconnection (non-blocking)"""
        if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Max reconnect attempts reached for {self.name}")
            return
        
        self.reconnect_attempts += 1
        self.health.record_reconnect()
        self.is_running = False
        self.health.is_connected = False
        
        # Release current connection
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        
        logger.info(f"Will reconnect to {self.name} (attempt {self.reconnect_attempts})")
    
    def try_reconnect(self) -> bool:
        """Try to reconnect if scheduled"""
        if self.is_running:
            return True  # Already connected
        
        # Simple delay based on attempt count — minimum 1 to avoid zero delay on first attempt
        delay = min(RECONNECT_DELAY * max(self.reconnect_attempts, 1), 120)
        
        # Check if enough time has passed since last attempt
        if not hasattr(self, '_last_reconnect_time'):
            self._last_reconnect_time = 0
        
        if time.time() - self._last_reconnect_time < delay:
            return False  # Wait more
        
        self._last_reconnect_time = time.time()
        logger.info(f"Attempting reconnect to {self.name}...")
        return self.connect()
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Read single frame - NEVER reconnect due to decode errors"""
        # If not running, try to reconnect (non-blocking)
        if not self.is_running:
            self.try_reconnect()
            return self.last_frame
        
        if not self.cap or not self.cap.isOpened():
            self.schedule_reconnect()
            return self.last_frame
        
        try:
            with self.lock:
                ret, frame = self.cap.read()
            
            if ret and frame is not None:
                # Validate frame
                if frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
                    return self.last_frame  # Just use last frame
                
                self.last_frame = frame
                self.last_frame_time = time.time()
                self.health.record_frame()
                self.health.frames_processed += 1
                return frame
            else:
                # Frame read failed - just use last frame, DON'T reconnect
                # Decode errors are NORMAL for RTSP streams
                return self.last_frame
                
        except Exception as e:
            self.health.record_error()
            logger.debug(f"Frame read error on {self.name}: {e}")
            return self.last_frame
    
    def get_snapshot(self) -> Optional[str]:
        """Get current frame as base64 JPEG"""
        frame = self.last_frame
        if frame is None:
            return None
        
        try:
            # Resize for snapshot (reduce bandwidth)
            h, w = frame.shape[:2]
            scale = min(640 / w, 480 / h, 1.0)
            if scale < 1.0:
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
            
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
            return None
    
    def release(self):
        """Release camera connection"""
        self.is_running = False
        self.health.is_connected = False
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None


class MLDetector:
    """Handles all ML detection tasks"""
    
    def __init__(self):
        self.yolo_model = None
        self.pose_model = None
        self.deepface_initialized = False
        self.watchlist_encodings = []
        
    def initialize(self):
        """Initialize ML models and update status"""
        global ai_model_status
        logger.info("Initializing ML models...")
        
        # YOLO for person detection (always required)
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO("yolov8n.pt")
            ai_model_status["yolo"]["loaded"] = True
            ai_model_status["yolo"]["status"] = "connected"
            logger.info("✅ YOLO model loaded")
        except Exception as e:
            ai_model_status["yolo"]["status"] = f"error: {str(e)[:50]}"
            logger.error(f"Failed to load YOLO: {e}")
        
        # Pose estimation
        if ENABLE_POSE:
            try:
                from ultralytics import YOLO
                self.pose_model = YOLO("yolov8n-pose.pt")
                ai_model_status["pose"]["loaded"] = True
                ai_model_status["pose"]["status"] = "connected"
                logger.info("✅ Pose model loaded")
            except Exception as e:
                ai_model_status["pose"]["status"] = f"error: {str(e)[:50]}"
                logger.error(f"Failed to load pose model: {e}")
        else:
            ai_model_status["pose"]["status"] = "disabled"
        
        # DeepFace for face recognition
        if ENABLE_FACE:
            try:
                from deepface import DeepFace
                # Warm up the model
                test_img = np.zeros((100, 100, 3), dtype=np.uint8)
                try:
                    DeepFace.represent(test_img, enforce_detection=False)
                except:
                    pass
                self.deepface_initialized = True
                ai_model_status["deepface"]["loaded"] = True
                ai_model_status["deepface"]["status"] = "connected"
                logger.info("✅ DeepFace initialized")
            except Exception as e:
                ai_model_status["deepface"]["status"] = f"error: {str(e)[:50]}"
                logger.error(f"Failed to initialize DeepFace: {e}")
        else:
            ai_model_status["deepface"]["status"] = "disabled"
    
    def detect_persons(self, frame: np.ndarray) -> List[Dict]:
        """Detect persons in frame using YOLO"""
        if self.yolo_model is None:
            return []
        
        try:
            results = self.yolo_model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)
            detections = []
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    if cls == 0:  # Person class
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = float(box.conf[0])
                        detections.append({
                            "bbox": [int(x1), int(y1), int(x2), int(y2)],
                            "confidence": conf,
                            "class": "person"
                        })
            
            return detections
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def detect_poses(self, frame: np.ndarray) -> List[Dict]:
        """Detect poses for behavior analysis"""
        if self.pose_model is None or not ENABLE_POSE:
            return []
        
        try:
            results = self.pose_model(frame, verbose=False)
            poses = []
            
            for r in results:
                if r.keypoints is not None:
                    for kp in r.keypoints:
                        keypoints = kp.xy[0].tolist() if kp.xy is not None else []
                        
                        # Analyze pose for suspicious behavior
                        pose_status = self._analyze_pose(keypoints)
                        poses.append({
                            "keypoints": keypoints,
                            "pose_status": pose_status
                        })
            
            return poses
        except Exception as e:
            logger.error(f"Pose detection error: {e}")
            return []
    
    def _analyze_pose(self, keypoints: List) -> str:
        """Analyze pose keypoints for suspicious behavior - MORE SENSITIVE"""
        if len(keypoints) < 17:
            return "unknown"
        
        try:
            # COCO keypoint indices
            # 0: nose, 5: left_shoulder, 6: right_shoulder, 
            # 9: left_wrist, 10: right_wrist, 11: left_hip, 12: right_hip
            # 15: left_ankle, 16: right_ankle
            
            nose = keypoints[0] if len(keypoints) > 0 else [0, 0]
            left_shoulder = keypoints[5] if len(keypoints) > 5 else [0, 0]
            right_shoulder = keypoints[6] if len(keypoints) > 6 else [0, 0]
            left_wrist = keypoints[9] if len(keypoints) > 9 else [0, 0]
            right_wrist = keypoints[10] if len(keypoints) > 10 else [0, 0]
            left_hip = keypoints[11] if len(keypoints) > 11 else [0, 0]
            right_hip = keypoints[12] if len(keypoints) > 12 else [0, 0]
            
            suspicious_behaviors = []
            
            # Calculate body metrics
            waist_y = (left_hip[1] + right_hip[1]) / 2 if left_hip[1] > 0 and right_hip[1] > 0 else 0
            shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2 if left_shoulder[1] > 0 and right_shoulder[1] > 0 else 0
            torso_height = waist_y - shoulder_y if waist_y > 0 and shoulder_y > 0 else 100
            
            # 1. Check for concealment behavior (hands near waist/pockets) - VERY COMMON
            if waist_y > 0:
                threshold = max(80, torso_height * 0.4)  # Larger threshold
                left_near_waist = abs(left_wrist[1] - waist_y) < threshold if left_wrist[1] > 0 else False
                right_near_waist = abs(right_wrist[1] - waist_y) < threshold if right_wrist[1] > 0 else False
                
                if left_near_waist or right_near_waist:
                    suspicious_behaviors.append("hands_near_waist")
            
            # 2. Check for bent/crouching posture (torso compression)
            # In image coords Y increases downward: nose_y < waist_y for upright person.
            # When crouching, nose approaches waist level — gap shrinks relative to torso height.
            if torso_height > 0 and nose[1] > 0 and waist_y > 0:
                if (waist_y - nose[1]) < torso_height * 0.5:
                    suspicious_behaviors.append("crouching")
            
            # 3. Check for looking around behavior (head turned away from body)
            if nose[0] > 0 and shoulder_y > 0:
                body_center_x = (left_shoulder[0] + right_shoulder[0]) / 2 if left_shoulder[0] > 0 and right_shoulder[0] > 0 else nose[0]
                head_offset = abs(nose[0] - body_center_x)
                shoulder_width = abs(left_shoulder[0] - right_shoulder[0]) if left_shoulder[0] > 0 and right_shoulder[0] > 0 else 100
                
                if head_offset > shoulder_width * 0.5:
                    suspicious_behaviors.append("looking_around")
            
            # 4. Check for arms extended (grabbing items)
            if left_shoulder[0] > 0 and left_wrist[0] > 0:
                shoulder_width = abs(left_shoulder[0] - right_shoulder[0]) if right_shoulder[0] > 0 else 100
                arm_threshold = max(150, shoulder_width * 1.2)
                if abs(left_wrist[0] - left_shoulder[0]) > arm_threshold:
                    suspicious_behaviors.append("left_arm_extended")
            
            if right_shoulder[0] > 0 and right_wrist[0] > 0:
                shoulder_width = abs(left_shoulder[0] - right_shoulder[0]) if left_shoulder[0] > 0 else 100
                arm_threshold = max(150, shoulder_width * 1.2)
                if abs(right_wrist[0] - right_shoulder[0]) > arm_threshold:
                    suspicious_behaviors.append("right_arm_extended")
            
            # 5. Hands above head (unusual)
            if shoulder_y > 0:
                if (left_wrist[1] > 0 and left_wrist[1] < shoulder_y - 50) or \
                   (right_wrist[1] > 0 and right_wrist[1] < shoulder_y - 50):
                    suspicious_behaviors.append("hands_raised")
            
            # Return most suspicious behavior found
            if "crouching" in suspicious_behaviors:
                return "crouching"
            elif "hands_near_waist" in suspicious_behaviors:
                return "suspicious_hands"
            elif "looking_around" in suspicious_behaviors:
                return "looking_around"
            elif "left_arm_extended" in suspicious_behaviors or "right_arm_extended" in suspicious_behaviors:
                return "reaching"
            elif suspicious_behaviors:
                return suspicious_behaviors[0]
            
            return "normal"
        except Exception as e:
            logger.error(f"Pose analysis error: {e}")
            return "unknown"
    
    def check_watchlist(self, frame: np.ndarray, bbox: List[int]) -> Optional[Dict]:
        """Check if detected person matches watchlist"""
        if not ENABLE_FACE or not self.deepface_initialized:
            return None
        
        if not self.watchlist_encodings:
            return None
        
        try:
            from deepface import DeepFace
            
            x1, y1, x2, y2 = bbox
            # Expand bbox for better face detection
            margin = 20
            x1 = max(0, x1 - margin)
            y1 = max(0, y1 - margin)
            x2 = min(frame.shape[1], x2 + margin)
            y2 = min(frame.shape[0], y2 + margin)
            
            face_img = frame[y1:y2, x1:x2]
            
            if face_img.size == 0:
                return None
            
            # Get face embedding
            embedding = DeepFace.represent(face_img, model_name="Facenet", enforce_detection=False)
            
            if embedding:
                # Compare with watchlist
                for person in self.watchlist_encodings:
                    distance = np.linalg.norm(
                        np.array(embedding[0]["embedding"]) - np.array(person["encoding"])
                    )
                    if distance < 0.6:  # Threshold for match
                        return {
                            "person_id": person["person_id"],
                            "name": person["name"],
                            "confidence": max(0.0, min(1.0, 1 - (distance / 0.6)))
                        }
            
            return None
        except Exception as e:
            # Face detection failures are common, don't log as error
            return None
    
    def set_watchlist(self, watchlist: List[Dict]):
        """Update watchlist encodings"""
        self.watchlist_encodings = []
        for person in watchlist:
            if "face_encoding" in person:
                self.watchlist_encodings.append({
                    "person_id": person.get("person_id"),
                    "name": person.get("name"),
                    "encoding": person["face_encoding"]
                })
        logger.info(f"Loaded {len(self.watchlist_encodings)} watchlist entries")


class VisionAnalyzer:
    """Vision AI analysis - supports Ollama (free/local) or Emergent (cloud)"""
    
    def __init__(self):
        global ai_model_status
        self.last_analysis_time = 0
        self.min_analysis_interval = GPT_ANALYSIS_INTERVAL
        self.provider = AI_PROVIDER
        
        # Check if vision AI is enabled and configured
        if AI_PROVIDER == "ollama":
            self.enabled = ENABLE_GPT
            self._test_ollama_connection()
        else:  # emergent
            self.enabled = ENABLE_GPT and EMERGENT_LLM_KEY
            if self.enabled:
                ai_model_status["vision_ai"]["loaded"] = True
                ai_model_status["vision_ai"]["status"] = "connected"
                ai_model_status["vision_ai"]["provider"] = "emergent"
            else:
                ai_model_status["vision_ai"]["status"] = "no_api_key"
    
    def _test_ollama_connection(self):
        """Test connection to Ollama server"""
        global ai_model_status
        
        # Vision-capable models in Ollama
        VISION_MODELS = ["llava", "bakllava", "llava-llama3", "moondream", "cogvlm", "llama3.2-vision", "minicpm-v"]
        
        # Warn if using a non-vision model
        is_vision_model = any(vm in OLLAMA_MODEL.lower() for vm in VISION_MODELS)
        if not is_vision_model:
            logger.warning(f"⚠️ Model '{OLLAMA_MODEL}' may not support images. For vision analysis, use: llava, bakllava, or llava-llama3")
        
        try:
            import requests
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(OLLAMA_MODEL in name for name in model_names):
                    ai_model_status["vision_ai"]["loaded"] = True
                    ai_model_status["vision_ai"]["status"] = "connected"
                    ai_model_status["vision_ai"]["provider"] = f"ollama ({OLLAMA_MODEL})"
                    if is_vision_model:
                        logger.info(f"✅ Ollama connected - vision model: {OLLAMA_MODEL}")
                    else:
                        logger.warning(f"⚠️ Ollama connected - model: {OLLAMA_MODEL} (NOT a vision model)")
                        ai_model_status["vision_ai"]["status"] = "connected (text-only)"
                else:
                    ai_model_status["vision_ai"]["status"] = f"model {OLLAMA_MODEL} not found"
                    logger.warning(f"Ollama connected but model '{OLLAMA_MODEL}' not found. Available: {model_names}")
            else:
                ai_model_status["vision_ai"]["status"] = "connection_failed"
        except Exception as e:
            ai_model_status["vision_ai"]["status"] = f"error: {str(e)[:30]}"
            logger.error(f"Ollama connection failed: {e}")
    
    async def analyze_scene(self, frame: np.ndarray, detections: List[Dict]) -> Dict:
        """Analyze scene for shoplifting using Ollama or Emergent"""
        if not self.enabled:
            return {"analyzed": False, "threat_level": "safe", "is_shoplifting": False}
        
        # Rate limit — return a neutral skip sentinel, NOT is_shoplifting=False
        # (returning false would treat this frame as confirmed safe)
        now = time.time()
        if now - self.last_analysis_time < self.min_analysis_interval:
            return {"analyzed": False, "skipped": True, "is_shoplifting": None, "reason": "rate_limited"}
        
        logger.info(f"🔍 Running {self.provider} analysis ({len(detections)} people)...")
        
        # Update timestamp before the call — prevents tight retry loop if the call throws
        self.last_analysis_time = now

        # Lower JPEG quality = smaller image = faster analysis on edge hardware
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        prompt = f"""You are a security camera AI. Analyze this image for shoplifting.
People visible: {len(detections)}

Respond with ONLY a single JSON object. No explanation, no extra text, nothing before or after the JSON.

If shoplifting: {{"is_shoplifting": true, "confidence": 0.9, "description": "brief description"}}
If safe: {{"is_shoplifting": false, "confidence": 0.1, "description": "brief description"}}"""

        try:
            if self.provider == "ollama":
                result = await self._analyze_with_ollama(img_base64, prompt)
            else:
                result = await self._analyze_with_emergent(img_base64, prompt)
            
            return result
            
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return {"analyzed": False, "threat_level": "safe", "is_shoplifting": False, "error": str(e)}
    
    async def _analyze_with_ollama(self, img_base64: str, prompt: str) -> Dict:
        """Use Ollama for local vision analysis (FREE)"""
        import requests
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "images": [img_base64],
                    "stream": False
                },
                timeout=60
            )
        )
        
        if response.status_code == 200:
            content = response.json().get("response", "")
            return self._parse_response(content)
        else:
            logger.error(f"Ollama error: {response.status_code}")
            return {"analyzed": False, "threat_level": "safe", "is_shoplifting": False}
    
    async def _analyze_with_emergent(self, img_base64: str, prompt: str) -> Dict:
        """Use Emergent LLM for cloud vision analysis"""
        from emergentintegrations.llm.openai import chat_completion_with_image
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: chat_completion_with_image(
                api_key=EMERGENT_LLM_KEY,
                image=img_base64,
                prompt=prompt,
                model="gpt-5.2"
            )
        )
        
        if response and response.content:
            return self._parse_response(response.content)
        
        return {"analyzed": False, "threat_level": "safe", "is_shoplifting": False}
    
    def _parse_response(self, content: str) -> Dict:
        """Parse JSON response from vision AI — robust brace-matching extractor"""
        try:
            content = content.strip()

            if "{" not in content:
                logger.warning(f"No JSON found in response: {content[:100]}")
                return {"analyzed": False, "threat_level": "safe", "is_shoplifting": False}

            # Extract the FIRST complete JSON object using brace matching.
            # This handles models that add extra text before/after the JSON,
            # or return multiple JSON blocks — we only want the first one.
            start = content.find("{")
            depth = 0
            end = start
            for i, ch in enumerate(content[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            json_str = content[start:end]
            result = json.loads(json_str)

            is_shoplifting = bool(result.get("is_shoplifting", False))
            description = result.get("description", "")
            confidence = float(result.get("confidence", 0.5))

            if is_shoplifting:
                logger.warning(f"🚨 SHOPLIFTING DETECTED: {description} (conf: {confidence})")
            else:
                logger.info(f"👁️ Analysis: {description[:60]} (safe)")

            return {
                "analyzed": True,
                "threat_level": "critical" if is_shoplifting else "safe",
                "confidence": confidence,
                "description": description,
                "behaviors_detected": result.get("evidence", []),
                "is_shoplifting": is_shoplifting
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}\nRaw: {content[:200]}")

        return {"analyzed": False, "threat_level": "safe", "is_shoplifting": False}


class CentralServerSync:
    """Handles communication with central server"""
    
    def __init__(self, server_url: str, client_id: str, api_key: str):
        self.server_url = server_url.rstrip('/')
        self.client_id = client_id
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def get_config(self) -> Optional[Dict]:
        """Fetch configuration from central server"""
        try:
            response = await self.http_client.get(
                f"{self.server_url}/api/edge/config/{self.client_id}",
                params={"api_key": self.api_key}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Config fetch failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Config fetch error: {e}")
            return None
    
    async def register(self, device_name: str, device_ip: str) -> bool:
        """Register edge device with central server"""
        try:
            response = await self.http_client.post(
                f"{self.server_url}/api/edge/register",
                json={
                    "client_id": self.client_id,
                    "api_key": self.api_key,
                    "device_name": device_name,
                    "device_ip": device_ip
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False
    
    async def send_heartbeat(self, cameras_online: int, cameras_total: int, 
                            stream_health: List[Dict] = None) -> bool:
        """Send heartbeat with health data and AI model status"""
        global ai_model_status
        try:
            response = await self.http_client.post(
                f"{self.server_url}/api/edge/heartbeat",
                json={
                    "client_id": self.client_id,
                    "api_key": self.api_key,
                    "cameras_online": cameras_online,
                    "cameras_total": cameras_total,
                    "device_name": DEVICE_NAME,
                    "stream_health": stream_health or [],
                    "ai_model_status": ai_model_status,  # Send AI status to server
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False
    
    async def upload_incident(self, incident: Dict) -> bool:
        """Upload incident to central server"""
        try:
            response = await self.http_client.post(
                f"{self.server_url}/api/edge/incidents",
                json={
                    "client_id": self.client_id,
                    "api_key": self.api_key,
                    **incident
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Incident uploaded: {incident['incident_id']}")
                return True
            else:
                logger.error(f"Incident upload failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Incident upload error: {e}")
            return False
    
    async def upload_snapshots(self, snapshots: List[Dict]) -> bool:
        """Upload camera snapshots for live view"""
        try:
            response = await self.http_client.post(
                f"{self.server_url}/api/edge/snapshots",
                json={
                    "client_id": self.client_id,
                    "api_key": self.api_key,
                    "snapshots": snapshots,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Snapshot upload error: {e}")
            return False
    
    async def close(self):
        await self.http_client.aclose()


class EdgeProcessor:
    """Main edge device processor - SHOPLIFTING ONLY"""
    
    def __init__(self):
        self.sync = CentralServerSync(CENTRAL_SERVER_URL, CLIENT_ID, API_KEY)
        self.detector = MLDetector()
        self.vision_analyzer = VisionAnalyzer()  # Renamed from gpt_analyzer
        self.cameras: Dict[str, CameraStream] = {}
        self.config = {}
        self.is_running = True
        self.detection_count = 0
        self.incident_count = 0
        self.suspicious_tracker: Dict[str, Dict] = {}  # Track suspicious frames
        
    async def initialize(self):
        """Initialize edge processor"""
        logger.info("=" * 50)
        logger.info("SecureGuard Edge Device Starting")
        logger.info(f"AI Provider: {AI_PROVIDER.upper()}")
        logger.info("=" * 50)
        
        # Register with central server
        device_ip = self._get_device_ip()
        if await self.sync.register(DEVICE_NAME, device_ip):
            logger.info("✅ Registered with central server")
        else:
            logger.warning("⚠️ Could not register with central server (will retry)")
        
        # Fetch configuration
        await self.refresh_config()
        
        # Initialize ML models
        self.detector.initialize()
        
        # Connect to cameras
        await self.setup_cameras()
        
        # Log AI model status
        logger.info("=" * 50)
        logger.info("AI Model Status:")
        for model, status in ai_model_status.items():
            icon = "✅" if status["loaded"] else "❌"
            logger.info(f"  {icon} {model}: {status['status']}")
        logger.info("=" * 50)
        logger.info("Edge Device Ready")
        logger.info("=" * 50)
    
    def _get_device_ip(self) -> str:
        """Get device IP address"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
    async def refresh_config(self):
        """Refresh configuration from central server"""
        config = await self.sync.get_config()
        
        if config and config.get("success"):
            self.config = config
            
            # Update watchlist
            if "watchlist" in config:
                self.detector.set_watchlist(config["watchlist"])
            
            # Store locally for offline use
            config_db.truncate()
            config_db.insert({"config": config, "timestamp": time.time()})
            
            logger.info(f"✅ Config refreshed: {len(config.get('cameras', []))} cameras")
        else:
            # Try to use cached config
            cached = config_db.all()
            if cached:
                self.config = cached[0].get("config", {})
                logger.info("Using cached configuration")
    
    async def setup_cameras(self):
        """Setup camera connections from config"""
        cameras_config = self.config.get("cameras", [])
        
        if not cameras_config:
            logger.warning("⚠️ No cameras configured. Add cameras in the admin panel.")
            return
        
        for cam in cameras_config:
            cam_id = cam.get("camera_id")
            rtsp_url = cam.get("rtsp_url")
            name = cam.get("name", "Unknown Camera")
            
            if not rtsp_url:
                logger.warning(f"Camera {name} has no RTSP URL, skipping")
                continue
            
            camera = CameraStream(cam_id, rtsp_url, name)
            if camera.connect():
                self.cameras[cam_id] = camera
            else:
                # Store for retry later
                self.cameras[cam_id] = camera
        
        logger.info(f"Camera setup complete: {sum(1 for c in self.cameras.values() if c.is_running)}/{len(self.cameras)} connected")
    
    async def process_frame(self, camera: CameraStream, frame: np.ndarray):
        """Process frame - ONLY GPT-confirmed shoplifting (CRITICAL only)"""
        
        # Step 1: Detect persons (just to know if anyone is in frame)
        detections = self.detector.detect_persons(frame)
        self.detection_count += 1
        
        if not detections:
            return None  # No one in frame
        
        # Step 2: Check watchlist (CRITICAL - known shoplifters)
        if ENABLE_FACE:
            for det in detections:
                match = self.detector.check_watchlist(frame, det["bbox"])
                if match:
                    logger.warning(f"🚨 WATCHLIST MATCH: {match.get('name')}")
                    return await self._create_incident_if_allowed(
                        camera, frame, detections,
                        {
                            "analyzed": False,
                            "threat_level": "critical",
                            "confidence": 0.95,
                            "description": f"Known shoplifter: {match.get('name', 'Unknown')}",
                            "behaviors_detected": ["watchlist_match"],
                            "is_shoplifting": True
                        },
                        match
                    )
        
        # Step 3: Pose detection for suspicious behavior (if enabled)
        suspicious_poses = []
        if ENABLE_POSE:
            poses = self.detector.detect_poses(frame)
            for pose in poses:
                status = pose.get("pose_status", "normal")
                # Use the full set of labels that _analyze_pose() actually returns
                if status in {"suspicious_hands", "crouching", "looking_around", "reaching"}:
                    suspicious_poses.append(status)
            
            if suspicious_poses:
                # Track suspicious frames per camera
                camera_id = camera.camera_id
                if camera_id not in self.suspicious_tracker:
                    self.suspicious_tracker[camera_id] = {"count": 0, "last_time": 0}
                
                tracker = self.suspicious_tracker[camera_id]
                current_time = time.time()
                
                # Reset counter if too much time has passed (use SUSPICIOUS_RESET_WINDOW, not 5s)
                if current_time - tracker["last_time"] > SUSPICIOUS_RESET_WINDOW:
                    tracker["count"] = 1
                else:
                    tracker["count"] += 1
                tracker["last_time"] = current_time
                
                logger.info(f"⚠️ Suspicious pose detected: {suspicious_poses} (frame {tracker['count']}/{MIN_SUSPICIOUS_FRAMES})")
                
                # Only proceed if enough suspicious frames accumulated
                if tracker["count"] < MIN_SUSPICIOUS_FRAMES:
                    return None
        
        # Step 4: Pose-only path (GPT disabled OR GPT confirmation not required)
        if not ENABLE_GPT:
            if suspicious_poses and not REQUIRE_GPT_CONFIRMATION:
                return await self._create_incident_if_allowed(
                    camera, frame, detections,
                    {
                        "analyzed": False,
                        "threat_level": "critical",
                        "confidence": 0.7,
                        "description": f"Suspicious behavior: {', '.join(suspicious_poses)}",
                        "behaviors_detected": suspicious_poses,
                        "is_shoplifting": True
                    },
                    None
                )
            return None
        
        # Pose fallback: if pose is confident AND GPT confirmation not required, fire now
        if suspicious_poses and not REQUIRE_GPT_CONFIRMATION:
            return await self._create_incident_if_allowed(
                camera, frame, detections,
                {
                    "analyzed": False,
                    "threat_level": "critical",
                    "confidence": 0.7,
                    "description": f"Suspicious behavior: {', '.join(suspicious_poses)}",
                    "behaviors_detected": suspicious_poses,
                    "is_shoplifting": True
                },
                None
            )

        # Step 5: Vision AI Analysis (Ollama or Emergent)
        vision_result = await self.vision_analyzer.analyze_scene(frame, detections)
        
        # Skip rate-limited frames — don't treat as safe
        if vision_result.get("skipped"):
            return None
        
        # Only create incident if AI explicitly confirms shoplifting
        if vision_result.get("is_shoplifting") == True:
            logger.warning(f"🚨 SHOPLIFTING: {vision_result.get('description', '')[:80]}")
            return await self._create_incident_if_allowed(camera, frame, detections, vision_result, None)
    
    async def _create_incident_if_allowed(self, camera, frame, detections, vision_result, watchlist_match):
        """Create CRITICAL incident if cooldown allows"""
        current_time = time.time()
        camera_last_incident = getattr(camera, 'last_incident_time', 0)
        
        if current_time - camera_last_incident < INCIDENT_COOLDOWN:
            return None  # Cooldown active
        
        camera.last_incident_time = current_time
        return await self.create_incident(camera, frame, detections, [], vision_result, watchlist_match)
    
    async def create_incident(self, camera: CameraStream, frame: np.ndarray, 
                            detections: List, poses: List, vision_result: Dict,
                            watchlist_match: Optional[Dict] = None) -> Dict:
        """Create and upload CRITICAL shoplifting incident"""
        
        # Generate thumbnail with detection boxes (RED for shoplifters)
        annotated_frame = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            # Red box for all - this is a shoplifting incident
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(annotated_frame, "SHOPLIFTER", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Resize to max 640x480 and compress heavily to avoid 413 payload too large
        thumb_h, thumb_w = annotated_frame.shape[:2]
        scale = min(640 / thumb_w, 480 / thumb_h, 1.0)
        if scale < 1.0:
            annotated_frame = cv2.resize(
                annotated_frame,
                (int(thumb_w * scale), int(thumb_h * scale)),
                interpolation=cv2.INTER_AREA
            )
        _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
        thumbnail = base64.b64encode(buffer).decode('utf-8')
        
        incident = {
            "incident_id": f"inc_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "critical",  # ALWAYS CRITICAL
            "confidence": vision_result.get("confidence", 0.8),
            "description": vision_result.get("description", "Shoplifting detected"),
            "camera_id": camera.camera_id,
            "camera_name": camera.name,
            "frame_thumbnail": thumbnail,
            "behaviors": vision_result.get("behaviors_detected", []),
            "persons_detected": len(detections),
            "watchlist_match": watchlist_match
        }
        
        # Store locally with upload status for offline retry
        local_db.insert({**incident, "uploaded": False})
        self.incident_count += 1
        
        # Upload to central server
        success = await self.sync.upload_incident(incident)
        if success:
            local_db.update({"uploaded": True},
                            Query().incident_id == incident["incident_id"])
        
        severity_icon = "🔴" if incident["severity"] == "critical" else "🟡"
        logger.warning(f"{severity_icon} INCIDENT: {incident['severity'].upper()} - {incident['description'][:60]}")
        
        if not success:
            logger.warning("Incident stored locally for later sync")
        
        return incident
    
    async def upload_snapshots(self):
        """Upload camera snapshots for live view"""
        snapshots = []
        
        for camera_id, camera in self.cameras.items():
            snapshot = camera.get_snapshot()
            if snapshot:
                snapshots.append({
                    "camera_id": camera_id,
                    "camera_name": camera.name,
                    "image": snapshot,
                    "health": camera.health.to_dict()
                })
        
        if snapshots:
            await self.sync.upload_snapshots(snapshots)
    
    async def sync_pending_incidents(self):
        """Sync locally stored incidents that failed to upload"""
        pending = local_db.search(Query().uploaded == False)
        if not pending:
            return
        logger.info(f"Retrying {len(pending)} pending incident(s)...")
        for incident in pending:
            # Remove TinyDB internal fields before uploading
            clean = {k: v for k, v in incident.items() if not k.startswith("_") and k != "uploaded"}
            success = await self.sync.upload_incident(clean)
            if success:
                local_db.update({"uploaded": True}, doc_ids=[incident.doc_id])
    
    async def run(self):
        """Main processing loop"""
        await self.initialize()
        
        last_heartbeat = 0
        last_config_refresh = 0
        last_snapshot = 0
        last_sync = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # Refresh config periodically (every 5 minutes)
                if current_time - last_config_refresh > 300:
                    await self.refresh_config()
                    last_config_refresh = current_time
                
                # Process each camera
                for camera_id, camera in self.cameras.items():
                    if not camera.is_running:
                        # Try to reconnect
                        camera.connect()
                        continue
                    
                    frame = camera.read_frame()
                    
                    if frame is not None:
                        try:
                            incident = await self.process_frame(camera, frame)
                        except Exception as e:
                            logger.error(f"Frame processing error: {e}")
                
                # Upload snapshots for live view
                if current_time - last_snapshot > SNAPSHOT_INTERVAL:
                    await self.upload_snapshots()
                    last_snapshot = current_time
                
                # Retry any incidents that failed to upload
                if current_time - last_sync > SYNC_INTERVAL:
                    await self.sync_pending_incidents()
                    last_sync = current_time
                
                # Heartbeat with health data
                if current_time - last_heartbeat > HEARTBEAT_INTERVAL:
                    online = sum(1 for c in self.cameras.values() if c.is_running)
                    health_data = [c.health.to_dict() for c in self.cameras.values()]
                    
                    await self.sync.send_heartbeat(online, len(self.cameras), health_data)
                    last_heartbeat = current_time
                    
                    # Log status
                    logger.info(f"📊 Status: {online}/{len(self.cameras)} cameras | {self.detection_count} detections | {self.incident_count} incidents")
                
                # Sleep between detection cycles
                await asyncio.sleep(DETECTION_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Processing error: {e}")
                await asyncio.sleep(5)
        
        # Cleanup
        for camera in self.cameras.values():
            camera.release()
        
        await self.sync.close()
        logger.info("Edge Device stopped")
    
    def stop(self):
        """Stop the processor"""
        self.is_running = False


# Main entry point
if __name__ == "__main__":
    if not CLIENT_ID or not API_KEY:
        print("=" * 50)
        print("ERROR: CLIENT_ID and API_KEY must be set in .env")
        print("")
        print("To get these credentials:")
        print("1. Log into the SecureGuard Admin Portal")
        print("2. Go to: Admin → Edge Devices → Provision")
        print("3. Create a new edge device for your client")
        print("4. Copy the CLIENT_ID and API_KEY to your .env file")
        print("=" * 50)
        sys.exit(1)
    
    processor = EdgeProcessor()
    asyncio.run(processor.run())
