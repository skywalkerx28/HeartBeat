#!/bin/bash

# HeartBeat Engine - Shutdown Script

echo "=========================================="
echo "HEARTBEAT ENGINE - SHUTDOWN"
echo "=========================================="
echo ""

# Check for PID file
if [ ! -f ".heartbeat_pids" ]; then
    echo "No running processes found (no .heartbeat_pids file)"
    echo "Checking for processes manually..."
    
    # Find and kill backend
    BACKEND_PID=$(ps aux | grep "python main.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo "✓ Backend stopped"
    fi
    
    # Find and kill frontend
    FRONTEND_PID=$(ps aux | grep "npm run dev" | grep -v grep | awk '{print $2}')
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo "✓ Frontend stopped"
    fi
    
    exit 0
fi

# Read PIDs from file
read BACKEND_PID FRONTEND_PID < .heartbeat_pids

echo "Stopping processes..."
echo ""

# Stop backend
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "Stopping backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID
    sleep 1
    
    # Force kill if still running
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "Force stopping backend..."
        kill -9 $BACKEND_PID
    fi
    
    echo "✓ Backend stopped"
else
    echo "Backend already stopped"
fi

# Stop frontend
if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo "Stopping frontend (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID
    sleep 1
    
    # Force kill if still running
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "Force stopping frontend..."
        kill -9 $FRONTEND_PID
    fi
    
    echo "✓ Frontend stopped"
else
    echo "Frontend already stopped"
fi

# Also kill any remaining Next.js processes
echo ""
echo "Cleaning up remaining processes..."
pkill -f "next dev" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null

# Optionally stop Redis (commented out by default to allow manual control)
# Uncomment if you want to stop Redis on shutdown:
# echo "Stopping Redis..."
# redis-cli shutdown 2>/dev/null
# echo "✓ Redis stopped"

# Clean up PID file
rm -f .heartbeat_pids

echo ""
echo "=========================================="
echo "HEARTBEAT ENGINE - STOPPED"
echo "=========================================="
echo ""

