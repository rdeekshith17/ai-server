#!/bin/bash
# SecureGuard Local Deployment Script
# Run this on your local server (Linux/Mac)

set -e

echo "=========================================="
echo "  SecureGuard Local Deployment"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user.${NC}"
fi

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="redhat"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
fi

echo "Detected OS: $OS"
echo ""

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

MISSING_DEPS=""

check_command python3 || MISSING_DEPS="$MISSING_DEPS python3"
check_command pip3 || MISSING_DEPS="$MISSING_DEPS pip3"
check_command node || MISSING_DEPS="$MISSING_DEPS node"
check_command npm || MISSING_DEPS="$MISSING_DEPS npm"
check_command ffmpeg || MISSING_DEPS="$MISSING_DEPS ffmpeg"
check_command mongod || MISSING_DEPS="$MISSING_DEPS mongodb"

if [ ! -z "$MISSING_DEPS" ]; then
    echo ""
    echo -e "${YELLOW}Missing dependencies:${NC}$MISSING_DEPS"
    echo ""
    
    if [ "$OS" == "linux" ] && [ "$DISTRO" == "debian" ]; then
        echo "Install with:"
        echo "  sudo apt update"
        echo "  sudo apt install -y python3 python3-pip python3-venv nodejs npm ffmpeg"
        echo ""
        echo "For MongoDB:"
        echo "  wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -"
        echo "  echo 'deb http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse' | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list"
        echo "  sudo apt update && sudo apt install -y mongodb-org"
        echo "  sudo systemctl start mongod"
    elif [ "$OS" == "mac" ]; then
        echo "Install with Homebrew:"
        echo "  brew install python@3.11 node ffmpeg mongodb-community"
        echo "  brew services start mongodb-community"
    fi
    
    echo ""
    read -p "Install missing dependencies now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ "$OS" == "linux" ] && [ "$DISTRO" == "debian" ]; then
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv nodejs npm ffmpeg
        elif [ "$OS" == "mac" ]; then
            brew install python@3.11 node ffmpeg
        fi
    else
        echo "Please install dependencies and run again."
        exit 1
    fi
fi

echo ""

# Step 2: Setup directories
echo "Step 2: Setting up directories..."
INSTALL_DIR="${INSTALL_DIR:-$HOME/secureguard}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "  Install directory: $INSTALL_DIR"

# Step 3: Backend setup
echo ""
echo "Step 3: Setting up backend..."

if [ ! -d "backend" ]; then
    mkdir -p backend
fi

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "  Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet fastapi uvicorn motor python-dotenv pydantic opencv-python-headless numpy ultralytics httpx twilio aiofiles python-multipart Pillow

# Install emergentintegrations
pip install --quiet emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

echo -e "  ${GREEN}✓${NC} Backend dependencies installed"

# Create .env file
if [ ! -f ".env" ]; then
    echo "  Creating .env file..."
    cat > .env << 'EOF'
# MongoDB Configuration
MONGO_URL=mongodb://localhost:27017
DB_NAME=secureguard

# Emergent API Key (get from Emergent platform)
EMERGENT_API_KEY=your_emergent_api_key_here

# Optional: Twilio WhatsApp Alerts
# TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TWILIO_AUTH_TOKEN=your_auth_token
# TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# CORS (update for production)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
EOF
    echo -e "  ${YELLOW}⚠${NC} Edit backend/.env with your EMERGENT_API_KEY"
fi

cd ..

# Step 4: Frontend setup
echo ""
echo "Step 4: Setting up frontend..."

if [ ! -d "frontend" ]; then
    mkdir -p frontend
fi

cd frontend

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "  Frontend code not found. You need to copy the frontend code."
    echo "  Download from Emergent platform or clone from GitHub."
else
    echo "  Installing Node dependencies..."
    npm install --silent
    echo -e "  ${GREEN}✓${NC} Frontend dependencies installed"
fi

# Create .env file
if [ ! -f ".env" ]; then
    echo "  Creating .env file..."
    cat > .env << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
EOF
fi

cd ..

# Step 5: Create startup scripts
echo ""
echo "Step 5: Creating startup scripts..."

# Backend start script
cat > start_backend.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/backend"
source venv/bin/activate
echo "Starting SecureGuard Backend on port 8001..."
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
EOF
chmod +x start_backend.sh

# Frontend start script
cat > start_frontend.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/frontend"
echo "Starting SecureGuard Frontend on port 3000..."
npm start
EOF
chmod +x start_frontend.sh

# Combined start script
cat > start_all.sh << 'EOF'
#!/bin/bash
echo "Starting SecureGuard Platform..."
echo ""

# Start MongoDB if not running
if ! pgrep -x "mongod" > /dev/null; then
    echo "Starting MongoDB..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start mongodb-community
    else
        sudo systemctl start mongod
    fi
    sleep 2
fi

# Start backend in background
echo "Starting backend..."
./start_backend.sh &
BACKEND_PID=$!
sleep 5

# Start frontend
echo "Starting frontend..."
./start_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "  SecureGuard is running!"
echo "=========================================="
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8001"
echo "  API Docs: http://localhost:8001/docs"
echo ""
echo "  Press Ctrl+C to stop all services"
echo ""

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
EOF
chmod +x start_all.sh

echo -e "  ${GREEN}✓${NC} Startup scripts created"

# Step 6: Test RTSP cameras
echo ""
echo "Step 6: Testing RTSP camera connectivity..."

test_rtsp() {
    local url=$1
    local name=$2
    echo -n "  Testing $name... "
    if timeout 5 ffprobe -v quiet "$url" 2>/dev/null; then
        echo -e "${GREEN}✓ Connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Not reachable${NC}"
        return 1
    fi
}

# Your cameras
test_rtsp "rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=1&subtype=1" "Camera Channel 1"
test_rtsp "rtsp://admin:admin123456@192.168.200.189:554/cam/realmonitor?channel=2&subtype=1" "Camera Channel 2"

# Summary
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Copy the frontend and backend code to:"
echo "   $INSTALL_DIR/"
echo ""
echo "2. Edit backend/.env and add your EMERGENT_API_KEY"
echo ""
echo "3. Start the platform:"
echo "   cd $INSTALL_DIR"
echo "   ./start_all.sh"
echo ""
echo "4. Open http://localhost:3000 in your browser"
echo ""
echo "5. First user to sign in becomes Super Admin"
echo ""
