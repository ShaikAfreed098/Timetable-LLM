#!/bin/bash

# ============================================================================
# Timetable LLM - Quick Start Script for Linux/macOS
# This script starts both backend and frontend servers
# ============================================================================

set -e

echo ""
echo "============================================================================"
echo "Timetable LLM - Application Startup"
echo "============================================================================"
echo ""

# Check if we're in the right directory
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Please run this script from the project root."
    echo ""
    exit 1
fi

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Install Python 3.11+ from https://www.python.org"
    exit 1
fi
python3 --version

# Check Node
echo ""
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Install from https://nodejs.org"
    exit 1
fi
node --version

echo ""
echo "============================================================================"
echo "Starting services..."
echo "============================================================================"
echo ""

# Function to start backend
start_backend() {
    cd "$(dirname "$0")/backend"
    
    # Create venv if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate venv
    source .venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt -q
    
    # Run migrations
    echo "Running migrations..."
    alembic upgrade head
    
    echo ""
    echo "============================================================================"
    echo "Backend is running on http://localhost:8000"
    echo "API Documentation: http://localhost:8000/api/docs"
    echo "============================================================================"
    echo ""
    
    # Start backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# Function to start frontend
start_frontend() {
    sleep 3  # Wait for backend to start
    
    cd "$(dirname "$0")/frontend"
    
    echo "Installing dependencies..."
    npm install --silent
    
    echo ""
    echo "============================================================================"
    echo "Frontend is running on http://localhost:3000"
    echo "============================================================================"
    echo ""
    
    # Start frontend
    npm run dev
}

# Start backend in background
start_backend &
BACKEND_PID=$!

# Start frontend in background
start_frontend &
FRONTEND_PID=$!

echo ""
echo "============================================================================"
echo "Services Started!"
echo "============================================================================"
echo ""
echo "Frontend:     http://localhost:3000"
echo "Backend API:  http://localhost:8000"
echo "API Docs:     http://localhost:8000/api/docs"
echo "Health Check: http://localhost:8000/health"
echo ""
echo "IMPORTANT:"
echo "- Both services are running in the background"
echo "- Press Ctrl+C to stop both services"
echo "- Check the output above for any error messages"
echo ""
echo "Next Steps:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Wait for both servers to fully start (~30-60 seconds)"
echo "3. If you see errors, check the output above"
echo ""
echo "============================================================================"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
