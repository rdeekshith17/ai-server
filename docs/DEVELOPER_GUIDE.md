# SecureGuard - Complete Developer & Deployment Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Backend Code Notes](#backend-code-notes)
3. [Frontend Code Notes](#frontend-code-notes)
4. [Admin Dashboard Guide](#admin-dashboard-guide)
5. [Client Dashboard Guide](#client-dashboard-guide)
6. [RTSP Camera Integration](#rtsp-camera-integration)
7. [WhatsApp Alerts Setup](#whatsapp-alerts-setup)
8. [Manual Deployment Guide](#manual-deployment-guide)
9. [API Reference](#api-reference)
10. [Environment Variables](#environment-variables)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        SECUREGUARD PLATFORM                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   React.js   │────▶│   FastAPI    │────▶│   MongoDB    │    │
│  │   Frontend   │     │   Backend    │     │   Database   │    │
│  │   (Port 3000)│     │   (Port 8001)│     │              │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │                    │                                  │
│         │                    ├────────────────────┐             │
│         │                    ▼                    ▼             │
│         │             ┌──────────────┐     ┌──────────────┐    │
│         │             │   ML Models  │     │   Twilio     │    │
│         │             │ YOLO/DeepFace│     │  WhatsApp    │    │
│         │             └──────────────┘     └──────────────┘    │
│         │                    │                                  │
│         │                    ▼                                  │
│         │             ┌──────────────┐                         │
│         │             │  GPT-5.2     │                         │
│         └────────────▶│   Vision     │                         │
│                       └──────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn/UI, Framer Motion, Recharts
- **Backend**: FastAPI (Python 3.11), Motor (async MongoDB)
- **Database**: MongoDB
- **AI/ML**: YOLO v8, DeepFace, YOLO Pose, OpenAI GPT-5.2 Vision
- **Auth**: Emergent Google OAuth
- **Alerts**: Twilio WhatsApp API

---

## Backend Code Notes

### Directory Structure
```
/app/backend/
├── server.py           # Main FastAPI application
├── routes/
│   ├── __init__.py    # Route exports
│   ├── auth.py        # Authentication routes
│   ├── admin.py       # Admin management routes
│   └── alerts.py      # WhatsApp alert routes
├── config/
│   └── multi_tenant.py # Multi-tenant configuration
├── models/
│   └── multi_tenant.py # Database models
├── video_storage/     # Uploaded video files
├── requirements.txt   # Python dependencies
└── .env              # Environment variables
```

### Key Files

#### `server.py`
Main application with:
- Video upload & analysis endpoints
- Live detection frame processing
- Dashboard statistics
- Watchlist management
- ML model initialization (lazy loading)

```python
# Key endpoints
POST /api/videos/upload        # Upload video
POST /api/videos/analyze/{id}  # Analyze video with AI
POST /api/live/process-frame   # Process single frame
GET  /api/dashboard/stats      # Dashboard statistics
GET  /api/incidents            # List incidents
POST /api/watchlist            # Add to watchlist
```

#### `routes/auth.py`
Authentication service:
- Emergent Google OAuth integration
- Session management (7-day expiry)
- RBAC with 4 roles: super_admin, client_owner, client_staff, client_viewer
- Permission-based access control

```python
# Key functions
create_auth_routes(db)     # Creates auth router
get_current_user(request)  # Get authenticated user
require_auth(request)      # Require authentication
require_admin(request)     # Require admin role
```

#### `routes/admin.py`
Admin management:
- Client CRUD (create, read, update, delete)
- User management & role assignment
- Camera management
- AI model settings per client
- System health monitoring

#### `routes/alerts.py`
Alert service:
- WhatsApp notifications via Twilio
- Configurable alert triggers (critical/warning)
- Quiet hours support
- Cooldown period to prevent spam
- Alert logging

### Adding New Endpoints

```python
# In server.py
@api_router.get("/your-endpoint")
async def your_endpoint():
    return {"message": "Hello"}

# Or create new route file
# routes/your_routes.py
from fastapi import APIRouter

your_router = APIRouter(prefix="/your", tags=["Your"])

@your_router.get("/endpoint")
async def endpoint():
    return {"data": "value"}

# Add to server.py
from routes import create_your_routes
your_router = create_your_routes(db)
app.include_router(your_router, prefix="/api")
```

---

## Frontend Code Notes

### Directory Structure
```
/app/frontend/src/
├── components/
│   ├── ui/            # Shadcn UI components
│   ├── Layout.jsx     # Client sidebar layout
│   └── AdminLayout.jsx # Admin sidebar layout
├── context/
│   └── AuthContext.jsx # Auth state management
├── pages/
│   ├── Login.jsx      # Login page
│   ├── AuthCallback.jsx # OAuth callback
│   ├── Dashboard.jsx  # Client dashboard
│   ├── LiveFeed.jsx   # Live detection
│   ├── Incidents.jsx  # Incident history
│   ├── Watchlist.jsx  # Face recognition watchlist
│   ├── VideoUpload.jsx # Upload videos
│   ├── Analytics.jsx  # Analytics charts
│   └── admin/
│       ├── AdminDashboard.jsx
│       ├── AdminClients.jsx
│       ├── AdminUsers.jsx
│       ├── AdminCameras.jsx
│       ├── AdminAIControl.jsx
│       └── AdminAlerts.jsx
├── App.js            # Main app with routing
├── App.css           # Global styles
└── index.js          # Entry point
```

### Key Components

#### `AuthContext.jsx`
```jsx
import { useAuth } from "../context/AuthContext";

function MyComponent() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  
  if (!isAuthenticated) return <Redirect to="/login" />;
  
  return <div>Welcome, {user.name}</div>;
}
```

#### `ProtectedRoute`
```jsx
// Require authentication
<ProtectedRoute>
  <Dashboard />
</ProtectedRoute>

// Require admin role
<ProtectedRoute requireAdmin>
  <AdminDashboard />
</ProtectedRoute>
```

### Adding New Pages

1. Create component in `/pages/`:
```jsx
// pages/NewPage.jsx
import { useState, useEffect } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function NewPage() {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    axios.get(`${API}/endpoint`, { withCredentials: true })
      .then(res => setData(res.data));
  }, []);
  
  return <div>{/* Your UI */}</div>;
}
```

2. Add route in `App.js`:
```jsx
import NewPage from "./pages/NewPage";

// Inside Routes
<Route path="new-page" element={<NewPage />} />
```

3. Add navigation in `Layout.jsx` or `AdminLayout.jsx`:
```jsx
const navItems = [
  // existing items...
  { path: "/new-page", icon: IconComponent, label: "New Page" },
];
```

---

## Admin Dashboard Guide

### Access
- URL: `/admin`
- Requires: `super_admin` role
- First user to sign in becomes super_admin

### Features

#### Dashboard (`/admin`)
- Total clients, cameras, incidents (24h)
- Monthly revenue calculation
- Recent clients list
- Recent incidents list
- System status indicators

#### Client Management (`/admin/clients`)
- Create new clients with subscription plans
- View client details (cameras, users, incidents)
- Suspend/activate clients
- Delete clients (cascades to all data)

#### User Management (`/admin/users`)
- View all platform users
- Assign users to clients
- Update user roles
- Filter by role/client

#### Camera Management (`/admin/cameras`)
- Add cameras to clients
- Configure RTSP URLs
- Set detection sensitivity
- Enable/disable cameras
- Monitor online/offline status

#### AI Control (`/admin/ai-control`)
- Enable/disable models per client:
  - YOLO v8 (person detection)
  - DeepFace (face recognition)
  - Pose Estimation (body posture)
  - GPT-5.2 Vision (behavior analysis)
- Adjust detection sensitivity
- Set threat threshold

#### Alerts (`/admin/alerts`)
- Enable WhatsApp notifications
- Configure alert triggers (critical/warning)
- Add recipient phone numbers
- Set quiet hours
- Set cooldown period
- Send test alerts
- View alert log

---

## Client Dashboard Guide

### Access
- URL: `/`
- Requires: Any authenticated user

### Features

#### Dashboard (`/`)
- Video analysis statistics
- Incident severity breakdown
- Recent incidents
- ML model status

#### Live Detection (`/live`)
- Real-time video processing
- Detection overlays (bounding boxes, pose skeletons)
- Threat assessment indicators
- Stop/pause controls

#### Video Upload (`/upload`)
- Drag & drop video files
- Support: MP4, MOV, AVI, WEBM
- Upload progress indicator
- Analysis trigger

#### Incidents (`/incidents`)
- Full incident history
- Severity filtering
- Search functionality
- Detailed incident view with:
  - Frame image
  - Behaviors detected
  - Confidence scores
  - Watchlist matches

#### Watchlist (`/watchlist`)
- Add known individuals
- Upload reference photos
- Set threat levels
- DeepFace auto-encodes faces

#### Analytics (`/analytics`)
- Incident trends chart
- Severity distribution
- Time-based analysis

---

## RTSP Camera Integration

### What is RTSP?
RTSP (Real Time Streaming Protocol) is a standard for streaming video from IP cameras.

### Finding Your Camera's RTSP URL

#### Generic Format
```
rtsp://[username]:[password]@[ip_address]:[port]/[stream_path]
```

#### Common Examples by Brand

**Hikvision:**
```
rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101
```

**Dahua:**
```
rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0
```

**Amcrest:**
```
rtsp://admin:password@192.168.1.200:554/cam/realmonitor?channel=1&subtype=0
```

**Reolink:**
```
rtsp://admin:password@192.168.1.80:554/h264Preview_01_main
```

**Axis:**
```
rtsp://root:password@192.168.1.50:554/axis-media/media.amp
```

**Generic ONVIF:**
```
rtsp://admin:password@192.168.1.100:554/onvif1
```

### How to Find Your RTSP URL

1. **Check Camera Manual**: Look for "RTSP URL" or "Stream URL"

2. **Use Camera's Web Interface**:
   - Open browser, go to camera IP
   - Look in Settings → Network → RTSP

3. **Use ONVIF Device Manager**:
   - Download: https://sourceforge.net/projects/onvifdm/
   - Scan network for cameras
   - View stream URLs

4. **Use VLC to Test**:
   - Open VLC → Media → Open Network Stream
   - Enter RTSP URL
   - If video plays, URL is correct

### Adding RTSP Camera in SecureGuard

1. Go to Admin → Cameras
2. Click "Add Camera"
3. Select client
4. Enter camera name and location
5. Enter RTSP URL
6. Set detection sensitivity
7. Click "Create Camera"

### Network Requirements

- Camera and server must be on same network (or VPN)
- Port 554 (RTSP default) must be accessible
- Firewall must allow RTSP traffic
- For remote access, use port forwarding or VPN

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check IP, port, firewall |
| Auth failed | Verify username/password |
| No video | Check stream path |
| Lag/buffering | Use substream (lower quality) |
| Camera offline | Check power, network |

---

## WhatsApp Alerts Setup

### Prerequisites
- Twilio account
- Verified phone number

### Step 1: Create Twilio Account
1. Go to https://www.twilio.com/
2. Sign up for free trial
3. Verify your phone number

### Step 2: Enable WhatsApp Sandbox
1. Login to Twilio Console
2. Go to Messaging → Try it out → Send a WhatsApp message
3. Follow instructions to join sandbox:
   - Send "join [your-sandbox-code]" to +1 415 523 8886

### Step 3: Get Credentials
1. Go to Twilio Console Dashboard
2. Copy your:
   - Account SID (starts with AC...)
   - Auth Token (click to reveal)

### Step 4: Configure Backend
Add to `/app/backend/.env`:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### Step 5: Restart Backend
```bash
sudo supervisorctl restart backend
```

### Step 6: Configure Alerts
1. Go to Admin → Alerts
2. Select client
3. Enable alerts
4. Add WhatsApp numbers (must have joined sandbox)
5. Configure trigger rules
6. Send test alert

### Production WhatsApp
For production, upgrade to Twilio WhatsApp Business:
1. Apply for WhatsApp Business API
2. Get dedicated number
3. Update `TWILIO_WHATSAPP_FROM` in .env

---

## Manual Deployment Guide

### Option 1: Deploy to VPS (DigitalOcean, AWS EC2, etc.)

#### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm mongodb nginx git

# Install yarn
npm install -g yarn
```

#### 2. Clone Repository
```bash
# From Emergent, download code or push to GitHub first
git clone https://github.com/your-username/secureguard.git
cd secureguard
```

#### 3. Backend Setup
```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your values:
# - MONGO_URL=mongodb://localhost:27017
# - EMERGENT_API_KEY=your_key
# - TWILIO credentials if using alerts
```

#### 4. Frontend Setup
```bash
cd ../frontend

# Install dependencies
yarn install

# Create .env file
echo "REACT_APP_BACKEND_URL=https://your-domain.com" > .env

# Build for production
yarn build
```

#### 5. Nginx Configuration
```nginx
# /etc/nginx/sites-available/secureguard
server {
    listen 80;
    server_name your-domain.com;

    # Frontend (React build)
    location / {
        root /var/www/secureguard/frontend/build;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/secureguard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 6. SSL with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### 7. Run Backend with PM2
```bash
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'secureguard-backend',
    cwd: '/var/www/secureguard/backend',
    script: 'venv/bin/uvicorn',
    args: 'server:app --host 0.0.0.0 --port 8001',
    env: {
      NODE_ENV: 'production',
    },
  }]
}
EOF

pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Option 2: Deploy with Docker

#### Dockerfile (Backend)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### Dockerfile (Frontend)
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install
COPY . .
RUN yarn build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

#### docker-compose.yml
```yaml
version: '3.8'
services:
  mongodb:
    image: mongo:6
    volumes:
      - mongo-data:/data/db
    ports:
      - "27017:27017"

  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://mongodb:27017
    depends_on:
      - mongodb

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mongo-data:
```

```bash
docker-compose up -d
```

### Push to GitHub

#### From Emergent Platform
1. Click "Save to GitHub" in chat input
2. Follow OAuth flow
3. Select repository

#### Manual Push
```bash
# Initialize git if needed
git init
git add .
git commit -m "Initial commit"

# Add remote
git remote add origin https://github.com/your-username/secureguard.git
git branch -M main
git push -u origin main
```

---

## API Reference

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/session` | POST | Exchange OAuth session_id |
| `/api/auth/me` | GET | Get current user |
| `/api/auth/logout` | POST | Logout user |

### Admin Routes
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/dashboard/stats` | GET | Platform statistics |
| `/api/admin/system/health` | GET | System health |
| `/api/admin/clients` | GET/POST | List/Create clients |
| `/api/admin/clients/{id}` | GET/PUT/DELETE | Client CRUD |
| `/api/admin/users` | GET | List users |
| `/api/admin/users/{id}/assign` | PUT | Assign user to client |
| `/api/admin/cameras` | GET/POST | List/Create cameras |
| `/api/admin/ai/settings/{id}` | GET | Get AI settings |
| `/api/admin/ai/settings` | PUT | Update AI settings |

### Alert Routes
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts/settings/{id}` | GET | Get alert settings |
| `/api/alerts/settings` | PUT | Update alert settings |
| `/api/alerts/test` | POST | Send test alert |
| `/api/alerts/log/{id}` | GET | Get alert history |
| `/api/alerts/status` | GET | Twilio status |

### Video & Detection
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/videos/upload` | POST | Upload video |
| `/api/videos/analyze/{id}` | POST | Analyze video |
| `/api/live/process-frame` | POST | Process frame |
| `/api/incidents` | GET | List incidents |
| `/api/watchlist` | GET/POST | Watchlist CRUD |
| `/api/dashboard/stats` | GET | Dashboard stats |
| `/api/ml/status` | GET | ML model status |

---

## Environment Variables

### Backend (`/app/backend/.env`)
```env
# Required
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
EMERGENT_API_KEY=your_emergent_key_here

# Optional - WhatsApp Alerts
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Optional - CORS (comma-separated)
CORS_ORIGINS=*
```

### Frontend (`/app/frontend/.env`)
```env
REACT_APP_BACKEND_URL=https://your-domain.com
```

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
tail -f /var/log/supervisor/backend.err.log

# Common issues:
# - Missing dependencies: pip install -r requirements.txt
# - Port in use: lsof -i :8001
# - MongoDB not running: sudo systemctl start mongodb
```

### Frontend build fails
```bash
# Clear cache and reinstall
rm -rf node_modules yarn.lock
yarn install
yarn build
```

### Auth not working
- Check EMERGENT_API_KEY in backend .env
- Verify OAuth callback URL matches
- Check browser cookies (session_token)

### WhatsApp alerts not sending
- Verify TWILIO credentials
- Recipient must join sandbox first
- Check alert log for errors

---

## Support
- Documentation: `/app/docs/`
- PRD: `/app/memory/PRD.md`
- Architecture: `/app/docs/MULTI_TENANT_ARCHITECTURE.md`
