# SecureGuard - Shoplifting Detection System PRD

## Original Problem Statement
Build a shoplifting detection system for liquor stores, convenience stores and gas stations with:
- Upload pre-recorded video files for analysis
- Advanced AI-powered detection with object tracking using OpenAI GPT-5.2 Vision
- On-screen alerts only
- Real-time monitoring dashboard
- Incident history/logs
- Analytics and reporting

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion + Recharts
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: OpenAI GPT-5.2 Vision via Emergent Integrations

## User Personas
1. **Store Owner**: Monitors overall security, reviews incidents
2. **Security Personnel**: Real-time monitoring, incident response
3. **Loss Prevention Team**: Analytics review, pattern identification

## Core Requirements (Static)
- [x] Video upload (MP4, MOV, AVI, WEBM)
- [x] AI-powered frame analysis using GPT-5.2 Vision
- [x] Shoplifting behavior detection
- [x] Incident logging with severity levels
- [x] Real-time dashboard with stats
- [x] Analytics with charts (Recharts)
- [x] Incident filtering and search

## What's Been Implemented (December 2025)
### Backend
- Video upload endpoint with file validation
- Frame extraction using OpenCV
- GPT-5.2 Vision integration for behavior analysis
- Incident CRUD operations
- Analytics aggregation
- Dashboard stats API

### Frontend
- Security-themed dark dashboard (Rajdhani/Manrope fonts)
- Video upload with drag-drop
- Analysis progress tracking
- Incidents list with filtering
- Analytics charts
- Responsive sidebar navigation

### Detection Capabilities
- Concealment behavior
- Unusual item handling
- Group coordination
- Loitering detection
- Nervous behavior patterns
- Quick grabbing motions

## Prioritized Backlog
### P0 (Critical)
- ✅ Core video upload and analysis
- ✅ AI detection integration
- ✅ Incident logging

### P1 (High)
- [ ] Live camera feed integration (RTSP)
- [ ] Email/SMS alerts
- [ ] User authentication

### P2 (Medium)
- [ ] Multiple camera support
- [ ] Video playback with timestamp jumping
- [ ] Export incidents report (PDF/CSV)

### P3 (Low)
- [ ] Mobile app
- [ ] Multi-store support
- [ ] Employee tracking

## Next Tasks
1. Add live camera feed support (RTSP streams)
2. Implement email notifications via SendGrid
3. Add user authentication
4. Video playback with incident timestamp markers
5. Export functionality for compliance reporting
