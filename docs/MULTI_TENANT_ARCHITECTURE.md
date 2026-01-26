# SecureGuard Multi-Tenant Architecture
## Enterprise Shoplifting Detection Platform

---

## 1. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ADMIN DASHBOARD                                      │
│                    (Your Central Management Console)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Client    │  │   Billing   │  │  Analytics  │  │   System    │            │
│  │ Management  │  │  & Plans    │  │  Overview   │  │  Health     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY / LOAD BALANCER                           │
│                    (NGINX / AWS ALB / Cloudflare)                                │
│         Rate Limiting │ SSL Termination │ Request Routing │ Auth Check          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│   AUTH SERVICE        │  │   API SERVICE         │  │   STREAM SERVICE      │
│   (Authentication)    │  │   (REST API)          │  │   (RTSP Ingestion)    │
│                       │  │                       │  │                       │
│ • JWT Token Issue     │  │ • Client CRUD         │  │ • RTSP Connection     │
│ • API Key Validation  │  │ • Camera Management   │  │ • Frame Extraction    │
│ • Role-Based Access   │  │ • Incident Retrieval  │  │ • Stream Health       │
│ • Multi-tenant Auth   │  │ • Analytics           │  │ • Reconnect Logic     │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          MESSAGE QUEUE (Redis / RabbitMQ)                        │
│                    Frame Queue │ Alert Queue │ Analytics Queue                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│   ML WORKER POOL      │  │   ML WORKER POOL      │  │   ML WORKER POOL      │
│   (Auto-scaling)      │  │   (Auto-scaling)      │  │   (Auto-scaling)      │
│                       │  │                       │  │                       │
│ • YOLO Detection      │  │ • YOLO Detection      │  │ • YOLO Detection      │
│ • Pose Estimation     │  │ • Pose Estimation     │  │ • Pose Estimation     │
│ • Face Recognition    │  │ • Face Recognition    │  │ • Face Recognition    │
│ • GPT-5.2 Analysis    │  │ • GPT-5.2 Analysis    │  │ • GPT-5.2 Analysis    │
│ • Decision Engine     │  │ • Decision Engine     │  │ • Decision Engine     │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE LAYER                                       │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                       │
│  │      MongoDB            │  │      Redis              │                       │
│  │  (Multi-tenant Data)    │  │  (Cache & Sessions)     │                       │
│  │                         │  │                         │                       │
│  │  • clients collection   │  │  • Session tokens       │                       │
│  │  • users collection     │  │  • Rate limit counters  │                       │
│  │  • cameras collection   │  │  • Real-time frames     │                       │
│  │  • incidents collection │  │  • Stream status        │                       │
│  │  • watchlists collection│  │  • Alert queue          │                       │
│  └─────────────────────────┘  └─────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           OBJECT STORAGE (S3 / MinIO)                            │
│              Video Clips │ Incident Screenshots │ Watchlist Photos               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. MULTI-TENANT DATA MODEL

### 2.1 Client (Tenant) Schema
```javascript
{
  "_id": ObjectId,
  "client_id": "cli_xxxxx",           // Unique client identifier
  "name": "ABC Liquor Store",
  "slug": "abc-liquor",               // URL-friendly identifier
  "contact": {
    "name": "John Smith",
    "email": "john@abcliquor.com",
    "phone": "+1-555-0123"
  },
  "subscription": {
    "plan": "professional",           // basic, professional, enterprise
    "max_cameras": 16,
    "max_users": 5,
    "features": ["live_detection", "watchlist", "analytics", "api_access"],
    "billing_cycle": "monthly",
    "price_cents": 29900,
    "started_at": ISODate,
    "expires_at": ISODate
  },
  "settings": {
    "timezone": "America/New_York",
    "alert_email": true,
    "alert_sms": false,
    "alert_webhook": "https://...",
    "detection_sensitivity": "medium",  // low, medium, high
    "auto_incident_creation": true
  },
  "api_keys": [
    {
      "key_id": "key_xxxxx",
      "key_hash": "hashed_api_key",
      "name": "Production Key",
      "permissions": ["read", "write"],
      "created_at": ISODate,
      "last_used_at": ISODate
    }
  ],
  "status": "active",                 // active, suspended, trial, cancelled
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### 2.2 User Schema (Multi-tenant)
```javascript
{
  "_id": ObjectId,
  "user_id": "usr_xxxxx",
  "client_id": "cli_xxxxx",           // Tenant association
  "email": "manager@store.com",
  "password_hash": "bcrypt_hash",
  "role": "manager",                  // owner, manager, viewer, api_only
  "permissions": {
    "view_live": true,
    "view_incidents": true,
    "manage_cameras": true,
    "manage_watchlist": true,
    "view_analytics": true,
    "manage_users": false,
    "api_access": true
  },
  "mfa_enabled": false,
  "last_login_at": ISODate,
  "created_at": ISODate
}
```

### 2.3 Camera Schema
```javascript
{
  "_id": ObjectId,
  "camera_id": "cam_xxxxx",
  "client_id": "cli_xxxxx",           // Tenant association
  "name": "Entrance Camera 1",
  "location": "Front Door",
  "rtsp_url": "rtsp://user:pass@192.168.1.100:554/stream1",
  "rtsp_url_encrypted": "encrypted_string",  // Stored encrypted
  "resolution": "1080p",
  "fps": 15,
  "store_info": {
    "store_id": "store_001",
    "store_name": "Main Street Location",
    "address": "123 Main St",
    "store_type": "liquor"
  },
  "detection_settings": {
    "enabled": true,
    "sensitivity": "medium",
    "detection_zone": [[0,0], [100,0], [100,100], [0,100]],  // Polygon
    "excluded_zones": [],
    "process_fps": 2,                 // Frames to analyze per second
    "enable_pose": true,
    "enable_face_recognition": true,
    "enable_gpt_analysis": false      // Cost consideration
  },
  "status": "online",                 // online, offline, error, disabled
  "last_frame_at": ISODate,
  "health": {
    "uptime_percent": 99.5,
    "avg_latency_ms": 150,
    "error_count_24h": 2
  },
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### 2.4 Incident Schema (Multi-tenant)
```javascript
{
  "_id": ObjectId,
  "incident_id": "inc_xxxxx",
  "client_id": "cli_xxxxx",           // Tenant association
  "camera_id": "cam_xxxxx",
  "store_id": "store_001",
  "timestamp": ISODate,
  "severity": "critical",
  "confidence": 0.87,
  "detection_type": "theft",          // theft, watchlist_match, staff_theft
  "description": "Item concealment detected",
  "details": {
    "person_description": "Male, blue jacket",
    "items_involved": ["liquor bottle"],
    "concealment_method": "coat",
    "movement_towards_exit": true,
    "behaviors": ["item_in_pocket", "concealment_posture"]
  },
  "evidence": {
    "frame_url": "s3://bucket/incidents/inc_xxxxx/frame.jpg",
    "video_clip_url": "s3://bucket/incidents/inc_xxxxx/clip.mp4",
    "thumbnail_url": "s3://bucket/incidents/inc_xxxxx/thumb.jpg"
  },
  "watchlist_match": {
    "matched": true,
    "person_id": "wl_xxxxx",
    "person_name": "John Doe",
    "match_confidence": 0.92
  },
  "ml_metadata": {
    "yolo_detections": 2,
    "pose_analysis": {...},
    "gpt_analysis": {...},
    "processing_time_ms": 450
  },
  "status": "new",                    // new, reviewed, escalated, resolved, false_positive
  "reviewed_by": "usr_xxxxx",
  "reviewed_at": ISODate,
  "notes": "Confirmed theft, police notified",
  "created_at": ISODate
}
```

---

## 3. API STRUCTURE

### 3.1 Authentication Endpoints
```
POST   /api/v1/auth/login              # User login (returns JWT)
POST   /api/v1/auth/refresh            # Refresh JWT token
POST   /api/v1/auth/logout             # Invalidate token
POST   /api/v1/auth/api-key/validate   # Validate API key
```

### 3.2 Admin Endpoints (Your Dashboard)
```
# Client Management
GET    /api/v1/admin/clients                    # List all clients
POST   /api/v1/admin/clients                    # Create new client
GET    /api/v1/admin/clients/{client_id}        # Get client details
PUT    /api/v1/admin/clients/{client_id}        # Update client
DELETE /api/v1/admin/clients/{client_id}        # Delete client
POST   /api/v1/admin/clients/{client_id}/suspend
POST   /api/v1/admin/clients/{client_id}/activate

# System Overview
GET    /api/v1/admin/dashboard/stats            # Global statistics
GET    /api/v1/admin/dashboard/health           # System health
GET    /api/v1/admin/cameras/status             # All cameras status
GET    /api/v1/admin/incidents/recent           # Recent incidents (all clients)
GET    /api/v1/admin/billing/summary            # Revenue summary
```

### 3.3 Client Endpoints (Tenant-Scoped)
```
# Automatically scoped to client_id from JWT/API key

# Dashboard
GET    /api/v1/dashboard/stats
GET    /api/v1/dashboard/alerts

# Cameras
GET    /api/v1/cameras
POST   /api/v1/cameras
GET    /api/v1/cameras/{camera_id}
PUT    /api/v1/cameras/{camera_id}
DELETE /api/v1/cameras/{camera_id}
POST   /api/v1/cameras/{camera_id}/test-connection
GET    /api/v1/cameras/{camera_id}/live-frame

# Incidents
GET    /api/v1/incidents
GET    /api/v1/incidents/{incident_id}
PUT    /api/v1/incidents/{incident_id}/status
GET    /api/v1/incidents/{incident_id}/video-clip

# Watchlist
GET    /api/v1/watchlist
POST   /api/v1/watchlist
DELETE /api/v1/watchlist/{person_id}

# Analytics
GET    /api/v1/analytics/summary
GET    /api/v1/analytics/incidents-by-time
GET    /api/v1/analytics/cameras-performance

# Users (for owner/manager)
GET    /api/v1/users
POST   /api/v1/users
DELETE /api/v1/users/{user_id}
```

---

## 4. AUTHENTICATION & AUTHORIZATION

### 4.1 JWT Token Structure
```json
{
  "sub": "usr_xxxxx",
  "client_id": "cli_xxxxx",
  "role": "manager",
  "permissions": ["view_live", "view_incidents", "manage_cameras"],
  "is_admin": false,
  "iat": 1704067200,
  "exp": 1704153600
}
```

### 4.2 API Key Structure
```
Header: X-API-Key: sg_live_xxxxxxxxxxxxxxxxxxxxx

Decoded contains:
- client_id
- key_id
- permissions
```

### 4.3 Role Hierarchy
```
SUPER_ADMIN (You)
    └── Full access to all clients and system
    
CLIENT_OWNER
    └── Full access to their client's resources
    └── Can manage users, billing
    
CLIENT_MANAGER
    └── Manage cameras, watchlist, review incidents
    └── Cannot manage users or billing
    
CLIENT_VIEWER
    └── View-only access to dashboard, incidents
    
API_ONLY
    └── Programmatic access via API key
```

---

## 5. STREAM PROCESSING PIPELINE

### 5.1 RTSP Ingestion Architecture
```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│   Camera 1     │     │   Camera 2     │     │   Camera N     │
│   RTSP Stream  │     │   RTSP Stream  │     │   RTSP Stream  │
└───────┬────────┘     └───────┬────────┘     └───────┬────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STREAM INGESTION SERVICE                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Stream Manager (per client)                             │   │
│  │  • Connection pool management                            │   │
│  │  • Reconnection with exponential backoff                 │   │
│  │  • Health monitoring                                     │   │
│  │  • Frame rate throttling                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       REDIS FRAME QUEUE                          │
│  Key: frames:{client_id}:{camera_id}                            │
│  TTL: 5 seconds (drop old frames)                               │
│  Structure: { frame_base64, timestamp, camera_id, client_id }   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ML WORKER POOL (Celery/RQ)                    │
│  • Pull frames from queue                                        │
│  • Run YOLO + Pose + Face Recognition                           │
│  • Apply Decision Engine                                         │
│  • Generate alerts                                               │
│  • Store incidents                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Processing Pipeline Code Structure
```python
# Worker process pseudocode
async def process_frame(task):
    frame_data = task.data
    client_id = frame_data['client_id']
    camera_id = frame_data['camera_id']
    
    # 1. Load client settings
    client = await get_client(client_id)
    camera = await get_camera(camera_id)
    
    # 2. Run ML detection
    detections = run_yolo(frame_data['frame'])
    
    # 3. Run pose estimation
    poses = run_pose_estimation(frame_data['frame'], detections)
    
    # 4. Check watchlist (if enabled)
    if camera.detection_settings.enable_face_recognition:
        watchlist = await get_client_watchlist(client_id)
        matches = check_watchlist(frame_data['frame'], watchlist)
    
    # 5. Apply Decision Engine
    threats = decision_engine.analyze(detections, poses, matches)
    
    # 6. Create incident if threshold exceeded
    if threats.max_score > client.settings.detection_sensitivity:
        incident = create_incident(client_id, camera_id, threats, frame_data)
        await save_incident(incident)
        await send_alert(client, incident)
    
    # 7. Update real-time cache
    await update_live_status(client_id, camera_id, {
        'frame': frame_data['frame'],
        'detections': detections,
        'threats': threats,
        'timestamp': now()
    })
```

---

## 6. HORIZONTAL SCALING STRATEGY

### 6.1 Service Scaling Matrix
```
┌─────────────────────┬─────────────────────┬─────────────────────────────┐
│ Service             │ Scaling Trigger     │ Scale Method                │
├─────────────────────┼─────────────────────┼─────────────────────────────┤
│ API Service         │ Requests/sec > 1000 │ Add container replicas      │
│ Stream Ingestion    │ Cameras > 100       │ Add stream workers          │
│ ML Workers          │ Queue depth > 100   │ Add GPU workers             │
│ MongoDB             │ Storage > 80%       │ Add shards                  │
│ Redis               │ Memory > 80%        │ Add cluster nodes           │
└─────────────────────┴─────────────────────┴─────────────────────────────┘
```

### 6.2 Capacity Planning
```
Per Client (Average):
- 16 cameras
- 2 FPS processing per camera = 32 frames/sec
- ~1.5 MB/frame = 48 MB/sec
- 1 incident per 100 frames = 0.32 incidents/sec

For 100 Clients:
- 1,600 cameras
- 3,200 frames/sec to process
- 4.8 GB/sec throughput
- 32 incidents/sec

Recommended Infrastructure:
- 4x API servers (8 CPU, 16GB RAM each)
- 8x Stream workers (4 CPU, 8GB RAM each)
- 16x ML workers (8 CPU, 32GB RAM, GPU each)
- 3x MongoDB replica set (16 CPU, 64GB RAM, 1TB SSD each)
- 3x Redis cluster nodes (8 CPU, 32GB RAM each)
```

---

## 7. DEPLOYMENT ARCHITECTURE

### 7.1 Kubernetes Deployment
```yaml
# Namespace per environment
namespaces:
  - secureguard-prod
  - secureguard-staging

# Deployments
deployments:
  api-service:
    replicas: 4
    resources:
      cpu: "2"
      memory: "4Gi"
    autoscaling:
      minReplicas: 2
      maxReplicas: 10
      targetCPU: 70%
      
  stream-service:
    replicas: 8
    resources:
      cpu: "2"
      memory: "4Gi"
    autoscaling:
      minReplicas: 4
      maxReplicas: 20
      
  ml-worker:
    replicas: 16
    resources:
      cpu: "4"
      memory: "16Gi"
      nvidia.com/gpu: 1
    autoscaling:
      minReplicas: 8
      maxReplicas: 32
      targetGPU: 80%
```

### 7.2 Infrastructure Options
```
Option A: AWS
├── EKS (Kubernetes)
├── DocumentDB (MongoDB compatible)
├── ElastiCache (Redis)
├── S3 (Object storage)
├── CloudFront (CDN)
├── ALB (Load balancer)
└── EC2 p3.2xlarge (GPU instances)

Option B: GCP
├── GKE (Kubernetes)
├── Cloud Firestore / MongoDB Atlas
├── Memorystore (Redis)
├── Cloud Storage
├── Cloud CDN
├── Cloud Load Balancing
└── Compute Engine with T4 GPUs

Option C: Self-Hosted
├── Kubernetes (k3s or Rancher)
├── MongoDB (self-managed cluster)
├── Redis (self-managed cluster)
├── MinIO (S3-compatible storage)
├── NGINX (Load balancer)
└── NVIDIA GPU servers
```

---

## 8. MONITORING & ALERTING

### 8.1 Metrics to Monitor
```
Business Metrics:
- Active clients
- Active cameras
- Incidents per hour
- False positive rate
- Average detection latency

Technical Metrics:
- API response time (p50, p95, p99)
- Queue depth
- ML worker utilization
- GPU memory usage
- Stream connection health
- Database query performance
- Cache hit rate
```

### 8.2 Monitoring Stack
```
Prometheus + Grafana
├── API metrics
├── ML worker metrics
├── Stream health
└── Infrastructure metrics

ELK Stack (Elasticsearch, Logstash, Kibana)
├── Application logs
├── Error tracking
├── Audit logs
└── Security events

PagerDuty / OpsGenie
├── Critical alerts
├── On-call rotation
└── Incident management
```

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Data Security
```
At Rest:
- MongoDB encryption (AES-256)
- S3 server-side encryption
- RTSP credentials encrypted in database

In Transit:
- TLS 1.3 for all API calls
- Encrypted RTSP streams (RTSPS where supported)
- Internal service mesh with mTLS

Access Control:
- JWT with short expiration (1 hour)
- API key rotation support
- IP allowlisting for API keys
- Rate limiting per client
```

### 9.2 Compliance
```
GDPR:
- Data retention policies
- Right to deletion
- Data export capability

SOC 2:
- Audit logging
- Access controls
- Encryption

PCI DSS (if billing):
- Secure payment processing via Stripe
- No card data storage
```

---

## 10. PRICING TIERS

```
┌─────────────────┬─────────────┬─────────────┬─────────────┐
│ Feature         │ Basic       │ Professional│ Enterprise  │
├─────────────────┼─────────────┼─────────────┼─────────────┤
│ Price/month     │ $99         │ $299        │ $799+       │
│ Cameras         │ 4           │ 16          │ 32+         │
│ Users           │ 2           │ 5           │ Unlimited   │
│ Retention       │ 7 days      │ 30 days     │ 90 days     │
│ Live Detection  │ ✓           │ ✓           │ ✓           │
│ Watchlist       │ 10 people   │ 100 people  │ Unlimited   │
│ Analytics       │ Basic       │ Advanced    │ Custom      │
│ API Access      │ ✗           │ ✓           │ ✓           │
│ GPT Analysis    │ ✗           │ ✓           │ ✓           │
│ Webhook Alerts  │ ✗           │ ✓           │ ✓           │
│ Custom Branding │ ✗           │ ✗           │ ✓           │
│ SLA             │ 99%         │ 99.5%       │ 99.9%       │
│ Support         │ Email       │ Priority    │ Dedicated   │
└─────────────────┴─────────────┴─────────────┴─────────────┘
```

---

## 11. IMPLEMENTATION PHASES

### Phase 1: Core Multi-Tenancy (2-3 weeks)
- [ ] Multi-tenant database schema
- [ ] Authentication service (JWT + API keys)
- [ ] Client management API
- [ ] Basic admin dashboard

### Phase 2: Stream Processing (3-4 weeks)
- [ ] RTSP ingestion service
- [ ] Redis queue setup
- [ ] ML worker pool
- [ ] Real-time WebSocket streaming

### Phase 3: Client Dashboard (2-3 weeks)
- [ ] Client self-service portal
- [ ] Camera management UI
- [ ] Incident review workflow
- [ ] Basic analytics

### Phase 4: Scaling & Operations (2-3 weeks)
- [ ] Kubernetes deployment
- [ ] Auto-scaling configuration
- [ ] Monitoring & alerting
- [ ] Backup & disaster recovery

### Phase 5: Advanced Features (Ongoing)
- [ ] Billing integration (Stripe)
- [ ] Custom alerting (WhatsApp, Slack)
- [ ] Advanced analytics
- [ ] White-label option

---

## 12. QUICK START COMMANDS

```bash
# Development setup
docker-compose up -d mongodb redis
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Create first admin user
python scripts/create_admin.py --email admin@secureguard.ai --password secure123

# Create test client
python scripts/create_client.py --name "Test Store" --plan professional

# Run ML workers
celery -A app.workers worker --loglevel=info --concurrency=4

# Run stream service
python -m app.services.stream_ingestion
```
