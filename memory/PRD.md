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
- **Frontend**: React 18, TailwindCSS, Shadcn/UI, Framer Motion, Recharts
- **Backend**: FastAPI (Python 3.11), Motor (async MongoDB)
- **Database**: MongoDB
- **AI/ML**: YOLO v8, DeepFace, YOLO Pose, OpenAI GPT-5.2 Vision
- **Auth**: Emergent-managed Google OAuth
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
- [x] Role-Based Access Control (RBAC)
- [x] Admin Dashboard with platform stats
- [x] Client Management (CRUD)
- [x] Protected Routes (auth-gated)
- [x] User Profile & Navigation

### Phase 3: Admin Features ✅ (January 2026)
- [x] Camera Management UI
  - Add/edit/delete cameras
  - RTSP URL configuration
  - Detection sensitivity settings
  - Online/offline status
- [x] User Management UI
  - Assign users to clients
  - Update user roles
  - Filter by role/client
- [x] AI Model Control UI
  - Enable/disable models per client
  - YOLO, DeepFace, Pose, GPT toggles
  - Detection sensitivity slider
  - Threat threshold configuration
- [x] WhatsApp Alert Settings
  - Enable/disable alerts per client
  - Configure trigger rules (critical/warning)
  - Add/remove recipient numbers
  - Quiet hours configuration
  - Cooldown period setting
  - Test alert functionality
  - Alert history log

---

## Key Files Created

### Backend
- `/app/backend/routes/auth.py` - Authentication service
- `/app/backend/routes/admin.py` - Admin management routes
- `/app/backend/routes/alerts.py` - WhatsApp alert service

### Frontend
- `/app/frontend/src/pages/Login.jsx` - Google OAuth login
- `/app/frontend/src/pages/AuthCallback.jsx` - OAuth callback
- `/app/frontend/src/context/AuthContext.jsx` - Auth state
- `/app/frontend/src/components/AdminLayout.jsx` - Admin sidebar
- `/app/frontend/src/pages/admin/AdminDashboard.jsx`
- `/app/frontend/src/pages/admin/AdminClients.jsx`
- `/app/frontend/src/pages/admin/AdminCameras.jsx`
- `/app/frontend/src/pages/admin/AdminUsers.jsx`
- `/app/frontend/src/pages/admin/AdminAIControl.jsx`
- `/app/frontend/src/pages/admin/AdminAlerts.jsx`

### Documentation
- `/app/docs/DEVELOPER_GUIDE.md` - Complete developer guide
- `/app/docs/MULTI_TENANT_ARCHITECTURE.md` - Architecture design

---

## API Endpoints

### Authentication
- `POST /api/auth/session` - Exchange OAuth session
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Admin
- `GET /api/admin/dashboard/stats` - Platform stats
- `GET /api/admin/system/health` - System health
- `GET/POST /api/admin/clients` - Client CRUD
- `GET/POST /api/admin/cameras` - Camera CRUD
- `GET /api/admin/users` - User management
- `GET/PUT /api/admin/ai/settings` - AI settings

### Alerts
- `GET/PUT /api/alerts/settings/{client_id}` - Alert config
- `POST /api/alerts/test` - Send test alert
- `GET /api/alerts/log/{client_id}` - Alert history
- `GET /api/alerts/status` - Twilio status

---

## Prioritized Backlog

### P0 - Completed ✅
- ~~Camera Management UI~~
- ~~User Management UI~~
- ~~AI Model Control UI~~
- ~~WhatsApp Alerts~~

### P1 (High Priority) - Next
- [ ] Tenant-aware data filtering (add client_id to video/incident endpoints)
- [ ] Real RTSP stream ingestion (replace video simulation)
- [ ] WebSocket for real-time detection updates

### P2 (Medium Priority)
- [ ] Billing integration (Stripe)
- [ ] Client self-service portal
- [ ] Video playback with timestamp jumping
- [ ] Export incidents report (PDF/CSV)
- [ ] Client onboarding wizard

### P3 (Low Priority)
- [ ] Custom branding per client
- [ ] Mobile app
- [ ] Advanced analytics per client
- [ ] Webhook integrations

---

## Environment Variables

### Backend (.env)
```env
MONGO_URL=mongodb://...
DB_NAME=test_database
EMERGENT_API_KEY=your_key

# Optional - WhatsApp Alerts
TWILIO_ACCOUNT_SID=ACxxxxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### Frontend (.env)
```env
REACT_APP_BACKEND_URL=https://your-domain.com
```

---

## Testing Credentials
- First user to sign in via Google OAuth becomes Super Admin
- Create test users via MongoDB for testing

## Technical Notes
- Memory usage is high due to ML models - monitor carefully
- Video files stored in `/app/backend/video_storage/`
- All API responses exclude MongoDB `_id` field
- Session tokens expire after 7 days
