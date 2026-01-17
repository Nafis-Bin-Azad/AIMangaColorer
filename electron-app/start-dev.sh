#!/bin/bash

# Quick start script for Electron development

echo "🚀 Starting Manga Colorizer Electron App..."
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from electron-app directory"
    echo "Usage: cd electron-app && ./start-dev.sh"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node dependencies..."
    npm install
    echo ""
fi

# Check if Python venv exists
if [ ! -d "../venv" ]; then
    echo "⚠️  Warning: Python venv not found at ../venv"
    echo "Please create it first:"
    echo "  cd .."
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if FastAPI is installed
if ! ../venv/bin/python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Warning: FastAPI not installed"
    echo "Installing FastAPI..."
    ../venv/bin/pip install fastapi uvicorn[standard] python-multipart
    echo ""
fi

echo "✅ All checks passed!"
echo ""
echo "Starting development servers..."
echo "  - Python API: http://localhost:8000"
echo "  - React Dev: http://localhost:5173"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the app
npm run dev
