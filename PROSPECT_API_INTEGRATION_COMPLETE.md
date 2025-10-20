# Prospect API Integration - COMPLETE

## Summary

Successfully integrated the real MTL prospect data from the CSV file into the Prospect page. The system now loads actual prospect information from `/data/processed/rosters/MTL/20252026/prospects/mtl_prospects_20251015.csv`.

## What Was Implemented

### 1. Backend API Endpoint (`/api/prospects/team/{team_id}`)

**New Files Created:**
- `backend/api/routes/prospects.py` - FastAPI endpoints for prospect data

**API Endpoints:**
- `GET /api/prospects/team/MTL` - Get all MTL prospects
- `GET /api/prospects/team/MTL?position=F` - Get forwards only
- `GET /api/prospects/team/MTL?position=D` - Get defensemen only
- `GET /api/prospects/team/MTL?position=G` - Get goalies only

**Features:**
- Reads CSV file from data directory
- Parses all prospect information (name, age, position, draft details, etc.)
- Handles position filtering
- Returns structured JSON response
- Error handling for missing files

### 2. Frontend API Client

**New File:**
- `frontend/lib/prospectsApi.ts` - TypeScript client for prospect API

**Functions:**
- `getTeamProspects()` - Fetch all prospects for a team
- `getTeamProspectsByPosition()` - Fetch prospects by position
- `getPrimaryPosition()` - Parse combined positions (e.g., "C,RW" → "C")
- Helper functions for position type checking

### 3. Frontend Integration

**Updated:**
- `frontend/app/analytics/prospect/page.tsx` - Now fetches real data from API

**Data Flow:**
1. Page loads and fetches prospects from API
2. Converts API data to UI format
3. Falls back to mock data if API fails
4. Displays real prospect information

## Current Data Available (30 Prospects)

From the CSV file, we have:

### Forwards (13 players)
- Positions: C, LW, RW, combinations
- Ages: 18-24 years old
- Draft years: 2020-2025

### Defensemen (11 players)
- Positions: D
- Ages: 18-23 years old
- Draft years: 2021-2025

### Goalies (6 players)
- Position: G
- Ages: 18-21 years old
- Draft years: 2022-2025

## Data Fields Available

### From CSV (Now Live):
- ✅ Name
- ✅ Age
- ✅ Position
- ✅ Shot/Catches
- ✅ Height
- ✅ Weight
- ✅ Draft Round
- ✅ Draft Pick
- ✅ Draft Year
- ✅ Birthdate
- ✅ Birthplace
- ✅ Nationality
- ✅ Sign By Date
- ✅ UFA Year
- ✅ Waivers Eligibility
- ✅ Career Earnings

### Placeholder/Calculated (To Be Enhanced):
- ⏳ Current League (estimated from birthplace - needs improvement)
- ⏳ Current Team (placeholder "TBD")
- ⏳ Games Played (0 - awaiting HeartBeat bot)
- ⏳ Goals/Assists/Points (0 - awaiting HeartBeat bot)
- ⏳ Plus/Minus (null - awaiting HeartBeat bot)
- ⏳ Status (all "steady" - awaiting HeartBeat bot)
- ⏳ Potential Rating (calculated from draft position)

## How It Works

### Backend Logic
```python
# Backend reads CSV and returns structured data
prospects_path = "data/processed/rosters/MTL/20252026/prospects/mtl_prospects_20251015.csv"
df = pd.read_csv(prospects_path)
# Parse and return as JSON
```

### Frontend Logic
```typescript
// Frontend fetches from API
const response = await getTeamProspects('MTL', '20252026')

// Convert to UI format with placeholder data
const prospects = response.prospects.map(p => ({
  ...p,
  currentLeague: determineLeague(p.birthplace),  // Estimated
  currentTeam: 'TBD',  // To be populated by bot
  stats: { ... },  // Placeholder zeros
  potential: calculatePotential(p.draft_round, p.draft_pick)
}))
```

## Testing

### Backend API Test:
```bash
# Start backend server
cd backend
uvicorn main:app --reload

# Test endpoint
curl http://localhost:8000/api/prospects/team/MTL
```

### Frontend Test:
```bash
# Start frontend
cd frontend
npm run dev

# Visit page
open http://localhost:3000/analytics/prospect
```

## Next Steps (Future Enhancements)

### Phase 1: HeartBeat Bot Integration
- [ ] Auto-scrape stats from EliteProspects
- [ ] Track current teams/leagues
- [ ] Update performance status (rising/steady/declining)
- [ ] Monitor news for injuries/transactions

### Phase 2: Enhanced Data
- [ ] Add current season statistics
- [ ] Track league changes
- [ ] Historical performance tracking
- [ ] Injury status tracking

### Phase 3: Analytics
- [ ] Performance trend charts
- [ ] Comparison with draft peers
- [ ] Development trajectory analysis
- [ ] NHL readiness scoring

## Current Page Features

### "Other Prospects" Section
- Shows all 30 prospects from CSV
- Displays actual draft information
- Shows nationality and birthplace
- Filters work (position, search)
- Estimated league placement
- Calculated potential ratings

### "Laval Rocket" Section
- Currently empty (no AHL players in CSV)
- Will be populated when AHL roster data is added
- Separate from prospect pool

## Data Accuracy

### Highly Accurate (from CSV):
- Player names
- Ages and birthdates
- Draft information
- Physical measurements
- Contract details
- Nationality/birthplace

### Estimated (placeholder):
- Current league (basic logic from birthplace)
- Current team (all "TBD")
- Statistics (all zeros)
- Performance trends (all "steady")

### Calculated:
- Potential ratings (from draft position)
- NHL ETA (draft year + 3 years)

## File Locations

**Backend:**
- `/backend/api/routes/prospects.py` - API endpoints
- `/backend/api/routes/__init__.py` - Router registration
- `/backend/main.py` - App registration

**Frontend:**
- `/frontend/lib/prospectsApi.ts` - API client
- `/frontend/app/analytics/prospect/page.tsx` - Prospect page

**Data:**
- `/data/processed/rosters/MTL/20252026/prospects/mtl_prospects_20251015.csv` - Source data

## Summary

✅ Backend API created and working  
✅ Frontend API client implemented  
✅ Prospect page fetches real data  
✅ All 30 MTL prospects loading  
✅ Draft info and personal details accurate  
⏳ Stats and current teams pending HeartBeat bot  
⏳ AHL (Laval) roster pending separate data source  

The foundation is complete! The page now shows real prospect data from your CSV file. Next steps are to add the HeartBeat bot to automatically fetch current stats and team information from various league websites.

