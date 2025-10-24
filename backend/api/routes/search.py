from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path

router = APIRouter()

TEAM_MAPPING = {
    "ANA": "Anaheim Ducks",
    "BOS": "Boston Bruins",
    "BUF": "Buffalo Sabres",
    "CAR": "Carolina Hurricanes",
    "CBJ": "Columbus Blue Jackets",
    "CGY": "Calgary Flames",
    "CHI": "Chicago Blackhawks",
    "COL": "Colorado Avalanche",
    "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings",
    "EDM": "Edmonton Oilers",
    "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings",
    "MIN": "Minnesota Wild",
    "MTL": "Montreal Canadiens",
    "NJD": "New Jersey Devils",
    "NSH": "Nashville Predators",
    "NYI": "New York Islanders",
    "NYR": "New York Rangers",
    "OTT": "Ottawa Senators",
    "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins",
    "SEA": "Seattle Kraken",
    "SJS": "San Jose Sharks",
    "STL": "St. Louis Blues",
    "TBL": "Tampa Bay Lightning",
    "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Hockey Club",
    "VAN": "Vancouver Canucks",
    "VGK": "Vegas Golden Knights",
    "WPG": "Winnipeg Jets",
    "WSH": "Washington Capitals"
}


_roster_cache: Dict[str, Any] = {}
_cache_timestamp: float = 0
CACHE_TTL = 3600


def _load_roster_from_gcs() -> Dict[str, Any]:
    """
    Try loading unified roster JSON from GCS lake when running in Cloud.
    Bucket/path are determined by env:
      - GCS_LAKE_BUCKET (required)
      - ROSTER_UNIFIED_PATH (optional override)
    Defaults tried in order:
      silver/analytics/rosters/unified_roster_historical.json
      analytics/rosters/unified_roster_historical.json
      rosters/unified_roster_historical.json
    """
    try:
        bucket = os.getenv("GCS_LAKE_BUCKET")
        if not bucket:
            return {}
        path_override = os.getenv("ROSTER_UNIFIED_PATH")
        candidates = [
            path_override,
            "silver/analytics/rosters/unified_roster_historical.json",
            "analytics/rosters/unified_roster_historical.json",
            "rosters/unified_roster_historical.json",
        ]
        candidates = [p for p in candidates if p]
        from google.cloud import storage  # lazy import to avoid local dependency if unused
        client = storage.Client()
        b = client.bucket(bucket)
        for key in candidates:
            blob = b.blob(key)
            if blob.exists():
                raw = blob.download_as_bytes()
                data = json.loads(raw.decode("utf-8"))
                return {
                    "players": data.get("players", []),
                    "teams": data.get("teams", []),
                }
        return {}
    except Exception as e:
        print(f"GCS roster load failed: {e}")
        return {}


def load_roster_data() -> Dict[str, Any]:
    """
    Load all roster data from the unified historical roster file.
    Uses caching to avoid repeated file reads.
    """
    global _roster_cache, _cache_timestamp
    
    # Prefer GCS when configured (Cloud Run)
    gcs_loaded = _load_roster_from_gcs()
    if gcs_loaded:
        _roster_cache = gcs_loaded
        _cache_timestamp = _cache_timestamp or 1  # non-zero to keep cache
        return _roster_cache

    # Fallback: local file (developer environment)
    project_root = Path(__file__).parent.parent.parent.parent
    unified_file = project_root / "data" / "processed" / "rosters" / "unified_roster_historical.json"
    
    if not unified_file.exists():
        print(f"Unified roster file not found at {unified_file}")
        print("Historical roster data is required for search functionality.")
        return {"players": [], "teams": []}
    
    try:
        current_time = os.path.getmtime(unified_file)
        
        if _roster_cache and _cache_timestamp == current_time:
            return _roster_cache
        
        with open(unified_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        _roster_cache = {
            "players": data.get("players", []),
            "teams": data.get("teams", [])
        }
        _cache_timestamp = current_time
        
        print(f"Loaded {len(_roster_cache['players'])} players and {len(_roster_cache['teams'])} teams from unified roster")
        return _roster_cache
        
    except Exception as e:
        print(f"Error loading unified roster: {e}")
        import traceback
        traceback.print_exc()
        return {"players": [], "teams": []}


@router.get("/search")
async def search_league(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return")
) -> Dict[str, Any]:
    """
    Search for players and teams across the league.
    Returns matching players and teams based on the query.
    """
    query = q.lower().strip()
    
    data = load_roster_data()
    results = []
    
    for player in data["players"]:
        player_name_lower = player["name"].lower()
        # Handle both historical (currentTeamName/currentTeam) and current (teamName/team) roster formats
        team_name = player.get("currentTeamName") or player.get("teamName", "")
        team_code = player.get("currentTeam") or player.get("team", "")
        team_name_lower = team_name.lower()
        
        if (query in player_name_lower or 
            query in player["firstName"].lower() or 
            query in player["lastName"].lower() or
            query in team_name_lower or
            query in team_code.lower()):
            
            # Normalize player data to consistent format for frontend
            normalized_player = {
                **player,
                "teamName": team_name,  # Ensure teamName exists
                "team": team_code,       # Ensure team exists
                "relevance": calculate_relevance(query, player)
            }
            results.append(normalized_player)
    
    for team in data["teams"]:
        team_name_lower = team["name"].lower()
        team_code_lower = team["code"].lower()
        
        if query in team_name_lower or query in team_code_lower:
            results.append({
                **team,
                "relevance": calculate_relevance(query, team)
            })
    
    results.sort(key=lambda x: x["relevance"], reverse=True)
    
    return {
        "query": q,
        "results": results[:limit],
        "total": len(results)
    }


def calculate_relevance(query: str, item: Dict[str, Any]) -> float:
    """
    Calculate relevance score for search results.
    Higher score = better match.
    """
    query_lower = query.lower()
    name = item["name"].lower()
    
    # Base relevance score
    base_score = 50.0
    
    # Exact full name match (highest priority)
    if name == query_lower:
        base_score = 100.0
    # Full name starts with query
    elif name.startswith(query_lower):
        base_score = 95.0
    # Query is complete word in name
    elif query_lower in name.split():
        base_score = 90.0
    # Partial match in full name
    elif query_lower in name:
        base_score = 70.0
    
    # Check first/last name matches for players
    if item["type"] == "player":
        first_name = item.get("firstName", "").lower()
        last_name = item.get("lastName", "").lower()
        
        # Exact first or last name match
        if first_name == query_lower or last_name == query_lower:
            base_score = max(base_score, 98.0)
        # First or last name starts with query
        elif first_name.startswith(query_lower):
            base_score = max(base_score, 92.0)
        elif last_name.startswith(query_lower):
            base_score = max(base_score, 93.0)  # Slightly prefer last name
        # Partial match in first or last name
        elif query_lower in first_name:
            base_score = max(base_score, 75.0)
        elif query_lower in last_name:
            base_score = max(base_score, 76.0)
    
    # Boost score based on player prominence/activity
    # Use player ID as a rough proxy (lower ID = longer career/more established)
    if item["type"] == "player":
        player_id = item.get("id", 9999999)
        # Normalize: IDs typically range from 8465000-8490000+
        # Lower IDs (established players) get a small boost
        if player_id < 8475000:
            base_score += 3.0  # Veterans
        elif player_id < 8480000:
            base_score += 2.0  # Mid-career
        elif player_id < 8485000:
            base_score += 1.0  # Recent players
        # New players (8485000+) get no boost
    
    return base_score


@router.post("/search/refresh")
async def refresh_search_cache() -> Dict[str, Any]:
    """
    Manually refresh the search roster cache.
    Useful after roster updates or trades.
    """
    global _roster_cache, _cache_timestamp
    
    _roster_cache = {}
    _cache_timestamp = 0
    
    data = load_roster_data()
    
    return {
        "status": "success",
        "message": "Search cache refreshed",
        "players_loaded": len(data.get("players", [])),
        "teams_loaded": len(data.get("teams", []))
    }


@router.get("/search/stats")
async def get_search_stats() -> Dict[str, Any]:
    """Get statistics about the search index."""
    data = load_roster_data()
    
    position_counts = {}
    for player in data.get("players", []):
        pos = player.get("position", "Unknown")
        position_counts[pos] = position_counts.get(pos, 0) + 1
    
    team_counts = {}
    for player in data.get("players", []):
        team = player.get("team", "Unknown")
        team_counts[team] = team_counts.get(team, 0) + 1
    
    return {
        "total_players": len(data.get("players", [])),
        "total_teams": len(data.get("teams", [])),
        "players_by_position": position_counts,
        "players_by_team": team_counts,
        "cache_active": bool(_roster_cache)
    }

