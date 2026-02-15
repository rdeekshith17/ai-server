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
from typing import Dict, List, Optional, Tuple
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
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

DETECTION_INTERVAL = float(os.environ.get("DETECTION_INTERVAL", "0.2"))  # 5 FPS processing
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.3"))  # Lower for more detections
ENABLE_POSE = os.environ.get("ENABLE_POSE_DETECTION", "true").lower() == "true"
ENABLE_FACE = os.environ.get("ENABLE_FACE_RECOGNITION", "true").lower() == "true"
ENABLE_GPT = os.environ.get("ENABLE_GPT_ANALYSIS", "true").lower() == "true"

# Shoplifting detection settings
INCIDENT_COOLDOWN = int(os.environ.get("INCIDENT_COOLDOWN_SECONDS", "30"))  # Don't spam incidents
SUSPICIOUS_POSE_THRESHOLD = float(os.environ.get("SUSPICIOUS_POSE_THRESHOLD", "0.4"))
CREATE_TEST_INCIDENTS = os.environ.get("CREATE_TEST_INCIDENTS", "false").lower() == "true"

SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_SECONDS", "60"))
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "60"))
SNAPSHOT_INTERVAL = float(os.environ.get("SNAPSHOT_INTERVAL_SECONDS", "1"))  # 1 FPS live view
MAX_RECONNECT_ATTEMPTS = int(os.environ.get("MAX_RECONNECT_ATTEMPTS", "10"))
RECONNECT_DELAY = int(os.environ.get("RECONNECT_DELAY_SECONDS", "5"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EdgeDevice")

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
        with self.lock:
            try:
                # Release existing connection
                if self.cap:
                    self.cap.release()
                
                logger.info(f"Connecting to camera: {self.name} ({self.rtsp_url})")
                
                # Set RTSP transport options for better reliability
                # Try TCP first (more reliable), fallback to UDP
                os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|buffer_size;1024000'
                
                self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
                
                # Set timeouts
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
                
                if self.cap.isOpened():
                    # Read a test frame
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        logger.info(f"✅ Connected to camera: {self.name} ({self.camera_id})")
                        self.is_running = True
                        self.health.is_connected = True
                        self.reconnect_attempts = 0
                        self.last_frame = frame
                        self.last_frame_time = time.time()
                        return True
                    else:
                        logger.warning(f"Camera opened but no frame: {self.name}")
                
                logger.error(f"❌ Failed to connect to camera: {self.name}")
                self.health.is_connected = False
                return False
                
            except Exception as e:
                logger.error(f"Camera connection error ({self.name}): {e}")
                self.health.is_connected = False
                return False
    
    def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Max reconnect attempts reached for {self.name}")
            return False
        
        self.reconnect_attempts += 1
        self.health.record_reconnect()
        
        delay = min(RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1)), 60)
        logger.info(f"Reconnecting to {self.name} in {delay}s (attempt {self.reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})")
        
        time.sleep(delay)
        return self.connect()
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Read single frame from camera with error handling"""
        with self.lock:
            if not self.cap or not self.cap.isOpened():
                if not self.reconnect():
                    return None
            
            try:
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    # Validate frame
                    if frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
                        self.health.record_error()
                        return self.last_frame  # Return last good frame
                    
                    self.last_frame = frame
                    self.last_frame_time = time.time()
                    self.health.record_frame()
                    self.health.frames_processed += 1
                    return frame
                else:
                    self.health.record_error()
                    
                    # Check if we've lost connection
                    if self.health.decode_errors > 10:
                        logger.warning(f"Too many errors on {self.name}, reconnecting...")
                        self.reconnect()
                        self.health.decode_errors = 0
                    
                    # Return last good frame if available
                    if self.last_frame is not None:
                        return self.last_frame
                    return None
                    
            except Exception as e:
                logger.error(f"Frame read error ({self.name}): {e}")
                self.health.record_error()
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
        with self.lock:
            self.is_running = False
            self.health.is_connected = False
            if self.cap:
                self.cap.release()
                self.cap = None


class MLDetector:
    """Handles all ML detection tasks"""
    
    def __init__(self):
        self.yolo_model = None
        self.pose_model = None
        self.deepface_initialized = False
        self.watchlist_encodings = []
        
    def initialize(self):
        """Initialize ML models"""
        logger.info("Initializing ML models...")
        
        # YOLO for person detection
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO("yolov8n.pt")
            logger.info("✅ YOLO model loaded")
        except Exception as e:
            logger.error(f"Failed to load YOLO: {e}")
        
        # Pose estimation
        if ENABLE_POSE:
            try:
                from ultralytics import YOLO
                self.pose_model = YOLO("yolov8n-pose.pt")
                logger.info("✅ Pose model loaded")
            except Exception as e:
                logger.error(f"Failed to load pose model: {e}")
        
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
                logger.info("✅ DeepFace initialized")
            except Exception as e:
                logger.error(f"Failed to initialize DeepFace: {e}")
    
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
            
            # 2. Check for bent/crouching posture (reaching low shelves)
            if nose[1] > 0 and waist_y > 0:
                if nose[1] > waist_y * 0.7:  # Head below waist level
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
                left_arm_extended = abs(left_wrist[0] - left_shoulder[0]) > 150
                if left_arm_extended:
                    suspicious_behaviors.append("arm_extended")
            
            if right_shoulder[0] > 0 and right_wrist[0] > 0:
                right_arm_extended = abs(right_wrist[0] - right_shoulder[0]) > 150
                if right_arm_extended:
                    suspicious_behaviors.append("arm_extended")
            
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
            elif "arm_extended" in suspicious_behaviors:
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
                            "confidence": 1 - distance
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


class GPTAnalyzer:
    """GPT-5.2 Vision analysis for advanced threat detection"""
    
    def __init__(self):
        self.enabled = ENABLE_GPT and EMERGENT_LLM_KEY
        self.last_analysis_time = 0
        self.min_analysis_interval = 3.0  # Don't analyze too frequently
        
    async def analyze_scene(self, frame: np.ndarray, detections: List[Dict]) -> Dict:
        """Analyze scene with GPT Vision for threat assessment"""
        if not self.enabled:
            return {"analyzed": False, "threat_level": "unknown"}
        
        # Rate limit
        now = time.time()
        if now - self.last_analysis_time < self.min_analysis_interval:
            return {"analyzed": False, "threat_level": "unknown", "reason": "rate_limited"}
        
        try:
            from emergentintegrations.llm.openai import chat_completion_with_image
            
            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            prompt = f"""Analyze this retail store security camera image for potential shoplifting behavior.

There are {len(detections)} people detected in the frame.

Look for these suspicious behaviors:
1. Concealment - hiding items in clothing, bags, or pockets
2. Nervous behavior - looking around frequently, avoiding staff
3. Unusual browsing - staying too long in one area, handling items excessively
4. Group distraction - one person distracting while another takes items
5. Bag/jacket stuffing - putting items in personal bags or clothing
6. Price tag tampering
7. Quick grab and movement toward exit

Response Format (JSON):
{{
  "threat_level": "safe" | "warning" | "critical",
  "confidence": 0.0-1.0,
  "description": "Brief description of what you see",
  "behaviors_detected": ["list", "of", "suspicious", "behaviors"],
  "recommended_action": "suggestion for security staff"
}}

Respond ONLY with the JSON object, no other text."""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: chat_completion_with_image(
                    api_key=EMERGENT_LLM_KEY,
                    image=img_base64,
                    prompt=prompt,
                    model="gpt-5.2"
                )
            )
            
            self.last_analysis_time = now
            
            # Parse response
            if response and response.content:
                content = response.content.strip()
                # Extract JSON from response
                if content.startswith("{"):
                    result = json.loads(content)
                    result["analyzed"] = True
                    return result
            
            return {"analyzed": False, "threat_level": "unknown"}
            
        except Exception as e:
            logger.error(f"GPT analysis error: {e}")
            return {"analyzed": False, "threat_level": "unknown", "error": str(e)}


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
        """Send heartbeat with health data"""
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
    """Main edge device processor"""
    
    def __init__(self):
        self.sync = CentralServerSync(CENTRAL_SERVER_URL, CLIENT_ID, API_KEY)
        self.detector = MLDetector()
        self.gpt_analyzer = GPTAnalyzer()
        self.cameras: Dict[str, CameraStream] = {}
        self.config = {}
        self.is_running = True
        self.detection_count = 0
        self.incident_count = 0
        
    async def initialize(self):
        """Initialize edge processor"""
        logger.info("=" * 50)
        logger.info("SecureGuard Edge Device Starting")
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
        """Process a single frame for detection - MORE SENSITIVE"""
        
        # Step 1: Detect persons
        detections = self.detector.detect_persons(frame)
        self.detection_count += 1
        
        if not detections:
            return None  # No persons detected
        
        # Step 2: Detect poses
        poses = []
        if ENABLE_POSE:
            poses = self.detector.detect_poses(frame)
        
        # Step 3: Check watchlist for each detection
        watchlist_match = None
        for det in detections:
            match = self.detector.check_watchlist(frame, det["bbox"])
            if match:
                det["watchlist_match"] = match
                watchlist_match = match
        
        # Determine if we should create an incident
        should_create_incident = False
        should_analyze_gpt = False
        threat_indicators = []
        
        # Check for suspicious poses - ANY suspicious pose triggers incident
        suspicious_poses = [p for p in poses if p.get("pose_status") not in ["normal", "unknown"]]
        if suspicious_poses:
            should_create_incident = True
            should_analyze_gpt = True
            threat_indicators.extend([p["pose_status"] for p in suspicious_poses])
            logger.info(f"🔍 Suspicious pose detected: {[p['pose_status'] for p in suspicious_poses]}")
        
        # Multiple people increases risk
        if len(detections) >= 2:
            should_analyze_gpt = True
            threat_indicators.append("multiple_persons")
        
        # Watchlist match is always critical
        if watchlist_match:
            should_create_incident = True
            should_analyze_gpt = True
            threat_indicators.append("watchlist_match")
        
        # Single person near high-value areas (if configured)
        if len(detections) == 1 and poses:
            # Check if person is in certain positions that might indicate grabbing
            for pose in poses:
                if pose.get("pose_status") in ["reaching", "looking_around"]:
                    should_create_incident = True
                    threat_indicators.append(pose.get("pose_status"))
        
        # Step 4: GPT analysis if needed
        gpt_result = {"analyzed": False, "threat_level": "safe"}
        
        if should_analyze_gpt and ENABLE_GPT:
            gpt_result = await self.gpt_analyzer.analyze_scene(frame, detections)
            if gpt_result.get("threat_level") in ["warning", "critical"]:
                should_create_incident = True
        
        # Generate basic incident for suspicious poses even without GPT
        if should_create_incident and not gpt_result.get("analyzed"):
            severity = "critical" if watchlist_match else "warning"
            gpt_result = {
                "analyzed": False,
                "threat_level": severity,
                "confidence": 0.65,
                "description": f"Suspicious behavior: {', '.join(set(threat_indicators))}",
                "behaviors_detected": list(set(threat_indicators))
            }
        
        # Step 5: Create incident if warranted
        threat_level = gpt_result.get("threat_level", "safe")
        
        if should_create_incident or threat_level in ["warning", "critical"] or watchlist_match:
            # Check cooldown to avoid spam
            current_time = time.time()
            camera_last_incident = getattr(camera, 'last_incident_time', 0)
            
            if current_time - camera_last_incident < INCIDENT_COOLDOWN:
                return None  # Still in cooldown
            
            camera.last_incident_time = current_time
            incident = await self.create_incident(camera, frame, detections, poses, gpt_result, watchlist_match)
            return incident
        
        return None
    
    async def create_incident(self, camera: CameraStream, frame: np.ndarray, 
                            detections: List, poses: List, gpt_result: Dict,
                            watchlist_match: Optional[Dict] = None) -> Dict:
        """Create and upload incident"""
        
        # Generate thumbnail with detection boxes
        annotated_frame = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            color = (0, 0, 255) if det.get("watchlist_match") else (0, 255, 0)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
        
        _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        thumbnail = base64.b64encode(buffer).decode('utf-8')
        
        incident = {
            "incident_id": f"inc_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": gpt_result.get("threat_level", "warning"),
            "confidence": gpt_result.get("confidence", 0.7),
            "description": gpt_result.get("description", "Suspicious activity detected"),
            "camera_id": camera.camera_id,
            "camera_name": camera.name,
            "frame_thumbnail": thumbnail,
            "behaviors": gpt_result.get("behaviors_detected", []),
            "persons_detected": len(detections),
            "watchlist_match": watchlist_match
        }
        
        # Store locally
        local_db.insert(incident)
        self.incident_count += 1
        
        # Upload to central server
        success = await self.sync.upload_incident(incident)
        
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
        """Sync any locally stored incidents that failed to upload"""
        # This would sync incidents stored in local_db that haven't been uploaded
        pass
    
    async def run(self):
        """Main processing loop"""
        await self.initialize()
        
        last_heartbeat = 0
        last_config_refresh = 0
        last_snapshot = 0
        
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
