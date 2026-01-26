# SecureGuard - Multi-Tenant Shoplifting Detection Platform PRD

## Original Problem Statement
Build a shoplifting detection system for liquor stores, convenience stores and gas stations with:
- Upload pre-recorded video files for analysis
- Advanced AI-powered detection with object tracking using OpenAI GPT-5.2 Vision
- On-screen alerts only
- Real-time monitoring dashboard
- Incident history/logs
- Analytics and reporting

### Latest Request: Multi-Tenant SaaS Architecture
Transform into a scalable, multi-tenant platform supporting:
- Multiple clients (stores) with data isolation
- Multiple camera streams per client
- Separate admin/client dashboards
- RBAC: Admin, Client Owner, Client Staff roles

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion + Recharts
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI/ML**: YOLO v8, DeepFace, YOLO Pose, OpenAI GPT-5.2 Vision via Emergent Integrations
- **Auth**: Emergent-managed Google OAuth

## User Personas & Roles
1. **Super Admin**: Full platform access, client management, system monitoring
2. **Client Owner**: Full access to their organization's resources
3. **Client Staff**: View live feed, acknowledge alerts
4. **Client Viewer**: View-only access to dashboard and incidents

## What's Been Implemented

### Phase 1: Core MVP (Completed)
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

### Phase 2: Multi-Tenant Foundation (Completed - January 2026)
- [x] Emergent Google OAuth authentication
- [x] Role-Based Access Control (RBAC)
  - Super Admin, Client Owner, Client Staff, Client Viewer
  - Permission-based access to features
- [x] Admin Dashboard
  - Platform-wide statistics (clients, cameras, incidents, revenue)
  - System health monitoring
  - Quick actions for client management
- [x] Client Management
  - Create/Read/Update/Delete clients
  - Subscription plans (Trial, Basic, Professional, Enterprise)
  - Suspend/Activate clients
- [x] Protected Routes
  - Auth-gated client dashboard
  - Admin-only admin dashboard
- [x] User Profile & Navigation
  - User menu with avatar
  - Role-based navigation items
  - Logout functionality

### Key Files Created/Modified
- `/app/backend/routes/auth.py` - Authentication service with Emergent OAuth
- `/app/backend/routes/admin.py` - Admin routes for client/user management
- `/app/frontend/src/pages/Login.jsx` - Google OAuth login page
- `/app/frontend/src/pages/AuthCallback.jsx` - OAuth callback handler
- `/app/frontend/src/context/AuthContext.jsx` - Auth state management
- `/app/frontend/src/components/Layout.jsx` - Updated with user menu
- `/app/frontend/src/components/AdminLayout.jsx` - Admin sidebar layout
- `/app/frontend/src/pages/admin/AdminDashboard.jsx` - Admin stats dashboard
- `/app/frontend/src/pages/admin/AdminClients.jsx` - Client management UI

## API Endpoints

### Authentication
- `POST /api/auth/session` - Exchange OAuth session_id for session_token
- `GET /api/auth/me` - Get current user with permissions
- `POST /api/auth/logout` - Logout and invalidate session

### Admin (Super Admin only)
- `GET /api/admin/dashboard/stats` - Platform-wide statistics
- `GET /api/admin/system/health` - System health status
- `GET/POST /api/admin/clients` - List/Create clients
- `GET/PUT/DELETE /api/admin/clients/{id}` - Client CRUD
- `POST /api/admin/clients/{id}/suspend` - Suspend client
- `POST /api/admin/clients/{id}/activate` - Activate client
- `GET /api/admin/users` - List all users
- `PUT /api/admin/users/{id}/assign` - Assign user to client
- `GET /api/admin/cameras` - List all cameras
- `GET /api/admin/incidents/recent` - Recent incidents across clients
- `GET/PUT /api/admin/ai/settings` - AI model settings per client

### Client (Authenticated users)
- `GET /api/dashboard/stats` - Client dashboard stats
- `GET/POST /api/videos` - Video management
- `GET /api/incidents` - Incidents for client
- `GET/POST /api/watchlist` - Watchlist management
- `POST /api/live/process-frame` - Live detection

## Database Collections
- `users` - User accounts with roles and permissions
- `user_sessions` - Session tokens (7-day expiry)
- `clients` - Multi-tenant organizations
- `cameras` - Camera configurations per client
- `videos` - Uploaded videos with analysis status
- `incidents` - Detected security events
- `watchlist` - Known individuals for face recognition

## Prioritized Backlog

### P0 (In Progress)
- [ ] Camera management UI in admin dashboard
- [ ] User management UI (assign users to clients)
- [ ] AI Model Control UI per client
- [ ] Tenant-aware data filtering (add client_id to existing endpoints)

### P1 (High Priority)
- [ ] Real RTSP stream ingestion (replace video simulation)
- [ ] WebSocket for real-time detection updates
- [ ] Email/SMS alerts for critical incidents

### P2 (Medium Priority)
- [ ] Billing integration (Stripe)
- [ ] Client self-service portal
- [ ] Video playback with timestamp jumping
- [ ] Export incidents report (PDF/CSV)

### P3 (Low Priority)
- [ ] Custom branding per client
- [ ] Mobile app
- [ ] Advanced analytics per client
- [ ] Webhook integrations

## Testing Credentials
- Test Admin User: `test.admin@example.com`
- Session Token: Use MongoDB to create test sessions
- First user to sign in via Google OAuth becomes Super Admin

## Technical Notes
- Memory usage is high due to ML models (YOLO, DeepFace) - monitor carefully
- Video files are stored permanently in `/app/backend/video_storage/`
- All API responses exclude MongoDB `_id` field
- Session tokens expire after 7 days
- CORS is configured for all origins (restrict in production)
