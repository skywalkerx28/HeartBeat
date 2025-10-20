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
echo -e "${YELLOW}[1/7]${NC} Checking Google Cloud authentication..."
if gcloud auth application-default print-access-token > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Google Cloud authenticated${NC}"
else
    echo -e "${RED}✗ Google Cloud not authenticated${NC}"
    echo "Run: gcloud auth application-default login"
    exit 1
fi

# Check Redis installation
echo -e "${YELLOW}[2/7]${NC} Checking Redis..."
if ! command -v redis-server &> /dev/null; then
    echo -e "${RED}✗ Redis not installed${NC}"
    echo "Install: brew install redis (macOS) or apt-get install redis (Linux)"
    exit 1
fi

# Start Redis if not running
if ! pgrep -x redis-server > /dev/null; then
    echo "  Starting Redis server..."
    redis-server --daemonize yes --loglevel warning
    sleep 1
    echo -e "${GREEN}✓ Redis started${NC}"
else
    echo -e "${GREEN}✓ Redis already running${NC}"
fi

# Set environment variables
echo -e "${YELLOW}[3/7]${NC} Setting environment variables..."
# Default to OpenRouter unless explicitly overridden
export USE_OPENROUTER=${USE_OPENROUTER:-true}
export USE_QWEN3_ORCHESTRATOR=${USE_QWEN3_ORCHESTRATOR:-false}
export USE_BIGQUERY_ANALYTICS=${USE_BIGQUERY_ANALYTICS:-true}
export GCP_PROJECT=${GCP_PROJECT:-heartbeat-474020}
export BQ_DATASET_CORE=${BQ_DATASET_CORE:-core}
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
# Media routes: open access for development unless overridden
export CLIPS_OPEN_ACCESS=${CLIPS_OPEN_ACCESS:-1}

# GCP Phase 1 configuration
export GCS_LAKE_BUCKET=${GCS_LAKE_BUCKET:-heartbeat-474020-lake}
export VECTOR_BACKEND=${VECTOR_BACKEND:-vertex}

if [ "$USE_QWEN3_ORCHESTRATOR" = "true" ]; then
  echo -e "${GREEN}✓ Environment configured (Qwen3 enabled)${NC}"
else
  echo -e "${GREEN}✓ Environment configured (OpenRouter enabled)${NC}"
fi
echo "  GCP: BigQuery=$USE_BIGQUERY_ANALYTICS, Project=$GCP_PROJECT, Core=$BQ_DATASET_CORE"
echo "  GCP: BigQuery=$USE_BIGQUERY_ANALYTICS, Bucket=$GCS_LAKE_BUCKET, Vector=$VECTOR_BACKEND"

# Start backend
echo -e "${YELLOW}[4/7]${NC} Starting FastAPI backend..."
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
echo -e "${YELLOW}[5/7]${NC} Waiting for backend to be ready..."
echo "  NOTE: Vector backend set to '${VECTOR_BACKEND}'. Ensure Vertex env vars are set."
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

# Start Celery worker
echo -e "${YELLOW}[6/7]${NC} Starting HeartBeat.bot Celery worker..."
cd backend
celery -A bot.celery_app worker --loglevel=info --logfile=../celery_worker.log --detach
CELERY_WORKER_PID=$!
echo -e "${GREEN}✓ Celery worker started${NC}"

# Start Celery beat scheduler
echo "Starting Celery beat scheduler..."
celery -A bot.celery_app beat --loglevel=info --logfile=../celery_beat.log --detach
CELERY_BEAT_PID=$!
echo -e "${GREEN}✓ Celery beat started${NC}"
cd ..

# Start frontend
echo -e "${YELLOW}[7/7]${NC} Starting Next.js frontend..."
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
echo "News API:  http://localhost:8000/api/v1/news/daily-article"
echo ""
echo "Process IDs:"
echo "  Backend:  $BACKEND_PID"
echo "  Frontend: $FRONTEND_PID"
echo "  Redis:    $(pgrep -x redis-server)"
echo "  Celery:   $(pgrep -f 'celery.*worker')"
echo ""
echo "Logs:"
echo "  Backend:       tail -f backend.log"
echo "  Frontend:      tail -f frontend.log"
echo "  Celery Worker: tail -f celery_worker.log"
echo "  Celery Beat:   tail -f celery_beat.log"
echo ""
echo "To stop:"
echo "  bash stop_heartbeat.sh"
echo ""
echo "=========================================="
echo ""

# Save PIDs for easy stopping
echo "$BACKEND_PID $FRONTEND_PID" > .heartbeat_pids

echo "Press Ctrl+C to view logs, or run 'bash stop_heartbeat.sh' to stop"
echo ""

# Follow backend logs
tail -f backend.log
