# NHL Market Analytics - Quick Start Guide

## Immediate Setup (5 Minutes)

### Step 1: Generate Sample Data

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat
python scripts/market_data/generate_sample_market_data.py
```

This creates sample Parquet files in `data/processed/market/`:
- `players_contracts_2025_2026.parquet`
- `contract_performance_index_2025_2026.parquet`
- `team_cap_management_2025_2026.parquet`
- `trade_history_2025_2026.parquet`
- `market_comparables_2025_2026.parquet`
- `league_market_summary_2025_2026.parquet`

### Step 2: Test Local APIs (Without BigQuery)

The system works immediately with Parquet fallback:

```bash
# Start backend (if not running)
cd backend
python main.py

# Test in another terminal
curl http://localhost:8000/api/v1/market/health
```

### Step 3: Test Frontend

```bash
# Start frontend (if not running)
cd frontend
npm run dev

# Visit: http://localhost:3000/analytics/market
```

The market page will load sample data via API.

---

## BigQuery Setup (Optional - For Production)

### Prerequisites

1. Google Cloud SDK installed
2. Authentication configured: `gcloud auth application-default login`
3. Project ID: `heartbeat-474020`

### Setup Commands

```bash
# 1. Create infrastructure
python scripts/market_data/setup_bigquery.py

# 2. Upload sample data to GCS
gsutil cp data/processed/market/*.parquet gs://heartbeat-market-data/contracts/

# 3. Create BigQuery tables
bq query < scripts/market_data/bigquery_setup.sql

# 4. Verify
bq ls heartbeat-474020:market
```

---

## Testing the Complete Stack

### 1. Test REST APIs

```bash
# Health check
curl http://localhost:8000/api/v1/market/health

# Get contracts for MTL (will use sample data)
curl http://localhost:8000/api/v1/market/contracts/team/MTL?season=2025-2026

# Get cap summary
curl http://localhost:8000/api/v1/market/cap/team/MTL

# Get player contract (sample data has Player XXXXX names)
curl "http://localhost:8000/api/v1/market/contracts/player/name/Player%208470000"
```

### 2. Test Orchestrator Tools

```python
import asyncio
from orchestrator.agents.qwen3_best_practices_orchestrator import Qwen3BestPracticesOrchestrator
from orchestrator.utils.state import create_initial_state

async def test_market_tools():
    orchestrator = Qwen3BestPracticesOrchestrator()
    state = create_initial_state("Test market tools")
    
    # Test contract lookup
    result = await orchestrator._execute_tool(
        "get_player_contract",
        {"player_name": "Player 8470000", "team": "MTL"},
        state
    )
    print("Contract:", result)
    
    # Test cap analysis
    result = await orchestrator._execute_tool(
        "get_team_cap_analysis",
        {"team": "MTL", "season": "2025-2026"},
        state
    )
    print("Cap Summary:", result)

asyncio.run(test_market_tools())
```

### 3. Test Frontend

1. Open `http://localhost:3000/analytics/market`
2. Should display:
   - Team cap summary
   - Contract efficiency table
   - Cap projections chart
   - High value assets list
   - Risk watch list

---

## STANLEY LLM Integration

### Ask STANLEY Market Questions

The orchestrator has 5 new market tools. Test via chat:

**Contract Questions**:
- "What's the cap hit for Player 8470000?"
- "Show me MTL's cap space"
- "Which MTL players are overperforming their contracts?"

**Cap Analysis**:
- "Does MTL have space for a $5M player?"
- "What's MTL's projected cap space next season?"
- "How many contracts expire this year?"

**Market Intelligence**:
- "Find comparable contracts for Player 8470000"
- "What are recent trades involving MTL?"
- "What's the average cap hit for centers league-wide?"

STANLEY will use the appropriate market tools and synthesize answers.

---

## Customizing Sample Data

Edit `scripts/market_data/generate_sample_market_data.py`:

### Add Real Player Names

```python
# Around line 150, replace:
'full_name': f"Player {player_id}",

# With:
player_names = {
    'MTL': ['Nick Suzuki', 'Cole Caufield', 'Juraj Slafkovsky', ...],
    'TOR': ['Auston Matthews', 'William Nylander', ...],
    # etc.
}
'full_name': random.choice(player_names.get(team, [f"Player {player_id}"])),
```

### Adjust Contract Ranges

```python
# Line ~70
self.contract_ranges = {
    'C': (750000, 13500000),   # Increase max for McDavid-level
    'LW': (750000, 11500000),
    'RW': (750000, 11500000),
    'D': (750000, 11000000),
    'G': (750000, 11000000)
}
```

### Change Cap Ceiling

```python
# Line ~78
self.cap_ceiling = 95000000  # 2026-27 projected cap
```

Then regenerate:
```bash
python scripts/market_data/generate_sample_market_data.py
```

---

## Troubleshooting

### Issue: API returns 404

**Solution**: Ensure sample data is generated
```bash
ls data/processed/market/
# Should show 6 .parquet files
```

### Issue: Frontend shows "Failed to load"

**Solution**: Check backend is running
```bash
curl http://localhost:8000/api/v1/market/health
```

### Issue: BigQuery errors

**Solution**: System falls back to Parquet automatically. Check:
```bash
# Verify GCS bucket exists
gsutil ls gs://heartbeat-market-data/

# Verify BigQuery tables
bq ls heartbeat-474020:market
```

### Issue: Orchestrator tools fail

**Solution**: Check data_catalog path
```python
# In orchestrator initialization
self.data_catalog = HeartBeatDataCatalog(settings.parquet.data_directory)
# Ensure this points to: /Users/xavier.bouchard/Desktop/HeartBeat/data/processed
```

---

## Data Population Workflow

When you're ready to add real data:

### 1. Create CSV Template

```csv
nhl_player_id,full_name,team_abbrev,position,age,cap_hit,years_remaining,contract_type,no_trade_clause,no_movement_clause
8480018,Nick Suzuki,MTL,C,25,7875000,6,UFA,false,true
8479318,Cole Caufield,MTL,RW,23,7850000,7,UFA,false,false
```

### 2. Convert to Parquet

```python
import pandas as pd
import pyarrow.parquet as pq
from scripts.market_data.schemas import PLAYER_CONTRACTS_SCHEMA

# Load CSV
df = pd.read_csv('real_contracts.csv')

# Add required columns
df['contract_years_total'] = df['years_remaining'] + 1  # Estimate
df['contract_start_date'] = pd.to_datetime('2024-10-01')
df['contract_end_date'] = df['contract_start_date'] + pd.DateOffset(years=df['contract_years_total'])
df['signing_date'] = df['contract_start_date'] - pd.DateOffset(years=1)
df['signing_age'] = df['age'] - 1
df['signing_team'] = df['team_abbrev']
df['contract_status'] = 'active'
df['retained_percentage'] = 0.0
df['season'] = '2025-2026'
df['sync_date'] = pd.Timestamp.now().date()
df['data_source'] = 'manual_entry'
df['cap_hit_percentage'] = (df['cap_hit'] / 92000000) * 100

# Convert to Parquet
table = pa.Table.from_pandas(df, schema=PLAYER_CONTRACTS_SCHEMA)
pq.write_table(table, 'data/processed/market/players_contracts_real.parquet')
```

### 3. Update API to Use Real Data

System automatically uses newest Parquet files. No code changes needed.

---

## Performance Tips

### Enable Query Caching

```python
# In orchestrator/tools/market_data_client.py
market_client = MarketDataClient(
    enable_cache=True,        # Enable
    cache_ttl_seconds=600     # 10 minutes
)
```

### Optimize BigQuery Costs

```sql
-- Use native tables for current season
SELECT * FROM `heartbeat-474020.market.players_contracts`
WHERE season = '2025-2026'

-- Use external tables for historical
SELECT * FROM `heartbeat-474020.market.players_contracts_external`
WHERE season < '2024-2025'
```

### Reduce Frontend Latency

```typescript
// Cache cap summary client-side
const [capSummary, setCapSummary] = useState<TeamCapSummary | null>(null)

useEffect(() => {
  const cached = localStorage.getItem('mtl_cap_summary')
  if (cached) {
    const { data, timestamp } = JSON.parse(cached)
    if (Date.now() - timestamp < 600000) {  // 10 min
      setCapSummary(data)
      return
    }
  }
  
  // Fetch from API...
}, [])
```

---

## Ready for Production

Your framework is complete. When you have real contract data:

1. **Replace** sample data with real Parquet files
2. **Upload** to GCS (optional for BigQuery)
3. **Test** all endpoints return real data
4. **Deploy** to production

The architecture supports:
- All 32 NHL teams
- Historical multi-season data
- Real-time cap updates
- Trade tracking
- Market analysis
- Contract comparisons

**No code changes needed** - just populate the database!

---

## Summary

**Immediate Use**: ✅ Works now with sample data  
**BigQuery Setup**: Optional for production scale  
**Real Data**: Your responsibility to populate  
**LLM Integration**: Fully integrated with STANLEY  
**Production Ready**: Enterprise-grade architecture  

Start testing immediately with sample data, then populate with real contracts when ready!

