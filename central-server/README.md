# Central Server for SecureGuard SaaS
## Lightweight Dashboard & API (No ML Models)

---

# OVERVIEW

This is the **CENTRAL SERVER** component that YOU deploy once.
- Runs in Columbus, Ohio (or any VPS)
- Handles: Dashboard, Auth, Database, Alerts, Billing
- Does NOT run: YOLO, DeepFace, or any ML models
- Receives incidents from Edge Devices at client locations

---

# QUICK INSTALL

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USER/secureguard.git
cd secureguard/central-server

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies (lightweight - no ML!)
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# 5. Start MongoDB
sudo systemctl start mongod

# 6. Run server
uvicorn server:app --host 0.0.0.0 --port 8001
```

---

# REQUIREMENTS

## Server Specs (Minimal)
- **CPU**: 2 vCPU
- **RAM**: 4GB
- **Storage**: 50GB SSD
- **OS**: Ubuntu 22.04
- **Cost**: ~$20-40/month

## Recommended VPS Providers
- DigitalOcean Droplet: $24/mo (2vCPU, 4GB)
- Vultr Cloud: $24/mo
- Linode Shared: $24/mo
- Hetzner Cloud: €8/mo (~$9)

---

# CONFIGURATION

## Environment Variables (.env)

```env
# MongoDB
MONGO_URL=mongodb://localhost:27017
DB_NAME=secureguard_central

# Authentication
EMERGENT_API_KEY=your_key_here
API_KEY=3ca173b8c6d5b24d4317b226435ed37dd80791156f380bb4523d3b29114cf903

# Alerts (optional)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Billing (optional)
STRIPE_SECRET_KEY=sk_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Security
JWT_SECRET=your-random-secret-key
JWT_SECRET=9807c42391e28bc77702f3bf9b0262d9e9cf0cedd55bc83b85083f6dc8bf39846acecdc2102a131345c289535da44d9de3e98eea1e4d56090dd2e03adbc942e3
API_KEY_SALT=your-random-salt
API_KEY_SALT=80e20a23e11d9c76f0ab2306f1b42499b9ec0ea20589f5d4a488e5f239b95d11

# CORS (add your domain)
CORS_ORIGINS=https://yourdomain.com,http://localhost:3000
```

---

# API ENDPOINTS

## For Admin Dashboard
- `GET /api/admin/dashboard/stats` - Platform statistics
- `GET /api/admin/clients` - List all clients
- `POST /api/admin/clients` - Create client
- `GET /api/admin/edge-devices` - List edge devices
- `POST /api/admin/edge-devices/provision` - Generate credentials

## For Edge Devices (called by edge devices)
- `POST /api/edge/register` - Register new edge device
- `POST /api/edge/heartbeat` - Health check
- `POST /api/edge/incidents` - Upload incident
- `POST /api/edge/sync` - Sync watchlist, settings
- `GET /api/edge/config/{client_id}` - Get client config

## For Client Dashboard
- `GET /api/dashboard/stats` - Client's stats
- `GET /api/incidents` - Client's incidents
- `GET /api/cameras` - Client's cameras (from edge)

---

# PRODUCTION SETUP

## 1. Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 2. SSL with Let's Encrypt
```bash
sudo certbot --nginx -d api.yourdomain.com
```

## 3. PM2 Process Manager
```bash
pm2 start "uvicorn server:app --host 0.0.0.0 --port 8001" --name central-server
pm2 save
pm2 startup
```

---

# SCALING

| Clients | Server Spec | Cost |
|---------|-------------|------|
| 1-10 | 2 vCPU, 4GB | $24/mo |
| 10-50 | 4 vCPU, 8GB | $48/mo |
| 50-200 | 8 vCPU, 16GB | $96/mo |
| 200+ | Load balanced cluster | $200+/mo |
