# Profile Pages - Backend API Requirements

## Overview
This document outlines the backend API endpoints needed to support the player and team profile pages in the HeartBeat analytics platform.

## Team Profile Endpoints

### 1. GET `/api/team/{teamId}/profile`
**Purpose:** Retrieve team overview data for profile page

**Parameters:**
- `teamId` (path): Team abbreviation (MTL, TOR, BOS, etc.)

**Response:**
```json
{
  "teamId": "MTL",
  "name": "Montreal Canadiens",
  "abbreviation": "MTL",
  "division": "Atlantic",
  "conference": "Eastern",
  "record": {
    "wins": 25,
    "losses": 30,
    "otLosses": 5,
    "points": 55
  },
  "stats": {
    "goalsFor": 180,
    "goalsAgainst": 205,
    "ppPercent": 22.3,
    "pkPercent": 78.5,
    "shotsPerGame": 30.2,
    "shotsAgainstPerGame": 31.5
  },
  "logoUrl": "https://assets.nhle.com/logos/nhl/svg/MTL_light.svg"
}
```

### 2. GET `/api/team/{teamId}/performance`
**Purpose:** Retrieve performance metrics and chart data

**Parameters:**
- `teamId` (path): Team abbreviation
- `dateRange` (query, optional): Number of days (default 30)

**Response:**
```json
{
  "goalsPerGame": [
    {"date": "2025-10-01", "value": 2.8},
    {"date": "2025-10-02", "value": 3.1}
  ],
  "xGoalsPerGame": [
    {"date": "2025-10-01", "value": 2.5},
    {"date": "2025-10-02", "value": 2.9}
  ],
  "winLossPattern": [
    {"date": "2025-10-01", "result": "W"},
    {"date": "2025-10-02", "result": "L"}
  ],
  "homeAwaySplits": {
    "home": {"gf": 105, "ga": 95, "record": "15-8-2"},
    "away": {"gf": 95, "ga": 110, "record": "10-12-3"}
  }
}
```

### 3. GET `/api/team/{teamId}/matchups`
**Purpose:** Retrieve head-to-head matchup history

**Parameters:**
- `teamId` (path): Team abbreviation
- `season` (query, optional): Season (default current season)

**Response:**
```json
{
  "matchups": [
    {
      "opponent": "TOR",
      "gamesPlayed": 3,
      "wins": 2,
      "losses": 1,
      "otLosses": 0,
      "goalsFor": 10,
      "goalsAgainst": 8,
      "lastGame": "2025-10-05"
    }
  ]
}
```

## Player Profile Endpoints

### 4. GET `/api/player/{playerId}/profile`
**Purpose:** Retrieve player overview and season stats

**Parameters:**
- `playerId` (path): NHL player ID (e.g., 8480018)
- `season` (query, optional): Season (default current season)

**Response:**
```json
{
  "playerId": "8480018",
  "name": "Cole Caufield",
  "firstName": "Cole",
  "lastName": "Caufield",
  "position": "RW",
  "jerseyNumber": 22,
  "teamId": "MTL",
  "teamName": "Montreal Canadiens",
  "seasonStats": {
    "gamesPlayed": 45,
    "goals": 28,
    "assists": 22,
    "points": 50,
    "plusMinus": 12,
    "pim": 8,
    "shots": 145,
    "shootingPct": 19.3,
    "timeOnIce": "18:24",
    "powerPlayGoals": 12,
    "powerPlayPoints": 18,
    "shortHandedGoals": 0
  },
  "contract": {
    "aav": 7850000,
    "yearsRemaining": 7,
    "status": "Signed"
  }
}
```

### 5. GET `/api/player/{playerId}/game-logs`
**Purpose:** Retrieve detailed game-by-game logs

**Parameters:**
- `playerId` (path): NHL player ID
- `season` (query, optional): Season (default current season)
- `limit` (query, optional): Number of games (default 10)

**Response:**
```json
{
  "gameLogs": [
    {
      "gameId": "2025020100",
      "date": "2025-10-05",
      "opponent": "TOR",
      "homeAway": "home",
      "result": "W",
      "goals": 2,
      "assists": 1,
      "points": 3,
      "plusMinus": 2,
      "pim": 0,
      "shots": 5,
      "hits": 2,
      "blockedShots": 1,
      "timeOnIce": "19:23"
    }
  ]
}
```

### 6. GET `/api/player/{playerId}/game-logs/advanced` (Future Enhancement)
**Purpose:** Retrieve extensive 50+ column game logs from parquet files

**Parameters:**
- `playerId` (path): NHL player ID
- `season` (query, optional): Season
- `metrics` (query, optional): Comma-separated list of metrics to include

**Response:**
```json
{
  "gameLogs": [
    {
      "gameId": "2025020100",
      "date": "2025-10-05",
      "opponent": "TOR",
      "homeAway": "home",
      "result": "W",
      "goals": 2,
      "assists": 1,
      "points": 3,
      "plusMinus": 2,
      "pim": 0,
      "shots": 5,
      "hits": 2,
      "blockedShots": 1,
      "timeOnIce": "19:23",
      "xGoals": 1.85,
      "xAssists": 0.92,
      "shotAttempts": 8,
      "shotQuality": 0.185,
      "zoneEntries": 12,
      "zoneEntriesControlled": 9,
      "zoneExits": 8,
      "zoneExitsControlled": 7,
      "faceoffWins": 3,
      "faceoffLosses": 4,
      "corsiFor": 18,
      "corsiAgainst": 12,
      "fenwickFor": 15,
      "fenwickAgainst": 10,
      "shotAttemptsBlocked": 3,
      "shotAttemptsMissed": 2,
      "highDangerShots": 2,
      "mediumDangerShots": 2,
      "lowDangerShots": 1,
      "rebounds": 3,
      "rushAttempts": 5,
      "takeaways": 2,
      "giveaways": 1,
      "penaltyMinor": 0,
      "penaltyMajor": 0,
      "shiftCount": 22,
      "avgShiftLength": "0:52",
      "evenStrengthTOI": "14:32",
      "ppTOI": "3:45",
      "shTOI": "1:06",
      "gameScore": 2.85
    }
  ]
}
```

## Data Sources

### Current Implementation (Mock Data)
- All endpoints currently return mock data from `frontend/lib/profileApi.ts`
- Mock data generators: `getMockTeamProfile()`, `getMockPlayerProfile()`, `getMockGameLogs()`, etc.

### Future Implementation
1. **Team Data Sources:**
   - NHL API for real-time stats and standings
   - Existing parquet files in `data/processed/analytics/`
   - Team stats from `data/mtl_team_stats/`

2. **Player Data Sources:**
   - NHL API for player profiles and basic stats
   - Play-by-play parquet files for detailed game logs
   - Contract data from existing market API endpoints

3. **Performance Metrics:**
   - Expected goals (xG) from analytics parquet files
   - Zone entry/exit data from play-by-play processing
   - Advanced metrics from HeartBeat engine calculations

## Integration Notes

### Frontend Implementation
- Profile pages use async functions from `profileApi.ts`
- All functions are structured to match future API response format
- Easy swap: Replace mock data with `fetch()` calls when backend endpoints are ready

### Recommended Backend Implementation
1. Create FastAPI routes in `backend/api/routes/profiles.py`
2. Implement Pydantic models in `backend/api/models/profiles.py`
3. Connect to existing data sources (parquet files, NHL API)
4. Add caching layer for performance (Redis or in-memory)

### Example Backend Route (FastAPI)
```python
from fastapi import APIRouter, HTTPException
from backend.api.models.profiles import TeamProfile, PlayerProfile

router = APIRouter(prefix="/api", tags=["profiles"])

@router.get("/team/{team_id}/profile", response_model=TeamProfile)
async def get_team_profile(team_id: str):
    # Load from NHL API or parquet files
    team_data = await load_team_data(team_id)
    if not team_data:
        raise HTTPException(status_code=404, detail="Team not found")
    return team_data

@router.get("/player/{player_id}/profile", response_model=PlayerProfile)
async def get_player_profile(player_id: int):
    # Load from NHL API or parquet files
    player_data = await load_player_data(player_id)
    if not player_data:
        raise HTTPException(status_code=404, detail="Player not found")
    return player_data
```

## Priority Order

### Phase 1 (Immediate)
1. `GET /api/team/{teamId}/profile` - Basic team info
2. `GET /api/player/{playerId}/profile` - Basic player info

### Phase 2 (Near Term)
3. `GET /api/team/{teamId}/performance` - Performance charts
4. `GET /api/player/{playerId}/game-logs` - Basic game logs
5. `GET /api/team/{teamId}/matchups` - Matchup history

### Phase 3 (Future)
6. `GET /api/player/{playerId}/game-logs/advanced` - Full parquet-sourced logs with 50+ metrics

