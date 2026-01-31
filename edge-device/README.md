# Edge Device for SecureGuard
## ML Processing at Client Location

---

# OVERVIEW

This is the **EDGE DEVICE** software that runs at each client location.
- Runs on Mini PC at client's store
- Handles: Video capture, ML detection, local processing
- Syncs incidents to Central Server
- Direct access to local RTSP cameras

---

# QUICK INSTALL

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USER/secureguard.git
cd secureguard/edge-device

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies (includes ML)
pip install -r requirements.txt

# 4. Install Emergent integrations
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# 5. Configure (credentials from admin)
cp .env.example .env
nano .env

# 6. Run
python edge_processor.py
```

---

# HARDWARE REQUIREMENTS

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Storage | 64 GB SSD | 256 GB SSD |
| GPU | None | NVIDIA GTX 1650+ |
| Network | 100 Mbps | 1 Gbps |

## Recommended Hardware

**Budget ($300-400):**
- Beelink SER5 Pro (Ryzen 5 5600H, 16GB)
- Minisforum UM560 (Ryzen 5 5625U, 16GB)

**Mid-Range ($500-700):**
- Intel NUC 12 Pro (i7-1260P, 16GB)
- Beelink GTR6 (Ryzen 9 6900HX, 32GB)

**High Performance ($800+):**
- Mini PC with NVIDIA GPU
- Custom build with RTX 3060

---

# CONFIGURATION

## Environment Variables (.env)

```env
# Central Server Connection (from admin provisioning)
CENTRAL_SERVER_URL=https://api.yourdomain.com
CLIENT_ID=cli_xxxxxxxxxxxx
API_KEY=sg_edge_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEVICE_NAME=Store-001-Edge

# Emergent API (for GPT Vision)
EMERGENT_LLM_KEY=sk-emergent-xxxxxxxxxxxx

# Detection Settings
DETECTION_INTERVAL=1.0
CONFIDENCE_THRESHOLD=0.6
ENABLE_POSE_DETECTION=true
ENABLE_FACE_RECOGNITION=true
ENABLE_GPT_ANALYSIS=true

# Camera Discovery
AUTO_DISCOVER_CAMERAS=true
CAMERA_SCAN_SUBNET=192.168.200.0/24

# Or Manual Camera Config
# CAMERAS=rtsp://admin:pass@192.168.200.189:554/stream1,rtsp://admin:pass@192.168.200.190:554/stream1

# Local Storage
LOCAL_INCIDENT_RETENTION_DAYS=7
VIDEO_CLIP_DURATION=30

# Sync Settings
SYNC_INTERVAL_SECONDS=60
HEARTBEAT_INTERVAL_SECONDS=60
```

---

# RUNNING AS SERVICE

## Using systemd (Linux)

```bash
sudo nano /etc/systemd/system/secureguard-edge.service
```

```ini
[Unit]
Description=SecureGuard Edge Device
After=network.target

[Service]
Type=simple
User=secureguard
WorkingDirectory=/home/secureguard/edge-device
Environment=PATH=/home/secureguard/edge-device/venv/bin
ExecStart=/home/secureguard/edge-device/venv/bin/python edge_processor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable secureguard-edge
sudo systemctl start secureguard-edge
```

## Using PM2

```bash
pm2 start edge_processor.py --name secureguard-edge --interpreter python3
pm2 save
pm2 startup
```

---

# LOCAL WEB UI

The edge device runs a local web interface for configuration:

- URL: `http://DEVICE_IP:8080`
- Features:
  - Add/remove cameras
  - View live detection
  - Check connection status
  - View local incidents

---

# CAMERA AUTO-DISCOVERY

The edge device can automatically find cameras on the network:

```python
# Scans for RTSP cameras on subnet
python -m edge_device.discover_cameras --subnet 192.168.200.0/24
```

Supported protocols:
- RTSP (port 554)
- ONVIF (auto-detect URL)
- HTTP streams
