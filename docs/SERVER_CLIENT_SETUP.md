# SecureGuard Deployment & Setup Guide
## Complete Server and Client Configuration Notes

---

# PART 1: WHERE TO DEPLOY

## Deployment Options Comparison

| Option | Cost | Difficulty | Best For | RTSP Cameras |
|--------|------|------------|----------|--------------|
| **Local PC/Server** | Free | Easy | Testing, Single store | ✅ Direct access |
| **On-Premise Server** | $500-2000 | Medium | Production, Multi-store | ✅ Direct access |
| **Cloud VPS** | $20-100/mo | Medium | Remote access needed | ⚠️ Needs port forwarding |
| **Docker on NAS** | Free | Easy | Already have NAS | ✅ Same network |

---

## Option 1: Local PC/Workstation (Recommended for Testing)

### Requirements:
- **OS**: Windows 10/11, Ubuntu 20.04+, or macOS
- **CPU**: Intel i5/AMD Ryzen 5 or better (for ML)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB free space
- **Network**: Same LAN as cameras

### Pros:
- Free, no monthly cost
- Direct camera access
- Easy to set up and test

### Cons:
- Must keep PC running 24/7
- No remote access without VPN

---

## Option 2: Dedicated On-Premise Server (Recommended for Production)

### Hardware Options:

**Budget ($300-500):**
- Intel NUC or Mini PC
- Intel i5, 16GB RAM, 256GB SSD
- Example: Beelink SER5, ASUS PN51

**Mid-Range ($500-1000):**
- Small form factor workstation
- Intel i7/AMD Ryzen 7, 32GB RAM, 512GB SSD
- Example: HP ProDesk, Dell OptiPlex

**High-End ($1000-2000):**
- Tower server or rack-mounted
- With GPU (NVIDIA RTX 3060+) for faster ML
- Example: Dell PowerEdge, HP ProLiant

### Pros:
- 24/7 operation designed
- Direct camera access
- Full control over hardware

### Cons:
- Upfront hardware cost
- Requires physical space

---

## Option 3: Cloud VPS (For Remote Access)

### Providers:

| Provider | Recommended Plan | Monthly Cost | Notes |
|----------|-----------------|--------------|-------|
| **DigitalOcean** | CPU-Optimized 4vCPU | $42/mo | Good for ML workloads |
| **Vultr** | High Frequency 4vCPU | $48/mo | Fast NVMe storage |
| **Linode** | Dedicated 4GB | $36/mo | Reliable, good support |
| **AWS EC2** | c5.xlarge | ~$120/mo | Enterprise, scalable |
| **Hetzner** | CPX31 | €15/mo (~$16) | Best value in EU |

### Pros:
- No hardware to maintain
- Remote access built-in
- Scalable resources

### Cons:
- Monthly cost
- Cameras need port forwarding/VPN
- Network latency for video

---

## Option 4: Docker on NAS (If you have Synology/QNAP)

### Compatible NAS:
- Synology DS920+, DS1520+, DS1621+
- QNAP TS-453D, TS-653D

### Pros:
- Use existing hardware
- Low power consumption
- Same network as cameras

### Cons:
- Limited CPU for ML
- May be slow for real-time detection

---

# PART 2: SERVER SETUP

## Step-by-Step Installation

### A. Prepare the Server

#### For Ubuntu/Debian Linux:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nodejs \
    npm \
    ffmpeg \
    git \
    curl \
    nginx \
    certbot

# Install yarn globally
sudo npm install -g yarn

# Verify installations
python3 --version    # Should be 3.11+
node --version       # Should be 18+
ffmpeg -version      # Should show version
```

#### For Windows:
1. Download and install:
   - Python 3.11: https://www.python.org/downloads/
   - Node.js 18: https://nodejs.org/
   - Git: https://git-scm.com/
   - ffmpeg: https://ffmpeg.org/download.html

2. Add to PATH:
   - Python: `C:\Python311\` and `C:\Python311\Scripts\`
   - ffmpeg: `C:\ffmpeg\bin\`

#### For macOS:
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install packages
brew install python@3.11 node ffmpeg git nginx
brew install --cask mongodb-compass  # Optional GUI
```

---

### B. Install MongoDB

#### Ubuntu/Debian:
```bash
# Import MongoDB GPG key
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# Add repository
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
   sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Install MongoDB
sudo apt update
sudo apt install -y mongodb-org

# Start and enable MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Verify MongoDB is running
sudo systemctl status mongod
mongosh --eval "db.version()"
```

#### Windows:
1. Download MongoDB Community Server: https://www.mongodb.com/try/download/community
2. Run installer, select "Complete" installation
3. Check "Install MongoDB as a Service"
4. MongoDB starts automatically

#### macOS:
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

---

### C. Download SecureGuard Code

#### Option 1: From GitHub (after pushing from Emergent)
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/secureguard.git
cd secureguard
```

#### Option 2: Copy from Emergent Download
```bash
# After downloading ZIP from Emergent
unzip secureguard.zip -d ~/
cd ~/secureguard
```

---

### D. Backend Setup

```bash
cd ~/secureguard/backend

# Create Python virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\activate   # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install Emergent integrations (for GPT-5.2)
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Verify installation
python -c "import fastapi; print('FastAPI OK')"
python -c "import cv2; print('OpenCV OK')"
python -c "from ultralytics import YOLO; print('YOLO OK')"
```

---

### E. Configure Backend Environment

```bash
# Create/edit .env file
nano ~/secureguard/backend/.env
```

**Add these settings:**
```env
# MongoDB Connection
MONGO_URL=mongodb://localhost:27017
DB_NAME=secureguard

# Emergent API Key (REQUIRED for GPT-5.2 Vision)
# Get from: Emergent Platform → Profile → Universal Key
EMERGENT_LLM_KEY=sk-emergent-your-key-here

# CORS Settings (add your frontend URL)
CORS_ORIGINS=http://localhost:3000,http://YOUR_SERVER_IP:3000

# Optional: Twilio WhatsApp Alerts
# TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TWILIO_AUTH_TOKEN=your_auth_token
# TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

---

### F. Frontend Setup

```bash
cd ~/secureguard/frontend

# Install dependencies
yarn install
# OR
npm install

# Create environment file
nano .env
```

**Add:**
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

**For network access, use server IP:**
```env
REACT_APP_BACKEND_URL=http://192.168.1.100:8001
```

---

### G. Test Run (Development Mode)

**Terminal 1 - Backend:**
```bash
cd ~/secureguard/backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 - Frontend:**
```bash
cd ~/secureguard/frontend
yarn start
# OR
npm start
```

**Verify:**
- Backend API: http://localhost:8001/docs
- Frontend: http://localhost:3000

---

# PART 3: PRODUCTION SETUP

## A. Using PM2 (Process Manager)

```bash
# Install PM2
sudo npm install -g pm2

# Create PM2 ecosystem file
cat > ~/secureguard/ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'secureguard-backend',
      cwd: './backend',
      script: './venv/bin/python',
      args: '-m uvicorn server:app --host 0.0.0.0 --port 8001',
      env: {
        NODE_ENV: 'production'
      },
      max_memory_restart: '2G',
      autorestart: true
    },
    {
      name: 'secureguard-frontend',
      cwd: './frontend',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      },
      autorestart: true
    }
  ]
}
EOF

# Start all services
cd ~/secureguard
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Setup auto-start on boot
pm2 startup
# Run the command it outputs (starts with sudo)

# Check status
pm2 status
pm2 logs
```

---

## B. Using systemd (Linux Service)

**Create backend service:**
```bash
sudo nano /etc/systemd/system/secureguard-backend.service
```

```ini
[Unit]
Description=SecureGuard Backend API
After=network.target mongodb.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/secureguard/backend
Environment=PATH=/home/YOUR_USERNAME/secureguard/backend/venv/bin
ExecStart=/home/YOUR_USERNAME/secureguard/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Create frontend service:**
```bash
sudo nano /etc/systemd/system/secureguard-frontend.service
```

```ini
[Unit]
Description=SecureGuard Frontend
After=network.target secureguard-backend.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/secureguard/frontend
ExecStart=/usr/bin/npm start
Environment=PORT=3000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable secureguard-backend secureguard-frontend
sudo systemctl start secureguard-backend secureguard-frontend

# Check status
sudo systemctl status secureguard-backend
sudo systemctl status secureguard-frontend
```

---

## C. Nginx Reverse Proxy (Production)

```bash
sudo nano /etc/nginx/sites-available/secureguard
```

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        client_max_body_size 500M;  # For video uploads
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/secureguard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## D. SSL Certificate (HTTPS)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is set up automatically
# Test renewal
sudo certbot renew --dry-run
```

---

# PART 4: CLIENT SETUP

## A. Adding Your First Admin User

1. Open browser: `http://YOUR_SERVER_IP:3000`
2. Click "Continue with Google"
3. Sign in with your Google account
4. **First user automatically becomes Super Admin!**

---

## B. Adding Clients (Stores)

1. Go to **Admin → Clients**
2. Click **"Add Client"**
3. Fill in:
   - Company Name: `ABC Liquor Store`
   - URL Slug: `abc-liquor`
   - Contact Name: `John Smith`
   - Contact Email: `john@example.com`
   - Plan: `Professional` (for GPT analysis)
4. Click **Create Client**

---

## C. Adding RTSP Cameras

1. Go to **Admin → Cameras**
2. Click **"Add Camera"**
3. Fill in:
   - Client: Select your client
   - Camera Name: `Front Entrance`
   - Location: `Main entrance, Store #1`
   - RTSP URL: Your camera URL (see below)
   - Sensitivity: `Medium`
4. Click **Create Camera**

### Your RTSP URLs:
```
Channel 1: rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=1&subtype=1
Channel 2: rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=2&subtype=1
```

---

## D. Adding Users to Client

1. Go to **Admin → Users**
2. Find the user (they must sign in first)
3. Click **⋮** menu → **Assign to Client**
4. Select:
   - Client: `ABC Liquor Store`
   - Role: `Client Owner` / `Client Staff` / `Client Viewer`
5. Click **Assign**

---

## E. Configuring WhatsApp Alerts

1. Go to **Admin → Alerts**
2. Select your client
3. Enable **"Enable Alerts"**
4. Configure:
   - Alert on Critical: ✅
   - Alert on Warning: Optional
   - Cooldown: 5 minutes
5. Add WhatsApp numbers (with country code): `+1234567890`
6. Click **Save Settings**

**Note:** Requires Twilio credentials in backend `.env`

---

## F. Configuring AI Detection

1. Go to **Admin → AI Control**
2. Select your client
3. Enable/disable models:
   - ✅ YOLO v8 (person detection)
   - ✅ Pose Estimation (body posture)
   - ✅ DeepFace (face recognition)
   - ✅ GPT-5.2 Vision (behavior analysis)
4. Set Detection Sensitivity: `Medium`
5. Set Threat Threshold: `60%`
6. Click **Save Settings**

---

# PART 5: NETWORK CONFIGURATION

## A. Firewall Rules

```bash
# Allow required ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 3000/tcp    # Frontend (dev)
sudo ufw allow 8001/tcp    # Backend API
sudo ufw allow 27017/tcp   # MongoDB (only if remote access needed)

# Enable firewall
sudo ufw enable
sudo ufw status
```

---

## B. Camera Network Requirements

### Same Network (Recommended):
- Server and cameras on same subnet (e.g., 192.168.200.x)
- No additional configuration needed
- Lowest latency

### Different Subnet:
- Ensure routing between subnets
- Check firewall allows RTSP (port 554)
- May need static routes

### Remote Cameras (VPN):
```bash
# Option 1: WireGuard VPN
sudo apt install wireguard

# Option 2: Tailscale (easier)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

---

# PART 6: MAINTENANCE

## A. Backup MongoDB

```bash
# Create backup
mongodump --db secureguard --out ~/backups/$(date +%Y%m%d)

# Restore backup
mongorestore --db secureguard ~/backups/20240126/secureguard
```

## B. Update Application

```bash
cd ~/secureguard
git pull origin main

# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
yarn install

# Restart services
pm2 restart all
# OR
sudo systemctl restart secureguard-backend secureguard-frontend
```

## C. View Logs

```bash
# PM2 logs
pm2 logs secureguard-backend
pm2 logs secureguard-frontend

# systemd logs
sudo journalctl -u secureguard-backend -f
sudo journalctl -u secureguard-frontend -f

# MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

---

# PART 7: TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| Camera not connecting | Check IP, port 554, firewall |
| MongoDB won't start | Check `/var/log/mongodb/mongod.log` |
| Backend crashes | Check `pm2 logs` or `journalctl` |
| Frontend blank page | Check browser console (F12) |
| ML models slow | Need more RAM/CPU, consider GPU |
| Video upload fails | Increase `client_max_body_size` in nginx |

---

# QUICK REFERENCE

## URLs
- Frontend: `http://YOUR_IP:3000`
- Backend API: `http://YOUR_IP:8001`
- API Docs: `http://YOUR_IP:8001/docs`
- MongoDB: `mongodb://localhost:27017`

## Commands
```bash
# Start all
pm2 start ecosystem.config.js

# Stop all
pm2 stop all

# Restart all
pm2 restart all

# View status
pm2 status

# View logs
pm2 logs
```

## File Locations
```
~/secureguard/
├── backend/
│   ├── .env              # Backend config
│   ├── server.py         # Main API
│   └── video_storage/    # Uploaded videos
├── frontend/
│   ├── .env              # Frontend config
│   └── src/              # React source
└── ecosystem.config.js   # PM2 config
```

---

**Need Help?** Check `/app/docs/DEVELOPER_GUIDE.md` for detailed documentation.
