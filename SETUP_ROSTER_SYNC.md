# Daily Active Roster Sync - Setup Instructions

## Quick Start

The Daily Active Roster Sync system has been implemented and is ready to use. Follow these steps to get it running.

## Prerequisites

1. **Python Dependencies**

The script requires `httpx` which has been added to `orchestrator/requirements.txt`. Install it:

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat

# If using venv (recommended)
source venv/bin/activate
pip install httpx

# Or install all orchestrator requirements
pip install -r orchestrator/requirements.txt
```

2. **Contracts Data**

Ensure the contracts file exists:
```
/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/market/nhl_contracts_league_wide_2025_2026.parquet
```

If it doesn't exist, you'll need to run the market data sync first.

## Manual Testing

### Test 1: Validate Logic

Run the test script to verify the status assignment logic:

```bash
python3 scripts/tests/test_roster_sync.py
```

Expected output:
```
Testing Roster Status Logic
==================================================
✓ Player D correctly moved to NHL
✓ Player E correctly moved to MINOR
Test Complete!
```

### Test 2: Run Sync (Dry Run)

To see what the sync would do without modifying files, you can add logging:

```bash
# Run the actual sync
python3 scripts/ingest/daily_active_roster_sync.py --season 2025-2026
```

This will:
1. Fetch rosters for all 32 NHL teams
2. Update contract statuses (NHL vs MINOR)
3. Save historical snapshot
4. Update main contracts file
5. Display summary

### Test 3: Get Roster Summary

Check a team's current roster status:

```bash
# View Montreal Canadiens roster
python3 scripts/ingest/daily_active_roster_sync.py --summary MTL

# View New York Islanders roster  
python3 scripts/ingest/daily_active_roster_sync.py --summary NYI
```

## Production Setup

### Step 1: Fix Virtual Environment (if needed)

If your venv is broken (pointing to wrong Python path):

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat

# Remove old venv
rm -rf venv

# Create new venv
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r orchestrator/requirements.txt
```

### Step 2: Set Up Cron Automation

Run the setup script to configure daily execution:

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat
./setup_roster_cron.sh
```

This will:
- Create a cron job that runs at 6 AM ET daily
- Log output to `roster_sync.log`
- Use the correct Python path from venv

### Step 3: Verify Cron Job

Check that the cron job is installed:

```bash
crontab -l
```

You should see:
```
0 6 * * * cd /Users/xavier.bouchard/Desktop/HeartBeat && /Users/xavier.bouchard/Desktop/HeartBeat/venv/bin/python /Users/xavier.bouchard/Desktop/HeartBeat/scripts/ingest/daily_active_roster_sync.py >> /Users/xavier.bouchard/Desktop/HeartBeat/roster_sync.log 2>&1
```

### Step 4: Monitor Logs

Watch the sync process:

```bash
# View logs in real-time
tail -f /Users/xavier.bouchard/Desktop/HeartBeat/roster_sync.log

# View recent log entries
tail -100 /Users/xavier.bouchard/Desktop/HeartBeat/roster_sync.log
```

## What Gets Updated

### Input
- Reads: `/data/processed/market/nhl_contracts_league_wide_2025_2026.parquet`
- Fetches: Active rosters from NHL API for all 32 teams

### Output
- Updates: `/data/processed/market/nhl_contracts_league_wide_2025_2026.parquet`
- Creates: `/data/processed/market/historical/nhl_contracts_league_wide_{date}.parquet`

### Fields Updated
- `roster_status`: "NHL" or "MINOR"
- `roster_sync_date`: ISO timestamp
- `last_status_change`: ISO timestamp
- `days_on_nhl_roster`: Counter

## Expected Results

After running the sync, you should see:

```
==================================================
DAILY ACTIVE ROSTER SYNC COMPLETE
==================================================
Status: success
Teams Synced: 32/32
Active NHL Players: ~736 (23 players × 32 teams)
NHL Roster Status: ~736
Minor Roster Status: ~remaining contracts
IR/LTIR (Preserved): varies (injured players)
Status Changes: varies (callups/senddowns)
==================================================
```

## Using the Data

### Calculate Cap Space

```python
import pandas as pd

# Load updated contracts
df = pd.read_parquet('data/processed/market/nhl_contracts_league_wide_2025_2026.parquet')

# Get MTL active roster
mtl_active = df[(df['team_abbrev'] == 'MTL') & (df['roster_status'] == 'NHL')]

# Calculate daily cap hit
active_cap = mtl_active['cap_hit_2025_26'].sum()
cap_ceiling = 88_000_000  # 2025-26 salary cap
daily_cap_space = cap_ceiling - active_cap

print(f"MTL Daily Cap Space: ${daily_cap_space:,.0f}")
```

### Track Roster Changes

```python
import pandas as pd
from datetime import datetime, timedelta

# Load today's snapshot
today = datetime.now().strftime("%Y_%m_%d")
df_today = pd.read_parquet(f'data/processed/market/historical/nhl_contracts_league_wide_{today}.parquet')

# Load yesterday's snapshot
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y_%m_%d")
df_yesterday = pd.read_parquet(f'data/processed/market/historical/nhl_contracts_league_wide_{yesterday}.parquet')

# Find changes
changes = df_today[df_today['last_status_change'] == datetime.now().date().isoformat()]
print("Today's Roster Moves:")
for _, player in changes.iterrows():
    print(f"  {player['full_name']} ({player['team_abbrev']}): {player['roster_status']}")
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'httpx'"

**Solution:**
```bash
pip install httpx
```

### Issue: "Contracts file not found"

**Solution:**
Ensure the contracts file exists at:
```
/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/market/nhl_contracts_league_wide_2025_2026.parquet
```

### Issue: "API failures for multiple teams"

**Solution:**
- Check internet connection
- Verify NHL API is accessible: https://api-web.nhle.com/v1/roster/MTL/current
- Wait and retry (API may be temporarily down)

### Issue: "Unexpected roster sizes"

**Solution:**
- This is normal during preseason or early season
- Some teams may have < 23 or > 23 players temporarily
- Check logs for specific team issues

## Files Created

### New Files
- ✅ `scripts/ingest/daily_active_roster_sync.py` - Main sync script
- ✅ `scripts/tests/test_roster_sync.py` - Test validation script
- ✅ `DAILY_ROSTER_SYNC_GUIDE.md` - Complete documentation
- ✅ `SETUP_ROSTER_SYNC.md` - This setup guide

### Updated Files
- ✅ `setup_roster_cron.sh` - Updated for new script (6 AM ET execution)
- ✅ `orchestrator/requirements.txt` - Added httpx dependency

### Deprecated Files
- ❌ `scripts/nightly_roster_sync.py` - Removed (replaced by new system)

## Next Steps

1. ✅ Install dependencies (`pip install httpx`)
2. ✅ Test the sync manually (`python3 scripts/ingest/daily_active_roster_sync.py`)
3. ✅ Set up cron automation (`./setup_roster_cron.sh`)
4. ✅ Monitor first automated run (check logs at 6 AM ET)
5. ✅ Integrate cap space calculations into your analytics

## Support

For detailed documentation, see:
- `DAILY_ROSTER_SYNC_GUIDE.md` - Complete system documentation
- `roster_sync.log` - Execution logs
- NHL API docs: https://api-web.nhle.com/

The system is production-ready and will maintain accurate roster status daily!

