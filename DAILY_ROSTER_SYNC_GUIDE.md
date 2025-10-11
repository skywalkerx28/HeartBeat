# Daily Active Roster Sync System

## Overview

The Daily Active Roster Sync system fetches current 23-man NHL rosters for all 32 teams and updates contract statuses to enable accurate daily cap space calculations.

## Key Features

- Fetches active rosters from NHL API endpoint: `https://api-web.nhle.com/v1/roster/{team}/current`
- Updates `roster_status` field: "NHL" for active roster, "MINOR" for non-roster players
- Maintains historical snapshots for trend analysis
- Tracks roster changes over time
- Enables dynamic daily cap space calculations
- Automated daily execution via cron

## Architecture

### Main Components

1. **Daily Active Roster Sync Script** (`scripts/daily_active_roster_sync.py`)
   - Fetches rosters for all 32 NHL teams
   - Cross-references with contracts parquet file
   - Updates roster status based on active roster presence
   - Saves historical snapshots

2. **NHL Roster Client** (`orchestrator/tools/nhl_roster_client.py`)
   - Handles API communication
   - Provides caching and error handling
   - Supports concurrent team roster fetching

3. **Cron Automation** (`setup_roster_cron.sh`)
   - Sets up daily execution at 6 AM ET
   - Logs to `roster_sync.log`

## Data Flow

```
NHL API (/v1/roster/{team}/current)
    ↓
NHLRosterClient (fetch all 32 teams)
    ↓
Build set of active NHL player IDs
    ↓
Load contracts parquet file
    ↓
Update roster_status:
  - If player_id in active set → "NHL"
  - If player_id not in active set → "MINOR"
    ↓
Save historical snapshot
    ↓
Update canonical contracts file
```

## Roster Status Logic

### Status Assignment

- **NHL**: Player is on an active 23-man NHL roster
- **MINOR**: Player has a contract but is not on any NHL roster (in AHL/minors)
- **IR**: Player on Injured Reserve (status preserved, not updated)
- **LTIR**: Player on Long-Term Injured Reserve (status preserved, not updated)
- **Unsigned**: Player is unsigned (status unchanged)

### Special Cases

- **IR/LTIR Preservation**: Players with IR or LTIR status are NOT updated, even if they appear on active rosters. This prevents incorrectly changing injured players to "NHL" status.
- **Unsigned players**: Skip status update entirely
- **Status changes**: Tracked with timestamp in `last_status_change` field
- **Roster presence vs injury status**: A player can technically be on the roster while on IR/LTIR for cap purposes, but their injury status takes precedence

## File Structure

### Input Files

- **Contracts File**: `/data/processed/market/nhl_contracts_league_wide_2025_2026.parquet`
  - Contains all player contracts league-wide
  - Includes MTL and NYI detailed contract data
  - Fields: player_id, team, cap_hit, signing_bonus, clauses, etc.

### Output Files

- **Updated Contracts**: `/data/processed/market/nhl_contracts_league_wide_2025_2026.parquet`
  - Same file, updated with current roster_status
  
- **Historical Snapshots**: `/data/processed/market/historical/nhl_contracts_league_wide_{YYYY_MM_DD}.parquet`
  - Daily snapshots for trend analysis
  - Retention: 60 days

### New Tracking Fields

The sync adds/updates these fields:

- `roster_status`: "NHL" or "MINOR"
- `roster_sync_date`: ISO timestamp of last sync
- `last_status_change`: ISO timestamp of last status change
- `days_on_nhl_roster`: Counter for consecutive days on NHL roster

## Usage

### Manual Execution

```bash
# Run sync for current season
python scripts/daily_active_roster_sync.py --season 2025-2026

# Get roster summary for a specific team
python scripts/daily_active_roster_sync.py --summary MTL

# Get summary for all teams
python scripts/daily_active_roster_sync.py --summary ALL
```

### Automated Execution

```bash
# Set up daily cron job (runs at 6 AM ET)
./setup_roster_cron.sh

# View cron jobs
crontab -l

# View logs
tail -f roster_sync.log
```

## Cap Space Calculation

With roster status updated, you can calculate daily cap space:

```python
import pandas as pd

# Load contracts
df = pd.read_parquet('data/processed/market/nhl_contracts_league_wide_2025_2026.parquet')

# Get MTL active roster
mtl_active = df[(df['team_abbrev'] == 'MTL') & (df['roster_status'] == 'NHL')]

# Calculate active cap hit
active_cap_hit = mtl_active['cap_hit_2025_26'].sum()
cap_space = 95_500_000 - active_cap_hit  # Assuming $95.5M cap

print(f"MTL Active Cap Hit: ${active_cap_hit:,.0f}")
print(f"MTL Cap Space: ${cap_space:,.0f}")
```

## Team Summaries

The sync generates team summaries with:

- Team abbreviation
- Active roster count (should be ~23)
- Active cap hit total
- List of NHL roster players
- List of MINOR/AHL players
- Last sync timestamp

## Error Handling

- **API Failures**: Retries with exponential backoff
- **Missing Teams**: Logged as errors, doesn't stop sync
- **Invalid Roster Sizes**: Alerts if < 20 or > 25 players
- **File Not Found**: Logs error and exits gracefully

## Monitoring

### Success Indicators

- All 32 teams synced successfully
- Roster counts are reasonable (20-25 per team)
- No API failures
- Historical snapshot created
- Contracts file updated

### Logs

Check `roster_sync.log` for:

- Sync start/completion times
- Teams synced successfully
- API errors
- Status changes detected
- Player movements (callups/senddowns)

### Status Changes

The script logs all roster status changes:

```
Status change: Cole Caufield (MTL): MINOR -> NHL
Status change: Joshua Roy (MTL): NHL -> MINOR
```

## Dependencies

### Required Python Packages

```
pandas>=2.0.0
pyarrow>=10.0.0
httpx>=0.24.0
asyncio
```

Install with:

```bash
pip install -r orchestrator/requirements.txt
```

## Troubleshooting

### Virtual Environment Issues

If venv path is broken:

```bash
# Recreate venv
python3 -m venv venv
source venv/bin/activate
pip install -r orchestrator/requirements.txt
```

### API Issues

If NHL API is down:

- Check https://api-web.nhle.com/v1/roster/MTL/current
- Wait for API to recover
- Script will retry on next scheduled run

### Missing Contracts File

If contracts file doesn't exist:

- Ensure market data sync has run
- Check file path in script
- Verify parquet file exists

## Migration from Old System

The old `nightly_roster_sync.py` is now deprecated. Key differences:

| Old System | New System |
|------------|------------|
| Syncs all player data | Syncs only roster status |
| No contract integration | Updates contract status |
| Single latest file | Historical snapshots |
| No status tracking | Tracks changes over time |
| General roster data | Active roster focus |

## Future Enhancements

Potential improvements:

- [ ] LTIR tracking and cap relief calculations
- [ ] Trade deadline roster lock detection
- [ ] Injury status integration
- [ ] Waiver wire player tracking
- [ ] Emergency recalls handling
- [ ] Real-time roster change alerts
- [ ] Cap compliance validation

## API Reference

### NHL Roster Endpoint

```
GET https://api-web.nhle.com/v1/roster/{team}/current

Response: {
  "forwards": [...],
  "defensemen": [...],
  "goalies": [...]
}
```

### Team Codes

All 32 NHL teams:

```
ANA, BOS, BUF, CAR, CBJ, CGY, CHI, COL,
DAL, DET, EDM, FLA, LAK, MIN, MTL, NJD,
NSH, NYI, NYR, OTT, PHI, PIT, SEA, SJS,
STL, TBL, TOR, UTA, VAN, VGK, WPG, WSH
```

## Support

For issues or questions:

1. Check logs: `roster_sync.log`
2. Verify API status
3. Review this documentation
4. Test manually with `--summary` flag

