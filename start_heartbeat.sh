#!/bin/bash

# HeartBeat Engine - Full Stack Startup Script
# Starts backend (FastAPI) and frontend (Next.js) together

echo "=========================================="
echo "HEARTBEAT ENGINE - STARTUP"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo -e "${RED}Error: Must run from HeartBeat root directory${NC}"
    exit 1
fi

# Check Google Cloud authentication
echo -e "${YELLOW}[1/5]${NC} Checking Google Cloud authentication..."
if gcloud auth application-default print-access-token > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Google Cloud authenticated${NC}"
else
    echo -e "${RED}✗ Google Cloud not authenticated${NC}"
    echo "Run: gcloud auth application-default login"
    exit 1
fi

# Set environment variables
echo -e "${YELLOW}[2/5]${NC} Setting environment variables..."
export USE_QWEN3_ORCHESTRATOR=true
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
echo -e "${GREEN}✓ Environment configured (Qwen3 enabled)${NC}"

# Start backend
echo -e "${YELLOW}[3/5]${NC} Starting FastAPI backend..."
cd backend
source ../venv/bin/activate

# Ensure port 8000 is free (avoid ghost uvicorn keeping old code)
if lsof -i :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo -e "${YELLOW}Port 8000 in use. Stopping existing backend...${NC}"
  EXISTING_PIDS=$(lsof -i :8000 -sTCP:LISTEN -t)
  kill $EXISTING_PIDS >/dev/null 2>&1 || true
  sleep 1
  # Force kill if still alive
  for PID in $EXISTING_PIDS; do
    if ps -p $PID >/dev/null 2>&1; then
      kill -9 $PID >/dev/null 2>&1 || true
    fi
  done
  echo -e "${GREEN}✓ Freed port 8000${NC}"
fi

# Load .env file if it exists
if [ -f ../.env ]; then
    echo "  Loading environment variables from .env..."
    set -a
    source ../.env
    set +a
fi

# Start backend in background
python3 main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend starting (PID: $BACKEND_PID)${NC}"
cd ..

# Wait for backend to be ready (no timeout - first run downloads embedding model ~2GB)
echo -e "${YELLOW}[4/5]${NC} Waiting for backend to be ready..."
echo "  NOTE: First run will download Pinecone embedding model (~2GB, 2-5 min)"
echo "  Subsequent startups will be fast (model cached)"
echo ""

WAIT_COUNT=0
while true; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend ready at http://localhost:8000${NC}"
        break
    fi
    
    # Show progress every 10 seconds
    if [ $((WAIT_COUNT % 10)) -eq 0 ]; then
        echo "  Still waiting... (${WAIT_COUNT}s elapsed)"
    fi
    
    WAIT_COUNT=$((WAIT_COUNT + 1))
    sleep 1
done

# Start frontend
echo -e "${YELLOW}[5/5]${NC} Starting Next.js frontend..."
cd frontend

# Ensure port 3000 is free for Next.js
if lsof -i :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo -e "${YELLOW}Port 3000 in use. Stopping existing Next.js...${NC}"
  EXISTING_NEXT=$(lsof -i :3000 -sTCP:LISTEN -t)
  kill $EXISTING_NEXT >/dev/null 2>&1 || true
  sleep 1
  for PID in $EXISTING_NEXT; do
    if ps -p $PID >/dev/null 2>&1; then
      kill -9 $PID >/dev/null 2>&1 || true
    fi
  done
  echo -e "${GREEN}✓ Freed port 3000${NC}"
fi

# Start frontend in background
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend starting (PID: $FRONTEND_PID)${NC}"
cd ..

# Wait for frontend to be ready
echo ""
echo "Waiting for frontend to compile..."
sleep 5

echo ""
echo "=========================================="
echo -e "${GREEN}HEARTBEAT ENGINE - RUNNING${NC}"
echo "=========================================="
echo ""
echo "Frontend:  http://localhost:3000"
echo "Backend:   http://localhost:8000"
echo "Health:    http://localhost:8000/api/v1/health"
echo ""
echo "Process IDs:"
echo "  Backend:  $BACKEND_PID"
echo "  Frontend: $FRONTEND_PID"
echo ""
echo "Logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "To stop:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "=========================================="
echo ""

# Save PIDs for easy stopping
echo "$BACKEND_PID $FRONTEND_PID" > .heartbeat_pids

echo "Press Ctrl+C to view logs, or run 'bash stop_heartbeat.sh' to stop"
echo ""

# Follow backend logs
tail -f backend.log
