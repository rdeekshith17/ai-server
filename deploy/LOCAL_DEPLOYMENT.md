# SecureGuard Local Deployment Guide

## Quick Start (5 minutes)

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB 6+
- ffmpeg
- Git

### Step 1: Download Code

**Option A: From Emergent Platform**
1. Click "Save to GitHub" in Emergent chat
2. Clone your repository:
```bash
git clone https://github.com/YOUR_USERNAME/secureguard.git
cd secureguard
```

**Option B: Download ZIP**
1. In Emergent, click the download icon
2. Extract the ZIP file
3. Navigate to the folder

### Step 2: Install Dependencies

**Ubuntu/Debian:**
```bash
# System packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm ffmpeg

# MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

**macOS:**
```bash
brew install python@3.11 node ffmpeg mongodb-community
brew services start mongodb-community
```

**Windows:**
1. Install Python 3.11 from python.org
2. Install Node.js 18 from nodejs.org
3. Install MongoDB from mongodb.com
4. Install ffmpeg from ffmpeg.org
5. Add all to PATH

### Step 3: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install Emergent integrations
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

### Step 4: Configure Backend

Edit `backend/.env`:
```env
# Required
MONGO_URL=mongodb://localhost:27017
DB_NAME=secureguard
EMERGENT_API_KEY=your_key_from_emergent_platform

# Optional - WhatsApp Alerts
TWILIO_ACCOUNT_SID=ACxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# CORS - Add your frontend URL
CORS_ORIGINS=http://localhost:3000
```

**Get EMERGENT_API_KEY:**
1. Go to Emergent Platform
2. Click Profile → Universal Key
3. Copy the key

### Step 5: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
# OR
yarn install

# Create .env
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
```

### Step 6: Start the Platform

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

### Step 7: Access the Platform

1. Open http://localhost:3000
2. Sign in with Google
3. First user becomes Super Admin!

---

## Configure Your RTSP Cameras

### Add Cameras via Admin Dashboard

1. Go to Admin → Cameras
2. Click "Add Camera"
3. Enter your RTSP URLs:

**Channel 1:**
```
rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=1&subtype=1
```

**Channel 2:**
```
rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=2&subtype=1
```

### Test Camera Connection

Click "Test RTSP" on any camera to verify connectivity.

---

## Production Deployment

### Using PM2 (Recommended)

```bash
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'secureguard-backend',
      cwd: './backend',
      script: 'venv/bin/uvicorn',
      args: 'server:app --host 0.0.0.0 --port 8001',
      env: {
        NODE_ENV: 'production'
      }
    }
  ]
}
EOF

pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Using systemd (Linux)

```bash
sudo cat > /etc/systemd/system/secureguard.service << 'EOF'
[Unit]
Description=SecureGuard Backend
After=network.target mongodb.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/secureguard/backend
Environment=PATH=/home/your_user/secureguard/backend/venv/bin
ExecStart=/home/your_user/secureguard/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable secureguard
sudo systemctl start secureguard
```

### Using Docker

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

---

## Network Configuration

### If cameras are on a different subnet:

1. Ensure the server can reach 192.168.200.x network
2. Check firewall allows port 554 (RTSP)
3. Verify routing between subnets

### Firewall Rules (if needed):

```bash
# Allow RTSP
sudo ufw allow 554/tcp

# Allow backend API
sudo ufw allow 8001/tcp

# Allow frontend
sudo ufw allow 3000/tcp
```

---

## Troubleshooting

### MongoDB won't start
```bash
# Check status
sudo systemctl status mongod

# Check logs
sudo tail -f /var/log/mongodb/mongod.log

# Fix permissions
sudo chown -R mongodb:mongodb /var/lib/mongodb
sudo systemctl restart mongod
```

### RTSP connection fails
```bash
# Test with ffmpeg directly
ffmpeg -rtsp_transport tcp -i "rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=1&subtype=1" -frames:v 1 test.jpg

# Check network
ping 192.168.200.189
telnet 192.168.200.189 554
```

### Backend won't start
```bash
# Check if port is in use
lsof -i :8001

# Check Python path
which python3
python3 --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend build fails
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+
```

---

## Security Checklist

- [ ] Change default camera passwords
- [ ] Use HTTPS in production (nginx + Let's Encrypt)
- [ ] Set strong CORS_ORIGINS (not *)
- [ ] Enable MongoDB authentication
- [ ] Use firewall rules
- [ ] Regular backups of MongoDB

---

## Support

- Documentation: `/docs/DEVELOPER_GUIDE.md`
- Architecture: `/docs/MULTI_TENANT_ARCHITECTURE.md`
- PRD: `/memory/PRD.md`
