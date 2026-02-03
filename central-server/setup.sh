#!/bin/bash
# SecureGuard Central Server Setup Script
# Builds the React frontend and prepares the central server for deployment

set -e

echo "============================================"
echo "SecureGuard Central Server Setup"
echo "============================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")/frontend"
CENTRAL_SERVER_DIR="$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Installing Python dependencies...${NC}"
cd "$CENTRAL_SERVER_DIR"
pip install -r requirements.txt

echo -e "${YELLOW}Step 2: Building React frontend...${NC}"
cd "$FRONTEND_DIR"

# Check if yarn is available
if command -v yarn &> /dev/null; then
    yarn install
    yarn build
else
    npm install
    npm run build
fi

echo -e "${YELLOW}Step 3: Copying frontend build to central-server...${NC}"
mkdir -p "$CENTRAL_SERVER_DIR/frontend"
cp -r "$FRONTEND_DIR/build" "$CENTRAL_SERVER_DIR/frontend/"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "To start the server:"
echo "  cd $CENTRAL_SERVER_DIR"
echo "  python server.py"
echo ""
echo "Or with uvicorn:"
echo "  uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
echo ""
echo "Default URL: http://localhost:8001"
echo ""
echo "Environment Variables to configure:"
echo "  MONGO_URL        - MongoDB connection string"
echo "  DB_NAME          - Database name (default: secureguard_central)"
echo "  CORS_ORIGINS     - Allowed origins (comma-separated)"
echo "  CENTRAL_SERVER_URL - Public URL of this server"
