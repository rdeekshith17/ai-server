# SecureGuard Architecture Clarification
## What Gets Deployed Where?

---

# THE CONFUSION

The previous docs (`LOCAL_DEPLOYMENT.md`, `SERVER_CLIENT_SETUP.md`) were for deploying the **FULL application** at one location. 

For **multi-tenant SaaS across multiple states**, you need **TWO DIFFERENT deployments**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR SETUP (Multi-State SaaS)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   CENTRAL SERVER              EDGE DEVICES                       │
│   (Columbus, Ohio)            (At Each Client)                   │
│   ┌──────────────┐            ┌──────────────┐                  │
│   │ Dashboard    │            │ YOLO         │                  │
│   │ Auth         │◄──────────►│ DeepFace     │                  │
│   │ Database     │  Sync API  │ Pose Est.    │                  │
│   │ Alerts       │            │ GPT Vision   │                  │
│   │ Billing      │            │ Camera Feed  │                  │
│   │              │            │              │                  │
│   │ NO ML MODELS │            │ NO DASHBOARD │                  │
│   └──────────────┘            └──────────────┘                  │
│                                                                  │
│   Deploy ONCE                 Deploy at EACH client             │
└─────────────────────────────────────────────────────────────────┘
```

---

# WHAT GETS DEPLOYED WHERE

## 1. CENTRAL SERVER (Your Columbus Office or VPS)

**Deploy ONCE for your entire business**

| Component | Included | Notes |
|-----------|----------|-------|
| Admin Dashboard | ✅ | Manage all clients |
| Client Dashboard | ✅ | Clients view their data |
| Authentication | ✅ | Google OAuth |
| MongoDB Database | ✅ | All incidents stored here |
| WhatsApp Alerts | ✅ | Send notifications |
| User Management | ✅ | RBAC |
| Billing (Stripe) | ✅ | Subscriptions |
| API Gateway | ✅ | Edge devices connect here |
| **YOLO** | ❌ | Not needed |
| **DeepFace** | ❌ | Not needed |
| **Pose Estimation** | ❌ | Not needed |
| **GPT Vision** | ❌ | Called from edge |
| **Video Storage** | ❌ | Stays at client |

**Server Requirements:**
- 2-4 vCPU, 4-8GB RAM
- ~$40-80/month VPS
- No GPU needed!

---

## 2. EDGE DEVICE (At Each Client Location)

**Deploy at EVERY client store**

| Component | Included | Notes |
|-----------|----------|-------|
| Admin Dashboard | ❌ | Use central server |
| Client Dashboard | ❌ | Use central server |
| Authentication | ❌ | Use central server |
| MongoDB | ⚠️ | Local cache only (7 days) |
| WhatsApp Alerts | ❌ | Central server sends |
| **YOLO** | ✅ | Person detection |
| **DeepFace** | ✅ | Face recognition |
| **Pose Estimation** | ✅ | Body posture |
| **GPT Vision** | ✅ | Behavior analysis |
| **Video Processing** | ✅ | RTSP capture |
| **Camera Access** | ✅ | Local network |

**Hardware Requirements:**
- Mini PC: $300-500
- 4+ cores, 16GB RAM
- Optional: GPU for faster processing

---

# CORRECTED DEPLOYMENT GUIDE

## Step 1: Central Server (Do This FIRST, Only ONCE)

```bash
# On your VPS (DigitalOcean, etc.)

# Clone the repo
git clone https://github.com/YOUR_USER/secureguard.git
cd secureguard

# Use the CLOUD version (no ML)
cd central-server  # We'll create this

# Install lightweight dependencies
pip install fastapi uvicorn motor httpx twilio stripe

# NO tensorflow, pytorch, ultralytics, deepface!

# Run
uvicorn server:app --host 0.0.0.0 --port 8001
```

## Step 2: Edge Device (Do This at EACH Client)

```bash
# On the mini PC at client location

# Clone the repo
git clone https://github.com/YOUR_USER/secureguard.git
cd secureguard

# Use the EDGE version (ML only)
cd edge-device  # We'll create this

# Install ML dependencies
pip install ultralytics deepface opencv-python

# Configure connection to central server
echo "CENTRAL_SERVER_URL=https://your-central-server.com" >> .env
echo "CLIENT_ID=cli_xxxxx" >> .env
echo "API_KEY=xxxxx" >> .env

# Run
python edge_processor.py
```

---

# AUTO-PROVISIONING FLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                     AUTO-PROVISIONING FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. ADMIN creates client in dashboard                           │
│     └─► System generates: client_id + api_key                   │
│                                                                  │
│  2. ADMIN ships pre-configured edge device to client            │
│     └─► Device has install script + credentials                 │
│                                                                  │
│  3. CLIENT plugs in device, connects to network                 │
│     └─► Device auto-starts, connects to central server          │
│                                                                  │
│  4. DEVICE registers cameras automatically                       │
│     └─► Scans network for RTSP cameras                          │
│     └─► Or client enters camera IPs in local web UI             │
│                                                                  │
│  5. DETECTION starts automatically                               │
│     └─► Incidents sync to central server                        │
│     └─► Alerts sent via WhatsApp                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

# SUMMARY: WHAT GOES WHERE

| Item | Central Server | Edge Device |
|------|---------------|-------------|
| Location | Columbus (your office/VPS) | Each client store |
| Quantity | 1 | Many (1 per client) |
| Cost | $50-100/mo | $350 one-time each |
| Dashboard | ✅ Yes | ❌ No |
| Database | ✅ Yes (main) | ⚠️ Cache only |
| ML Models | ❌ No | ✅ Yes |
| Cameras | ❌ No access | ✅ Direct access |
| Alerts | ✅ Sends | ❌ No |
| Internet | Always online | Can work offline |

---

# WHICH DOCS TO USE

| Document | Use For |
|----------|---------|
| `CENTRAL_SERVER_SETUP.md` | Setting up YOUR server (once) |
| `EDGE_DEVICE_SETUP.md` | Setting up CLIENT devices |
| ~~`LOCAL_DEPLOYMENT.md`~~ | Outdated - was for single location |
| ~~`SERVER_CLIENT_SETUP.md`~~ | Outdated - was for single location |

I'll create the correct separated documentation now.
