# NHL Market Analytics - Data Population Guide

## Overview

Your infrastructure is ready. Now you need to populate `data/processed/market/` with real NHL contract data in Parquet format.

---

## Required Data Files

You need to create 6 Parquet files (you can start with just #1 and #2):

### Priority 1 (Essential):
1. **players_contracts_2025_2026.parquet** - Individual player contracts
2. **contract_performance_index_2025_2026.parquet** - Performance metrics
3. **team_cap_management_2025_2026.parquet** - Team cap space

### Priority 2 (Nice to have):
4. **trade_history_2025_2026.parquet** - Trade history
5. **market_comparables_2025_2026.parquet** - Contract comparables
6. **league_market_summary_2025_2026.parquet** - League summaries

---

## Data Format Requirements

### File 1: Player Contracts (CRITICAL)

This file should include **ALL players**:
- ✅ **Active NHL roster** (`contract_status=active`, `roster_status=roster`)
- ✅ **Non-roster (minors/AHL)** (`contract_status=active`, `roster_status=non_roster`)
- ✅ **Unsigned prospects (reserve list)** (`contract_status=unsigned`, `roster_status=reserve_list`)
  - These are drafted players whose rights the team holds
  - Must include `draft_year`, `draft_round`, `draft_overall`, `must_sign_by`
  - Set `cap_hit=0` and leave contract fields empty

**CSV Template** (`player_contracts.csv`):

```csv
nhl_player_id,full_name,team_abbrev,position,age,cap_hit,contract_years_total,years_remaining,contract_start_date,contract_end_date,signing_date,contract_type,no_trade_clause,no_movement_clause,signing_age,signing_team,contract_status,retained_percentage,season,sync_date,data_source
8480018,Nick Suzuki,MTL,C,25,7875000,8,6,2022-10-01,2030-06-30,2022-07-01,UFA,false,true,23,MTL,active,0.0,2025-2026,2025-10-09,manual
8479318,Cole Caufield,MTL,RW,23,7850000,8,7,2023-10-01,2031-06-30,2023-07-05,UFA,false,false,22,MTL,active,0.0,2025-2026,2025-10-09,manual
8481522,Juraj Slafkovsky,MTL,LW,20,925000,3,2,2023-10-01,2026-06-30,2023-09-15,ELC,false,false,19,MTL,active,0.0,2025-2026,2025-10-09,manual
8480800,Kirby Dach,MTL,C,23,3362500,4,2,2023-10-01,2027-06-30,2023-08-01,RFA,false,false,22,MTL,active,0.0,2025-2026,2025-10-09,manual
```

**Required Fields**:
- `nhl_player_id` (int64) - NHL's official player ID
- `full_name` (string) - Player name
- `team_abbrev` (string) - Team (MTL, TOR, etc.)
- `position` (string) - Position (C, LW, RW, D, G)
- `age` (int32) - Current age
- `cap_hit` (float64) - Annual cap hit in dollars
- `contract_years_total` (int32) - Total contract length
- `years_remaining` (int32) - Years left
- `contract_start_date` (date) - YYYY-MM-DD
- `contract_end_date` (date) - YYYY-MM-DD
- `signing_date` (date) - YYYY-MM-DD
- `contract_type` (string) - ELC, RFA, UFA, Extension
- `no_trade_clause` (bool) - true/false
- `no_movement_clause` (bool) - true/false
- `signing_age` (int32) - Age when signed
- `signing_team` (string) - Team that signed
- `contract_status` (string) - active, buyout, ltir, retained
- `retained_percentage` (float64) - 0.0 to 50.0
- `season` (string) - 2025-2026
- `sync_date` (date) - Today's date
- `data_source` (string) - Where you got the data

### File 2: Contract Performance Index

**CSV Template** (`contract_performance_index.csv`):

```csv
nhl_player_id,season,performance_index,contract_efficiency,market_value,surplus_value,performance_percentile,contract_percentile,status,last_calculated
8480018,2025-2026,135.0,1.71,11000000,3125000,85.5,92.3,overperforming,2025-10-09 12:00:00
8479318,2025-2026,145.0,1.85,12500000,4650000,90.2,95.1,overperforming,2025-10-09 12:00:00
8481522,2025-2026,95.0,10.27,2100000,1175000,65.3,98.5,overperforming,2025-10-09 12:00:00
8480800,2025-2026,85.0,0.75,2500000,-862500,55.1,45.2,underperforming,2025-10-09 12:00:00
```

**How to Calculate** (or use estimates):
- `performance_index`: 0-200 scale (100 = average), based on points/60, xG, defense
- `contract_efficiency`: performance_index / (cap_hit / league_avg)
- `market_value`: Estimated fair value based on production
- `surplus_value`: market_value - cap_hit
- `status`: overperforming (eff > 115), fair (85-115), underperforming (< 85)

### File 3: Team Cap Management

**CSV Template** (`team_cap_management.csv`):

```csv
team_abbrev,season,cap_ceiling,cap_hit_total,cap_space,ltir_pool,deadline_cap_space,active_roster_count,contracts_expiring,projected_next_season_cap,committed_next_season,sync_date
MTL,2025-2026,95500000,87364000,8136000,0,12500000,23,5,104000000,65200000,2025-10-09
TOR,2025-2026,95500000,93200000,2300000,0,5000000,22,7,104000000,72000000,2025-10-09
```

**Key Values**:
- `cap_ceiling`: **$95,500,000** (2025-26)
- `projected_next_season_cap`: **$104,000,000** (2026-27)
- Calculate `cap_space` = cap_ceiling - cap_hit_total
- `deadline_cap_space` = accumulated cap space at trade deadline

---

## Data Sources

### Where to Get Contract Data:

1. **CapFriendly Archives** (via Wayback Machine)
   - Historical contracts pre-2024
   - NMC/NTC details
   
2. **PuckPedia.com**
   - Current active contracts
   - Cap hit breakdowns
   - Trade clauses

3. **CapWages.com**
   - Salary details
   - Contract structures

4. **NHLPA.com**
   - Official salary data (public)
   - Annual salary disclosures

5. **Team Websites**
   - Official contract announcements
   - Press releases

6. **NHL.com**
   - Transaction logs
   - Official contracts database

---

## Conversion Script

Create a Python script to convert your CSV to Parquet:

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from pathlib import Path

# Import schemas
from scripts.market_data.schemas import PLAYER_CONTRACTS_SCHEMA

# Load your CSV
df = pd.read_csv('your_contract_data.csv')

# Data type conversions
df['cap_hit'] = df['cap_hit'].astype(float)
df['age'] = df['age'].astype('int32')
df['contract_years_total'] = df['contract_years_total'].astype('int32')
df['years_remaining'] = df['years_remaining'].astype('int32')
df['signing_age'] = df['signing_age'].astype('int32')

# Convert dates
df['contract_start_date'] = pd.to_datetime(df['contract_start_date'])
df['contract_end_date'] = pd.to_datetime(df['contract_end_date'])
df['signing_date'] = pd.to_datetime(df['signing_date'])
df['sync_date'] = pd.to_datetime(df['sync_date'])

# Convert booleans
df['no_trade_clause'] = df['no_trade_clause'].astype(bool)
df['no_movement_clause'] = df['no_movement_clause'].astype(bool)

# Add cap_hit_percentage
df['cap_hit_percentage'] = (df['cap_hit'] / 95500000) * 100

# Convert to Parquet
table = pa.Table.from_pandas(df, schema=PLAYER_CONTRACTS_SCHEMA)
pq.write_table(
    table,
    'data/processed/market/players_contracts_2025_2026.parquet',
    compression='ZSTD',
    compression_level=3
)

print(f"✅ Converted {len(df)} contracts to Parquet")
```

---

## Quick Start Options

### Option A: Manual Entry (Small Scale)

**For MTL only** (20-25 contracts):

1. Create `mtl_contracts.csv` with 20-25 rows
2. Manually enter contracts from PuckPedia
3. Run conversion script
4. Test immediately

**Time**: 2-3 hours for full MTL roster

### Option B: Web Scraping (League-Wide)

**For all 32 teams** (700+ contracts):

1. Scrape PuckPedia team pages
2. Parse HTML tables
3. Batch convert to Parquet
4. Upload to system

**Time**: 1-2 days to build scraper

### Option C: API Integration (Automated)

**Build API connector**:

1. Find/build NHL contract API client
2. Fetch all active contracts
3. Transform to our schema
4. Daily automated sync

**Time**: 2-3 days for robust solution

---

## Minimal Viable Dataset

**Start with just MTL** to test the full workflow:

### Step 1: Create MTL Contracts CSV

```csv
nhl_player_id,full_name,team_abbrev,position,age,cap_hit,years_remaining,contract_type,season,data_source
8480018,Nick Suzuki,MTL,C,25,7875000,6,UFA,2025-2026,puckpedia
8479318,Cole Caufield,MTL,RW,23,7850000,7,UFA,2025-2026,puckpedia
8481522,Juraj Slafkovsky,MTL,LW,20,925000,2,ELC,2025-2026,puckpedia
8480800,Kirby Dach,MTL,C,23,3362500,2,RFA,2025-2026,puckpedia
```

Add these **required fields with defaults**:
- `contract_years_total` = years_remaining + 1 (estimate)
- `contract_start_date` = 2024-10-01 (season start)
- `contract_end_date` = start + years
- `signing_date` = start - 1 year (estimate)
- `no_trade_clause` = false (unless you know)
- `no_movement_clause` = false (unless you know)
- `signing_age` = age - 1 (estimate)
- `signing_team` = MTL
- `contract_status` = active
- `retained_percentage` = 0.0
- `sync_date` = today

### Step 2: Run Conversion

Use the conversion script above to create the Parquet file.

### Step 3: Test

Restart backend and check if STANLEY now says "Nick Suzuki" instead of "Player 8480018"!

---

## Performance Index Calculation

If you don't have performance data yet, use **simple estimates**:

```python
import pandas as pd

contracts = pd.read_csv('mtl_contracts.csv')
performance = []

for _, player in contracts.iterrows():
    # Simple heuristic based on cap hit
    if player['cap_hit'] > 7000000:
        # High paid = expect high performance
        perf_index = 120 + random.uniform(-20, 30)
        efficiency = perf_index / (player['cap_hit'] / 3000000)
    elif player['cap_hit'] < 1500000:
        # ELC/cheap = often outperform
        perf_index = 110 + random.uniform(-15, 40)
        efficiency = perf_index / (player['cap_hit'] / 3000000)
    else:
        # Mid-tier
        perf_index = 100 + random.uniform(-25, 25)
        efficiency = perf_index / (player['cap_hit'] / 3000000)
    
    # Status
    if efficiency > 115:
        status = 'overperforming'
    elif efficiency > 85:
        status = 'fair'
    else:
        status = 'underperforming'
    
    performance.append({
        'nhl_player_id': player['nhl_player_id'],
        'season': '2025-2026',
        'performance_index': round(perf_index, 2),
        'contract_efficiency': round(efficiency, 2),
        'market_value': round(player['cap_hit'] * (perf_index / 100), 2),
        'surplus_value': round(player['cap_hit'] * ((perf_index / 100) - 1), 2),
        'performance_percentile': min(100, perf_index / 2),
        'contract_percentile': min(100, efficiency / 2),
        'status': status,
        'last_calculated': datetime.now()
    })

perf_df = pd.DataFrame(performance)
# Convert to Parquet using CONTRACT_PERFORMANCE_INDEX_SCHEMA
```

---

## Data Validation Checklist

Before converting to Parquet, verify:

- [ ] All `nhl_player_id` values are valid integers
- [ ] All `cap_hit` values are realistic ($750K - $15M)
- [ ] `team_abbrev` uses 3-letter codes (MTL, TOR, BOS)
- [ ] `position` is one of: C, LW, RW, D, G
- [ ] `contract_type` is one of: ELC, RFA, UFA, Extension
- [ ] `contract_status` is one of: active, buyout, ltir, retained
- [ ] Dates are in YYYY-MM-DD format
- [ ] Booleans are true/false
- [ ] `season` is "2025-2026" format
- [ ] No null values in required fields

---

## Quick Conversion Template

Save this as `scripts/market_data/csv_to_parquet.py`:

```python
"""
Convert CSV contract data to Parquet format.
Usage: python scripts/market_data/csv_to_parquet.py your_contracts.csv
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import sys
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.market_data.schemas import PLAYER_CONTRACTS_SCHEMA

def convert_csv_to_parquet(csv_file: str):
    """Convert contract CSV to Parquet."""
    
    # Load CSV
    df = pd.read_csv(csv_file)
    
    print(f"Loaded {len(df)} contracts from {csv_file}")
    
    # Type conversions
    df['nhl_player_id'] = df['nhl_player_id'].astype('int64')
    df['age'] = df['age'].astype('int32')
    df['contract_years_total'] = df['contract_years_total'].astype('int32')
    df['years_remaining'] = df['years_remaining'].astype('int32')
    df['signing_age'] = df['signing_age'].astype('int32')
    df['cap_hit'] = df['cap_hit'].astype('float64')
    df['retained_percentage'] = df['retained_percentage'].astype('float64')
    
    # Date conversions
    df['contract_start_date'] = pd.to_datetime(df['contract_start_date'])
    df['contract_end_date'] = pd.to_datetime(df['contract_end_date'])
    df['signing_date'] = pd.to_datetime(df['signing_date'])
    df['sync_date'] = pd.to_datetime(df['sync_date'])
    
    # Boolean conversions
    df['no_trade_clause'] = df['no_trade_clause'].map({'true': True, 'false': False, True: True, False: False})
    df['no_movement_clause'] = df['no_movement_clause'].map({'true': True, 'false': False, True: True, False: False})
    
    # Calculate cap_hit_percentage
    df['cap_hit_percentage'] = (df['cap_hit'] / 95500000) * 100
    
    # Validate schema
    required_columns = [
        'nhl_player_id', 'full_name', 'team_abbrev', 'position', 'age',
        'cap_hit', 'cap_hit_percentage', 'contract_years_total', 'years_remaining',
        'contract_start_date', 'contract_end_date', 'signing_date',
        'contract_type', 'no_trade_clause', 'no_movement_clause',
        'signing_age', 'signing_team', 'contract_status', 'retained_percentage',
        'season', 'sync_date', 'data_source'
    ]
    
    missing = set(required_columns) - set(df.columns)
    if missing:
        print(f"❌ Missing required columns: {missing}")
        return
    
    # Convert to Parquet
    output_path = 'data/processed/market/players_contracts_2025_2026.parquet'
    table = pa.Table.from_pandas(df, schema=PLAYER_CONTRACTS_SCHEMA, preserve_index=False)
    
    pq.write_table(
        table,
        output_path,
        compression='ZSTD',
        compression_level=3
    )
    
    print(f"✅ Saved {len(df)} contracts to {output_path}")
    print(f"   File size: {Path(output_path).stat().st_size / 1024:.1f} KB")
    
    # Show team breakdown
    print("\nTeam distribution:")
    print(df['team_abbrev'].value_counts())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python csv_to_parquet.py your_contracts.csv")
        sys.exit(1)
    
    convert_csv_to_parquet(sys.argv[1])
```

---

## Recommended Workflow

### Week 1: MTL Only
1. Manually enter 20-25 MTL contracts from PuckPedia
2. Convert to Parquet
3. Test with STANLEY
4. Verify accuracy

### Week 2: Division Rivals
1. Add TOR, BOS, OTT, BUF, DET, FLA, TBL
2. ~150 contracts total
3. Test market comparisons

### Week 3: League-Wide
1. Add remaining 25 teams
2. ~700 contracts total
3. Full market analytics operational

### Ongoing: Automation
1. Build daily sync script
2. Auto-update from PuckPedia API
3. Track trades and signings

---

## What You Need to Gather (Minimum)

**For each player**:
- ✅ Name
- ✅ Team
- ✅ Position
- ✅ Cap hit (AAV)
- ✅ Years remaining
- ⚠️ Contract type (can estimate from age/cap hit)
- ⚠️ NMC/NTC (false if unknown)
- ⚠️ Signing details (can estimate)

**Optional but helpful**:
- Performance stats (for accurate efficiency)
- Signing date
- Original contract length
- Bonus structure

---

## Testing Your Data

After populating:

```bash
# 1. Verify Parquet file
python3 -c "
import pandas as pd
df = pd.read_parquet('data/processed/market/players_contracts_2025_2026.parquet')
print(f'Total contracts: {len(df)}')
print(f'Teams: {df[\"team_abbrev\"].nunique()}')
print(df.head())
"

# 2. Test API
curl http://localhost:8000/api/v1/market/contracts/team/MTL

# 3. Test STANLEY
# Ask: "What's Nick Suzuki's contract?"
# Should return real data!
```

---

## Production Readiness Status

**Infrastructure**: ✅ 100% Complete
- Parquet schemas defined
- BigQuery DDL ready
- API endpoints operational
- Orchestrator tools registered
- Frontend integrated
- STANLEY working

**Data**: ⏳ Your Responsibility
- Gather real contract data
- Convert to Parquet format
- Populate database

**Timeline**:
- **Option 1**: MTL only → 2-3 hours
- **Option 2**: 8 teams → 1 day
- **Option 3**: All 32 teams → 2-3 days

---

## Immediate Action

**Create this file**: `mtl_contracts.csv`

Add just **5 MTL contracts** to start:
- Nick Suzuki ($7.875M)
- Cole Caufield ($7.85M)
- Juraj Slafkovsky ($925K)
- Kirby Dach ($3.36M)
- Josh Anderson ($5.5M)

Then run the conversion script and test!

**The infrastructure is ready - just needs real data!** 🎯

