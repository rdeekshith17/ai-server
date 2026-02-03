# SecureGuard Central Server

Lightweight API server for the SecureGuard multi-tenant SaaS platform. This server handles all management, authentication, and data storage while ML processing runs on Edge Devices at client locations.

## Features

- **Authentication**: Emergent Google OAuth integration
- **Admin Dashboard**: Manage clients, users, cameras, and AI settings
- **Edge Device Management**: Provision and monitor edge devices
- **Incident Storage**: Receive and store incidents from edge devices
- **Role-Based Access Control**: Super Admin, Client Owner, Client Staff, Client Viewer
- **React Frontend**: Built-in admin dashboard UI

## Quick Start

### Option 1: Using Setup Script

```bash
# Make script executable
chmod +x setup.sh

# Run setup (builds frontend and installs dependencies)
./setup.sh

# Start the server
python server.py
```

### Option 2: Manual Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Build the React frontend (from /app/frontend directory)
cd ../frontend
yarn install && yarn build

# Copy build to central-server
mkdir -p frontend
cp -r ../frontend/build frontend/

# Start the server
python server.py
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `secureguard_central` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `CENTRAL_SERVER_URL` | Public URL of this server | - |
| `API_KEY_SALT` | Salt for API key hashing | `secureguard` |

## API Endpoints

### Authentication
- `POST /api/auth/session` - Process OAuth callback
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Admin Dashboard
- `GET /api/admin/dashboard/stats` - Dashboard statistics
- `GET /api/admin/system/health` - System health

### Client Management
- `GET /api/admin/clients` - List clients
- `POST /api/admin/clients` - Create client
- `GET /api/admin/clients/{client_id}` - Get client details
- `PUT /api/admin/clients/{client_id}` - Update client
- `DELETE /api/admin/clients/{client_id}` - Delete client

### Edge Device Management
- `POST /api/admin/edge-devices/provision` - Provision new device
- `GET /api/admin/edge-devices` - List all devices

### Edge Device API (called by edge devices)
- `POST /api/edge/register` - Register device
- `POST /api/edge/heartbeat` - Send heartbeat
- `POST /api/edge/incidents` - Upload incident

## First Login

1. Navigate to `http://your-server:8001`
2. Click "Sign in with Google"
3. The **first user** to log in becomes the **Super Admin**
4. Subsequent users get the "Client Viewer" role (admins can promote them)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CENTRAL SERVER (Cloud)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   FastAPI   │  │   MongoDB   │  │   React Frontend    │   │
│  │   Backend   │──│   Database  │  │   (Admin Dashboard) │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
│         │                                      │              │
│         │  ◄──── Incidents/Heartbeats ────────┤              │
│         │                                      │              │
└─────────┼──────────────────────────────────────┼──────────────┘
          │                                      │
          ▼                                      ▼
┌─────────────────────┐              ┌─────────────────────┐
│   EDGE DEVICE #1    │              │   EDGE DEVICE #2    │
│  ┌───────────────┐  │              │  ┌───────────────┐  │
│  │ ML Processing │  │              │  │ ML Processing │  │
│  │ YOLO/DeepFace │  │              │  │ YOLO/DeepFace │  │
│  │ GPT-5.2 Vision│  │              │  │ GPT-5.2 Vision│  │
│  └───────────────┘  │              │  └───────────────┘  │
│         │           │              │         │           │
│         ▼           │              │         ▼           │
│  ┌───────────────┐  │              │  ┌───────────────┐  │
│  │ RTSP Cameras  │  │              │  │ RTSP Cameras  │  │
│  └───────────────┘  │              │  └───────────────┘  │
└─────────────────────┘              └─────────────────────┘
     Client Site A                        Client Site B
```

## Development

```bash
# Run with auto-reload
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

## Production Deployment

For production, consider:

1. **Use a proper WSGI server**: gunicorn with uvicorn workers
2. **Set up HTTPS**: Use nginx as a reverse proxy with SSL
3. **Configure MongoDB**: Use MongoDB Atlas or a secured instance
4. **Set secure environment variables**: Don't use default API_KEY_SALT

```bash
# Production command example
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```
