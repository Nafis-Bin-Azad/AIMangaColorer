#!/bin/bash

# Startup script for Manga Colorizer Electron App
# This script checks dependencies and starts the app

set -e

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [ ! -z "$PYTHON_PID" ]; then
        kill $PYTHON_PID 2>/dev/null || true
        echo "   Python API stopped"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🎨 Manga Colorizer - Starting Application"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Kill any existing instances
echo "🔪 Checking for existing instances..."

# First, kill ALL Electron processes (most reliable method)
killall -9 Electron 2>/dev/null || true

# Kill processes on ports 8000 and 5173-5174
for port in 8000 5173 5174; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "   Stopping process on port $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    fi
done

# Kill Python backend processes
pkill -f "backend/api/main.py" 2>/dev/null || true
pkill -f "uvicorn.*backend.api.main" 2>/dev/null || true

# Kill npm/node processes running in electron-app directory
if pgrep -f "npm.*electron-app" >/dev/null 2>&1; then
    echo "   Stopping npm processes..."
    pkill -9 -f "npm.*electron-app" 2>/dev/null || true
fi

# Kill concurrently processes
pkill -9 -f "concurrently.*dev:react.*dev:electron" 2>/dev/null || true

# Wait for processes to fully terminate
sleep 2

echo "✅ Cleanup complete"
echo ""

# Check Python virtual environment
echo "📦 Checking Python environment..."
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check Python dependencies
echo "📦 Checking Python dependencies..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing Python dependencies...${NC}"
    pip install -r backend/requirements.txt
fi

# Check Node.js dependencies
echo "📦 Checking Node.js dependencies..."
cd electron-app
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  Installing Node.js dependencies...${NC}"
    npm install
fi

# Build TypeScript
echo "🔨 Building TypeScript..."
npm run build

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ All dependencies checked${NC}"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🚀 Starting application..."
echo ""

# Start Python backend in background
echo "🐍 Starting Python backend..."
cd "$DIR"
source venv/bin/activate
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 > /tmp/manga_api.log 2>&1 &
PYTHON_PID=$!
echo "   Python API started (PID: $PYTHON_PID)"

# Wait for API to be ready
echo "   Waiting for API to be ready..."
sleep 3

# Check if Python API is actually running
if ! ps -p $PYTHON_PID > /dev/null; then
    echo -e "${RED}❌ Python API failed to start${NC}"
    echo "   Check /tmp/manga_api.log for errors"
    exit 1
fi

echo -e "${GREEN}   ✅ Python API ready${NC}"
echo ""

# Start the Electron app
cd electron-app
npm run dev
