# Depth Chart Integration - Complete

## Summary

Successfully integrated the HeartBeat depth chart database with the contracts page to display roster information enriched with player data.

## What Was Implemented

### 1. Player Enrichment System (`backend/bot/player_enrichment.py`)
- Matches depth chart players to unified roster historical data
- Enriches players with:
  - NHL Player ID
  - Birth date and country
  - Height and weight  
  - Shoots/Catches handedness
  - Headshot URLs
- **Result:** 1,081 out of 2,154 players (50.2%) successfully enriched

### 2. Database Schema Updates
- Added enrichment fields to `team_rosters` table:
  - `birth_date`, `birth_country`
  - `height_inches`, `weight_pounds`
  - `shoots_catches`, `headshot`
- Maintained draft information fields for unsigned players

### 3. Depth Chart Scraper Updates
- Integrated player enrichment into scraping pipeline
- Updated CSV export to exclude scraped_date column
- Added complete enrichment fields to CSV output
- All 32 NHL teams successfully scraped with enrichment

### 4. Backend API Endpoint
**New Endpoint:** `GET /api/v1/market/depth-chart/{team_code}`

Query Parameters:
- `roster_status` (optional): Filter by 'roster', 'non_roster', or 'unsigned'

Response includes:
- Player roster data from depth chart database
- Enrichment fields (birth info, physical stats, headshot)
- Roster breakdown statistics

### 5. Frontend Integration

#### Updated `frontend/lib/marketApi.ts`
- Added `DepthChartPlayer` interface
- Added `TeamDepthChart` interface
- Added `getTeamDepthChart()` function

#### Updated `frontend/app/contracts/page.tsx`
- Modified data fetching to use depth chart database as source of truth
- Merges depth chart roster with contract data by player_id
- **NHL Roster:** Displays players with `roster_status = 'roster'`
- **AHL Roster:** Displays players with `roster_status = 'non_roster'`
- Contract information matched and displayed for each player

## Data Flow

```
Depth Chart Database (team_rosters)
          |
          ↓
    API Endpoint (/api/v1/market/depth-chart/{team})
          |
          ↓
  Frontend Contracts Page
          |
          ↓
   Merge with Contract Data
          |
          ↓
Display NHL Roster (right) & AHL Roster (left)
```

## CSV Files Generated

All 32 teams have enriched depth chart CSV files at:
`data/depth_charts/{TEAM}_depth_chart_2025-10-18.csv`

### CSV Columns:
1. player_name
2. player_id (NHL ID)
3. position
4. roster_status
5. dead_cap
6. jersey_number
7. age
8. birth_date
9. birth_country
10. height_inches
11. weight_pounds
12. shoots_catches
13. drafted_by
14. draft_year
15. draft_round
16. draft_overall
17. must_sign_date
18. headshot (URL)

## Statistics

- **Total Players:** 2,154 across all 32 teams
- **Enriched Players:** 1,081 (50.2%)
- **Unenriched:** 1,073 (recent prospects/minor leaguers not in unified roster)
- **Dead Cap Players:** 46 (buyouts, retained salary)

## Usage

### Backend API
```bash
# Get full depth chart
curl http://localhost:8000/api/v1/market/depth-chart/MTL

# Get only NHL roster
curl http://localhost:8000/api/v1/market/depth-chart/MTL?roster_status=roster

# Get only AHL roster
curl http://localhost:8000/api/v1/market/depth-chart/MTL?roster_status=non_roster
```

### Frontend
```typescript
import { getTeamDepthChart } from '@/lib/marketApi'

// Get full depth chart
const depthChart = await getTeamDepthChart('MTL')

// Get only roster players
const nhlRoster = await getTeamDepthChart('MTL', 'roster')

// Get only non-roster (AHL) players
const ahlRoster = await getTeamDepthChart('MTL', 'non_roster')
```

## Files Modified

### Backend
- `backend/api/routes/market.py` - Added depth chart endpoint
- `backend/bot/db.py` - Updated schema and queries
- `backend/bot/scrape_depth_charts.py` - Integrated enrichment, updated CSV export
- `backend/bot/player_enrichment.py` - **NEW** - Player matching and enrichment

### Frontend
- `frontend/lib/marketApi.ts` - Added depth chart API function
- `frontend/app/contracts/page.tsx` - Integrated depth chart data

### Data
- `data/depth_charts/*.csv` - 32 enriched CSV files
- `data/heartbeat_news.duckdb` - Updated team_rosters table

## Next Steps

The contracts page now displays:
- ✅ NHL Roster from depth chart (roster status = 'roster')
- ✅ AHL Roster from depth chart (roster status = 'non_roster')
- ✅ Contract information matched by player_id
- ✅ Enrichment data (birth info, physical stats, headshots)

All data is live and automatically updates when teams are switched.

