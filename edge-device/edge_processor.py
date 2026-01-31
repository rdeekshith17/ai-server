"""
SecureGuard Edge Device Processor
Runs at client location - handles video capture and ML detection

This processor:
1. Connects to local RTSP cameras
2. Runs ML detection (YOLO, DeepFace, Pose)
3. Calls GPT Vision for behavior analysis
4. Syncs incidents to Central Server
5. Stores local cache for offline operation
"""

import os
import sys
import time
import json
import asyncio
import logging
import threading
import base64
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

import cv2
import numpy as np
import httpx
from dotenv import load_dotenv
from tinydb import TinyDB, Query

# Load environment
load_dotenv()

# Configuration
CENTRAL_SERVER_URL = os.environ.get("CENTRAL_SERVER_URL", "http://localhost:8001")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
API_KEY = os.environ.get("API_KEY", "")
DEVICE_NAME = os.environ.get("DEVICE_NAME", "Edge-Device-001")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

DETECTION_INTERVAL = float(os.environ.get("DETECTION_INTERVAL", "1.0"))
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.6"))
ENABLE_POSE = os.environ.get("ENABLE_POSE_DETECTION", "true").lower() == "true"
ENABLE_FACE = os.environ.get("ENABLE_FACE_RECOGNITION", "true").lower() == "true"
ENABLE_GPT = os.environ.get("ENABLE_GPT_ANALYSIS", "true").lower() == "true"

SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_SECONDS", "60"))
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "60"))

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

# ML Models (lazy loaded)
yolo_model = None
pose_model = None
deepface_initialized = False


class CameraStream:
    """Manages RTSP camera connection"""
    
    def __init__(self, camera_id: str, rtsp_url: str, name: str = "Camera"):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.name = name
        self.cap = None
        self.is_running = False
        self.last_frame = None
        self.frame_count = 0
        self.error_count = 0
        
    def connect(self) -> bool:
        """Connect to RTSP stream"""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if self.cap.isOpened():
                logger.info(f"Connected to camera: {self.name} ({self.camera_id})")
                self.is_running = True
                self.error_count = 0
                return True
            else:
                logger.error(f"Failed to connect to camera: {self.name}")
                return False
        except Exception as e:
            logger.error(f"Camera connection error: {e}")
            return False
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Read single frame from camera"""
        if not self.cap or not self.cap.isOpened():
            self.error_count += 1
            if self.error_count > 5:
                self.connect()  # Attempt reconnect
            return None
        
        ret, frame = self.cap.read()
        if ret:
            self.last_frame = frame
            self.frame_count += 1
            self.error_count = 0
            return frame
        else:
            self.error_count += 1
            return None
    
    def release(self):
        """Release camera connection"""
        self.is_running = False
        if self.cap:
            self.cap.release()


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
            logger.info("YOLO model loaded")
        except Exception as e:
            logger.error(f"Failed to load YOLO: {e}")
        
        # Pose estimation
        if ENABLE_POSE:
            try:
                self.pose_model = YOLO("yolov8n-pose.pt")
                logger.info("Pose model loaded")
            except Exception as e:
                logger.error(f"Failed to load Pose model: {e}")
        
        # DeepFace
        if ENABLE_FACE:
            try:
                from deepface import DeepFace
                # Warm up
                DeepFace.build_model("VGG-Face")
                self.deepface_initialized = True
                logger.info("DeepFace initialized")
            except Exception as e:
                logger.error(f"Failed to initialize DeepFace: {e}")
    
    def detect_persons(self, frame: np.ndarray) -> List[Dict]:
        """Detect persons in frame using YOLO"""
        if not self.yolo_model:
            return []
        
        results = self.yolo_model(frame, verbose=False)
        detections = []
        
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls == 0 and conf > CONFIDENCE_THRESHOLD:  # Person class
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    detections.append({
                        "class": "person",
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2]
                    })
        
        return detections
    
    def detect_poses(self, frame: np.ndarray) -> List[Dict]:
        """Detect body poses"""
        if not self.pose_model or not ENABLE_POSE:
            return []
        
        results = self.pose_model(frame, verbose=False)
        poses = []
        
        for result in results:
            if result.keypoints is not None:
                for kp in result.keypoints:
                    keypoints = kp.xy.cpu().numpy() if hasattr(kp.xy, 'cpu') else kp.xy
                    poses.append({
                        "keypoints": keypoints.tolist(),
                        "pose_status": self._analyze_pose(keypoints)
                    })
        
        return poses
    
    def _analyze_pose(self, keypoints) -> str:
        """Analyze pose for suspicious behavior"""
        # Simplified pose analysis
        # Real implementation would be more sophisticated
        return "normal"
    
    def check_watchlist(self, frame: np.ndarray, bbox: List[int]) -> Optional[Dict]:
        """Check if detected face matches watchlist"""
        if not self.deepface_initialized or not ENABLE_FACE:
            return None
        
        if not self.watchlist_encodings:
            return None
        
        try:
            from deepface import DeepFace
            
            x1, y1, x2, y2 = bbox
            face_img = frame[y1:y2, x1:x2]
            
            if face_img.size == 0:
                return None
            
            # Get encoding
            embedding = DeepFace.represent(face_img, model_name="VGG-Face", enforce_detection=False)
            
            # Compare with watchlist
            for person in self.watchlist_encodings:
                # Simple distance check (real implementation would use proper similarity)
                # This is a placeholder
                pass
            
            return None
            
        except Exception as e:
            logger.debug(f"Face check error: {e}")
            return None
    
    def update_watchlist(self, watchlist: List[Dict]):
        """Update watchlist encodings"""
        self.watchlist_encodings = watchlist
        logger.info(f"Updated watchlist with {len(watchlist)} entries")


class GPTAnalyzer:
    """GPT Vision analysis for behavior detection"""
    
    def __init__(self):
        self.enabled = ENABLE_GPT and EMERGENT_LLM_KEY
        
    async def analyze_scene(self, frame: np.ndarray, detections: List[Dict]) -> Dict:
        """Analyze scene using GPT Vision"""
        if not self.enabled:
            return {"analyzed": False, "reason": "GPT analysis disabled"}
        
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
            
            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Create prompt
            prompt = """Analyze this retail store security camera image for potential shoplifting.
            
Look for:
1. Suspicious behaviors (concealment, looking around nervously, unusual movements)
2. Items being hidden in clothing, bags, or pockets
3. Tag removal or product tampering
4. Coordinated group activities

Respond in JSON format:
{
    "threat_level": "safe|warning|critical",
    "confidence": 0.0-1.0,
    "behaviors_detected": ["list of behaviors"],
    "description": "brief description",
    "items_involved": ["any items of concern"]
}"""
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                model="gpt-5.2",
                system_prompt="You are a security AI analyzing surveillance footage."
            )
            
            response = await chat.send_message_async(
                UserMessage(
                    content=[
                        prompt,
                        ImageContent(base64_image=image_base64)
                    ]
                )
            )
            
            # Parse response
            try:
                result = json.loads(response.content)
                result["analyzed"] = True
                return result
            except:
                return {
                    "analyzed": True,
                    "threat_level": "safe",
                    "confidence": 0.5,
                    "description": response.content[:200]
                }
                
        except Exception as e:
            logger.error(f"GPT analysis error: {e}")
            return {"analyzed": False, "error": str(e)}


class CentralServerSync:
    """Handles communication with central server"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.is_connected = False
        self.pending_incidents = []
        
    async def register(self) -> bool:
        """Register device with central server"""
        try:
            response = await self.client.post(
                f"{CENTRAL_SERVER_URL}/api/edge/register",
                json={
                    "client_id": CLIENT_ID,
                    "api_key": API_KEY,
                    "device_name": DEVICE_NAME,
                    "device_ip": self._get_local_ip()
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Registered with central server")
                self.is_connected = True
                return True
            else:
                logger.error(f"Registration failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False
    
    async def send_heartbeat(self, cameras_online: int, cameras_total: int) -> Dict:
        """Send heartbeat to central server"""
        try:
            import psutil
            
            response = await self.client.post(
                f"{CENTRAL_SERVER_URL}/api/edge/heartbeat",
                json={
                    "client_id": CLIENT_ID,
                    "api_key": API_KEY,
                    "device_id": f"edge_{CLIENT_ID}",
                    "status": "online",
                    "cameras_online": cameras_online,
                    "cameras_total": cameras_total,
                    "cpu_usage": psutil.cpu_percent(),
                    "memory_usage": psutil.virtual_memory().percent,
                    "last_incident_at": None
                }
            )
            
            if response.status_code == 200:
                return response.json()
            return {}
            
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return {}
    
    async def upload_incident(self, incident: Dict) -> bool:
        """Upload incident to central server"""
        try:
            response = await self.client.post(
                f"{CENTRAL_SERVER_URL}/api/edge/incidents",
                json={
                    "client_id": CLIENT_ID,
                    "api_key": API_KEY,
                    **incident
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Incident uploaded: {incident['incident_id']}")
                return True
            else:
                logger.error(f"Incident upload failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Incident upload error: {e}")
            # Store for later sync
            self.pending_incidents.append(incident)
            return False
    
    async def sync_pending(self):
        """Sync any pending incidents"""
        synced = []
        for incident in self.pending_incidents:
            if await self.upload_incident(incident):
                synced.append(incident)
        
        for incident in synced:
            self.pending_incidents.remove(incident)
    
    async def get_config(self) -> Dict:
        """Get latest config from central server"""
        try:
            response = await self.client.get(
                f"{CENTRAL_SERVER_URL}/api/edge/config/{CLIENT_ID}",
                params={"api_key": API_KEY}
            )
            
            if response.status_code == 200:
                return response.json()
            return {}
            
        except Exception as e:
            logger.error(f"Config fetch error: {e}")
            return {}
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"


class EdgeProcessor:
    """Main edge device processor"""
    
    def __init__(self):
        self.cameras: Dict[str, CameraStream] = {}
        self.detector = MLDetector()
        self.gpt_analyzer = GPTAnalyzer()
        self.sync = CentralServerSync()
        self.is_running = False
        
    async def initialize(self):
        """Initialize the edge processor"""
        logger.info("=" * 50)
        logger.info("SecureGuard Edge Device Starting...")
        logger.info(f"Client ID: {CLIENT_ID}")
        logger.info(f"Central Server: {CENTRAL_SERVER_URL}")
        logger.info("=" * 50)
        
        # Initialize ML models
        self.detector.initialize()
        
        # Register with central server
        if await self.sync.register():
            # Get initial config
            config = await self.sync.get_config()
            if config.get("watchlist"):
                self.detector.update_watchlist(config["watchlist"])
        
        # Load cameras from config or environment
        await self.load_cameras()
        
        self.is_running = True
        logger.info("Edge Device initialized and ready!")
    
    async def load_cameras(self):
        """Load camera configuration"""
        cameras_env = os.environ.get("CAMERAS", "")
        
        if cameras_env:
            for i, url in enumerate(cameras_env.split(",")):
                camera_id = f"cam_{i+1}"
                camera = CameraStream(camera_id, url.strip(), f"Camera {i+1}")
                if camera.connect():
                    self.cameras[camera_id] = camera
        else:
            # Default to your cameras
            default_cameras = [
                ("cam_ch1", "rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=1&subtype=1", "Channel 1"),
                ("cam_ch2", "rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=2&subtype=1", "Channel 2"),
            ]
            
            for cam_id, url, name in default_cameras:
                camera = CameraStream(cam_id, url, name)
                if camera.connect():
                    self.cameras[cam_id] = camera
        
        logger.info(f"Loaded {len(self.cameras)} cameras")
    
    async def process_frame(self, camera: CameraStream, frame: np.ndarray):
        """Process a single frame for detection"""
        
        # Step 1: Detect persons
        detections = self.detector.detect_persons(frame)
        
        if not detections:
            return None  # No persons detected
        
        # Step 2: Detect poses
        poses = self.detector.detect_poses(frame)
        
        # Step 3: Check watchlist for each detection
        for det in detections:
            match = self.detector.check_watchlist(frame, det["bbox"])
            if match:
                det["watchlist_match"] = match
        
        # Step 4: GPT analysis if multiple persons or suspicious pose
        gpt_result = {"analyzed": False}
        if ENABLE_GPT and (len(detections) > 1 or any(p.get("pose_status") != "normal" for p in poses)):
            gpt_result = await self.gpt_analyzer.analyze_scene(frame, detections)
        
        # Step 5: Determine if incident should be created
        threat_level = gpt_result.get("threat_level", "safe")
        
        if threat_level in ["warning", "critical"] or any(d.get("watchlist_match") for d in detections):
            # Create incident
            incident = await self.create_incident(camera, frame, detections, poses, gpt_result)
            return incident
        
        return None
    
    async def create_incident(self, camera: CameraStream, frame: np.ndarray, 
                            detections: List, poses: List, gpt_result: Dict) -> Dict:
        """Create and upload incident"""
        
        # Generate thumbnail
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
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
            "watchlist_match": next((d.get("watchlist_match") for d in detections if d.get("watchlist_match")), None)
        }
        
        # Store locally
        local_db.insert(incident)
        
        # Upload to central server
        await self.sync.upload_incident(incident)
        
        logger.warning(f"INCIDENT CREATED: {incident['severity']} - {incident['description'][:50]}")
        
        return incident
    
    async def run(self):
        """Main processing loop"""
        await self.initialize()
        
        last_heartbeat = 0
        
        while self.is_running:
            try:
                # Process each camera
                for camera_id, camera in self.cameras.items():
                    frame = camera.read_frame()
                    
                    if frame is not None:
                        incident = await self.process_frame(camera, frame)
                
                # Heartbeat
                if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                    online = sum(1 for c in self.cameras.values() if c.is_running)
                    await self.sync.send_heartbeat(online, len(self.cameras))
                    last_heartbeat = time.time()
                
                # Sleep between detections
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
        
        logger.info("Edge Device stopped")
    
    def stop(self):
        """Stop the processor"""
        self.is_running = False


# Main entry point
if __name__ == "__main__":
    if not CLIENT_ID or not API_KEY:
        print("ERROR: CLIENT_ID and API_KEY must be set in .env")
        print("Get these from your admin at: Admin → Edge Devices → Provision")
        sys.exit(1)
    
    processor = EdgeProcessor()
    asyncio.run(processor.run())
