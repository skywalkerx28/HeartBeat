#!/bin/bash

# HeartBeat Engine - Daily Active Roster Sync Cron Setup
# Sets up automated daily roster updates at 6 AM ET (after overnight roster moves)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
PYTHON_PATH="${PROJECT_ROOT}/venv/bin/python"
SYNC_SCRIPT="${PROJECT_ROOT}/scripts/daily_active_roster_sync.py"

echo "HeartBeat Engine - Daily Roster Sync Automation Setup"
echo "================================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Python: $PYTHON_PATH"
echo "Sync script: $SYNC_SCRIPT"
echo ""

# Verify files exist
if [ ! -f "$PYTHON_PATH" ]; then
    echo "ERROR: Python not found at $PYTHON_PATH"
    echo "Please ensure virtual environment is set up"
    exit 1
fi

if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "ERROR: Sync script not found at $SYNC_SCRIPT"
    exit 1
fi

# Create cron job entry
# Runs at 6:00 AM ET daily (after overnight roster moves)
CRON_ENTRY="0 6 * * * cd $PROJECT_ROOT && $PYTHON_PATH $SYNC_SCRIPT >> $PROJECT_ROOT/roster_sync.log 2>&1"

echo "Cron entry to be added:"
echo "$CRON_ENTRY"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SYNC_SCRIPT"; then
    echo "Roster sync cron job already exists"
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting..."
        exit 0
    fi
    
    # Remove existing entry
    crontab -l 2>/dev/null | grep -v "$SYNC_SCRIPT" | crontab -
    echo "Removed existing cron job"
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo ""
echo "SUCCESS: Daily active roster sync cron job installed"
echo "The daily active roster sync will run at 6:00 AM ET"
echo ""
echo "To view cron jobs: crontab -l"
echo "To remove: crontab -e (then delete the line)"
echo "To test manually: $PYTHON_PATH $SYNC_SCRIPT"
echo ""
echo "Logs will be written to: $PROJECT_ROOT/roster_sync.log"
echo ""

