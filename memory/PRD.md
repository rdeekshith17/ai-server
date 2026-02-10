# SecureGuard - Multi-Tenant Shoplifting Detection Platform PRD

## Original Problem Statement
Build a shoplifting detection system for liquor stores, convenience stores and gas stations with:
- Upload pre-recorded video files for analysis
- Advanced AI-powered detection with object tracking using OpenAI GPT-5.2 Vision
- Multi-model ML pipeline: YOLO v8, DeepFace, Pose Estimation
- On-screen alerts and WhatsApp notifications
- Real-time monitoring dashboard
- Incident history/logs
- Analytics and reporting
- Multi-tenant SaaS architecture with RBAC

## Architecture
- **Central Server**: FastAPI backend for management, auth, client dashboard, incident storage
- **Edge Device**: On-premise ML processor that connects to RTSP cameras and runs detection
- **Frontend**: React 18, TailwindCSS, Shadcn/UI, Framer Motion, Recharts
- **Database**: MongoDB
- **AI/ML**: YOLO v8, DeepFace, YOLO Pose, OpenAI GPT-5.2 Vision (runs on edge devices)
- **Auth**: Emergent-managed Google OAuth + Email/Password
- **Alerts**: Twilio WhatsApp API (configurable per client)

## User Personas & Roles
1. **Super Admin**: Full platform access, client management, system monitoring
2. **Client Owner**: Full access to their organization's resources
3. **Client Staff**: View live feed, acknowledge alerts
4. **Client Viewer**: View-only access to dashboard and incidents

---

## What's Been Implemented

### Phase 1: Core MVP ✅
- [x] Video upload (MP4, MOV, AVI, WEBM)
- [x] AI-powered frame analysis using GPT-5.2 Vision
- [x] Multi-model detection (YOLO, DeepFace, Pose Estimation)
- [x] Shoplifting behavior detection
- [x] Incident logging with severity levels
- [x] Real-time dashboard with stats
- [x] Analytics with charts (Recharts)
- [x] Live Detection with visual overlays
- [x] Watchlist management with face recognition
- [x] Decision Engine for threat assessment

### Phase 2: Multi-Tenant Foundation ✅ (January 2026)
- [x] Emergent Google OAuth authentication
- [x] Email/Password authentication
- [x] Role-Based Access Control (RBAC)
- [x] Admin Dashboard with platform stats
- [x] Client Management (CRUD)
- [x] Protected Routes (auth-gated)
- [x] User Profile & Navigation

### Phase 3: Central/Edge Architecture ✅ (February 2026)
- [x] Central Server (lightweight API, no ML)
- [x] Edge Device framework with RTSP camera support
- [x] Edge config API: `/api/edge/config/{client_id}` - Returns cameras with RTSP URLs
- [x] Edge registration: `/api/edge/register`
- [x] Edge heartbeat: `/api/edge/heartbeat`
- [x] Incident upload from edge: `/api/edge/incidents`
- [x] Camera Management with RTSP URL field
- [x] AI Model Control per client

### Phase 4: Settings & Configuration ✅ (February 10, 2026)
- [x] Admin Profile Settings - save to API
- [x] Admin System Settings - maintenance mode, registrations, email verification
- [x] Admin Notification Settings - per-admin preferences
- [x] Client Detection Settings - sensitivity, pose, face, GPT analysis
- [x] Client Alert Settings - email, WhatsApp notifications
- [x] Twilio WhatsApp integration (backend ready, UI done)

---

## Key API Endpoints

### Authentication
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - Email/password login
- `POST /api/auth/session` - Google OAuth callback
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Settings (NEW)
- `PUT /api/users/{user_id}/profile` - Update user profile
- `GET /api/admin/system/settings` - Get system settings
- `PUT /api/admin/system/settings` - Update system settings
- `GET /api/admin/notifications/settings` - Get admin notification prefs
- `PUT /api/admin/notifications/settings` - Update admin notification prefs
- `GET /api/client/detection-settings/{client_id}` - Get detection settings
- `PUT /api/client/detection-settings/{client_id}` - Update detection settings
- `GET /api/alerts/settings/{client_id}` - Get alert settings
- `PUT /api/alerts/settings/{client_id}` - Update alert settings

### Edge Device
- `GET /api/edge/config/{client_id}` - Get full config including cameras with RTSP URLs
- `POST /api/edge/register` - Register edge device
- `POST /api/edge/heartbeat` - Send health data
- `POST /api/edge/incidents` - Upload detected incidents

### Admin
- `GET /api/admin/dashboard/stats` - Dashboard statistics
- `GET /api/admin/clients` - List clients
- `POST /api/admin/clients` - Create client
- `GET /api/admin/cameras` - List cameras
- `POST /api/admin/cameras` - Create camera with RTSP URL
- `PUT /api/admin/ai/settings` - Update AI settings per client

---

## Test Credentials
- **Admin**: test@admin.com / test123 (super_admin)
- **Test Client**: cli_778fc2f73915 (Test Store - professional plan)
- **Edge API Key**: sg_edge_yd4x6l4mnru-Zo9Z5Q634whLw7Y4yhDAalhGA5NyF3Y

---

## Prioritized Backlog

### P0 - Critical
- [ ] Test edge device RTSP connection to real cameras

### P1 - High Priority
- [ ] Refactor `server.py` (2000+ lines) into modules (routes/, models/, services/)
- [ ] Code cleanup: Remove deprecated `/app/backend.old` files
- [ ] Frontend lint warnings fix (useEffect dependencies)

### P2 - Medium Priority
- [ ] ML model fine-tuning controls on client dashboard
- [ ] Email integration for alerts (SendGrid/Resend)
- [ ] Billing/subscription management
- [ ] Incident video clip storage

### P3 - Future
- [ ] Mobile app notifications
- [ ] Custom branding per client
- [ ] API rate limiting
- [ ] Audit logs

---

## Files Structure
```
/app/
├── backend/           # Central server (copies from central-server)
│   ├── server.py      # Monolithic API (to be refactored)
│   ├── tests/         # Pytest tests
│   └── requirements.txt
├── central-server/    # Original central server code
├── edge-device/       # On-premise ML processor
│   ├── edge_processor.py
│   └── requirements.txt
├── frontend/          # React app
│   └── src/
│       ├── pages/
│       │   ├── admin/  # Admin pages
│       │   └── Settings.jsx  # Client settings
│       └── context/
└── docs/              # Documentation & presentations
```

---

## Change Log

### February 10, 2026
- Fixed all settings save buttons (Profile, Detection, Alerts, System, Notifications)
- Added `/api/edge/config/{client_id}` endpoint for edge devices to fetch cameras with RTSP URLs
- Added `/api/users/{user_id}/profile` endpoint
- Added `/api/admin/system/settings` and `/api/admin/notifications/settings` endpoints
- Added `/api/client/detection-settings/{client_id}` endpoint
- All 21 backend API tests passed
- All frontend save buttons verified working
