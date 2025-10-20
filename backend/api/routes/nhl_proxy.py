"""
NHL API Proxy Routes
Proxies NHL API calls to avoid CORS issues in the frontend
"""

from fastapi import APIRouter, HTTPException
import httpx
from typing import Any, Dict
import logging
import json
from pathlib import Path

router = APIRouter(prefix="/api/nhl", tags=["nhl-proxy"])
logger = logging.getLogger(__name__)

NHL_API_BASE = "https://api-web.nhle.com/v1"

# Simple in-process caches with TTL
_PLAYER_LANDING_TTL_SEC = 5 * 60  # 5 minutes
_STANDINGS_TTL_SEC = 60  # 1 minute

_player_landing_cache: dict[str, dict] = {}
_standings_cache: dict[str, any] = {"expires_at": 0, "data": None}

def _now_ts() -> float:
    import time
    return time.time()

async def _get_standings_now(client: httpx.AsyncClient) -> dict:
    now = _now_ts()
    if _standings_cache["data"] is not None and now < _standings_cache["expires_at"]:
        logger.info("Returning cached standings data")
        return _standings_cache["data"]

    # Use today's date for standings (NHL API format: /standings/YYYY-MM-DD)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Fetching standings for date: {today}")
    
    resp = await client.get(f"{NHL_API_BASE}/standings/{today}", follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Successfully fetched standings data")
    _standings_cache["data"] = data
    _standings_cache["expires_at"] = now + _STANDINGS_TTL_SEC
    return data

@router.get("/roster/{team_abbrev}/current")
async def get_team_roster(team_abbrev: str) -> Dict[str, Any]:
    """
    Proxy NHL API roster endpoint to avoid CORS issues
    
    Args:
        team_abbrev: Team abbreviation (MTL, TOR, BOS, etc.)
        
    Returns:
        Team roster data from NHL API
    """
    try:
        logger.info(f"Fetching roster for team: {team_abbrev}")
        
        # Use follow_redirects=True to handle 307 redirects
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(f"{NHL_API_BASE}/roster/{team_abbrev}/current")
            
            if response.status_code != 200:
                logger.warning(f"NHL API returned status {response.status_code} for team {team_abbrev}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"NHL API error: {response.status_code}"
                )
            
            data = response.json()
            logger.info(f"Successfully fetched roster for {team_abbrev}")
            return data
            
    except httpx.RequestError as e:
        logger.error(f"Request error fetching roster for {team_abbrev}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to NHL API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching roster for {team_abbrev}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/player/{player_id}/landing")
async def get_player_landing(player_id: str) -> Dict[str, Any]:
    """
    Proxy NHL API player landing endpoint (core player profile/details).

    Args:
        player_id: NHL player ID

    Returns:
        Player landing data from NHL API
    """
    try:
        logger.info(f"Fetching player landing for player: {player_id}")

        now = _now_ts()
        cached = _player_landing_cache.get(player_id)
        if cached and now < cached.get("expires_at", 0):
            logger.info(f"Returning cached data for player {player_id}")
            return cached["data"]

        # Use follow_redirects=True to handle any redirects
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(f"{NHL_API_BASE}/player/{player_id}/landing")

            if response.status_code != 200:
                logger.warning(
                    f"NHL API returned status {response.status_code} for player {player_id}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"NHL API error: {response.status_code}"
                )

            data = response.json()
            logger.info(f"Successfully fetched player landing for {player_id}")
            _player_landing_cache[player_id] = {
                "data": data,
                "expires_at": now + _PLAYER_LANDING_TTL_SEC,
            }
            return data

    except httpx.RequestError as e:
        logger.error(f"Request error fetching player landing for {player_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to NHL API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching player landing for {player_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/team/{team_abbrev}/summary")
async def get_team_summary(team_abbrev: str) -> Dict[str, Any]:
    """
    Return basic team record/stats using NHL standings.

    Fields include wins, losses, otLosses, points, gamesPlayed, goalsFor,
    goalsAgainst, ppPercent, pkPercent.
    """
    try:
        team_abbrev = team_abbrev.upper()
        async with httpx.AsyncClient(timeout=10.0) as client:
            data = await _get_standings_now(client)

        standings = data.get("standings") or []
        team_row = None
        for row in standings:
            # NHL API format: teamAbbrev is a dict with "default" key
            abbrev = row.get("teamAbbrev", {}).get("default", "")
            if abbrev.upper() == team_abbrev:
                team_row = row
                break

        if not team_row:
            logger.warning(f"Team {team_abbrev} not found in standings payload")
            raise HTTPException(status_code=404, detail="Team not found in standings")

        # Parse standings data (NHL API format)
        wins = team_row.get("wins", 0)
        losses = team_row.get("losses", 0)
        otLosses = team_row.get("otLosses", 0)
        points = team_row.get("points", 0)
        gamesPlayed = team_row.get("gamesPlayed", 0)
        goalsFor = team_row.get("goalFor", 0)  # Note: NHL API uses "goalFor" not "goalsFor"
        goalsAgainst = team_row.get("goalAgainst", 0)  # Note: "goalAgainst" not "goalsAgainst"
        
        # Calculate shots per game if available (may not be in standings endpoint)
        shotsPerGame = 0.0
        shotsAgainstPerGame = 0.0
        
        # PP% and PK% may not be in standings endpoint, will need different endpoint
        ppPercent = 0.0
        pkPercent = 0.0

        return {
            "team": team_abbrev,
            "record": {
                "wins": wins,
                "losses": losses,
                "otLosses": otLosses,
                "points": points,
                "gamesPlayed": gamesPlayed,
            },
            "stats": {
                "goalsFor": goalsFor,
                "goalsAgainst": goalsAgainst,
                "ppPercent": ppPercent,
                "pkPercent": pkPercent,
                "shotsPerGame": shotsPerGame,
                "shotsAgainstPerGame": shotsAgainstPerGame,
            },
            "source": "NHL API standings",
        }
    except httpx.RequestError as e:
        logger.error(f"Request error fetching team summary for {team_abbrev}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to NHL API: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching team summary for {team_abbrev}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/schedule/{date}")
async def get_schedule(date: str) -> Dict[str, Any]:
    """
    Proxy NHL API schedule endpoint
    
    Args:
        date: Date in YYYY-MM-DD format
        
    Returns:
        Schedule data from NHL API
    """
    try:
        logger.info(f"Fetching schedule for date: {date}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{NHL_API_BASE}/score/{date}")
            
            if response.status_code != 200:
                logger.warning(f"NHL API returned status {response.status_code} for date {date}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"NHL API error: {response.status_code}"
                )
            
            data = response.json()
            logger.info(f"Successfully fetched schedule for {date}")
            return data
            
    except httpx.RequestError as e:
        logger.error(f"Request error fetching schedule for {date}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to NHL API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching schedule for {date}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/gamecenter/{game_id}/boxscore")
async def get_game_boxscore(game_id: str) -> Dict[str, Any]:
    """
    Proxy NHL API boxscore endpoint
    
    Args:
        game_id: NHL game ID
        
    Returns:
        Game boxscore data from NHL API
    """
    try:
        logger.info(f"Fetching boxscore for game: {game_id}")
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{NHL_API_BASE}/gamecenter/{game_id}/boxscore")
            
            if response.status_code != 200:
                logger.warning(f"NHL API returned status {response.status_code} for game {game_id}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"NHL API error: {response.status_code}"
                )
            
            data = response.json()
            logger.info(f"Successfully fetched boxscore for {game_id}")
            return data
            
    except httpx.RequestError as e:
        logger.error(f"Request error fetching boxscore for {game_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to NHL API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching boxscore for {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/test")
async def test_nhl_connection() -> Dict[str, Any]:
    """
    Test NHL API connectivity and return sample data
    """
    try:
        logger.info("Testing NHL API connectivity")
        
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            # Test player endpoint
            player_response = await client.get(f"{NHL_API_BASE}/player/8480018/landing")
            player_data = player_response.json() if player_response.status_code == 200 else None
            
            # Test team summary
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            standings_response = await client.get(f"{NHL_API_BASE}/standings/{today}")
            standings_data = standings_response.json() if standings_response.status_code == 200 else None
            
            return {
                "status": "success",
                "message": "NHL API connection successful",
                "player_endpoint": {
                    "url": f"{NHL_API_BASE}/player/8480018/landing",
                    "status": player_response.status_code,
                    "working": player_response.status_code == 200,
                    "sample_name": f"{player_data.get('firstName', {}).get('default', '')} {player_data.get('lastName', {}).get('default', '')}" if player_data else None
                },
                "standings_endpoint": {
                    "url": f"{NHL_API_BASE}/standings/{today}",
                    "status": standings_response.status_code,
                    "working": standings_response.status_code == 200,
                    "teams_count": len(standings_data.get('standings', [])) if standings_data else 0
                }
            }
            
    except Exception as e:
        logger.error(f"NHL API test failed: {e}")
        return {
            "status": "error", 
            "message": f"NHL API connection failed: {str(e)}",
            "test_endpoint": f"{NHL_API_BASE}/player/8480018/landing"
        }

@router.get("/player/{player_id}/cumulative/{season}/{game_type}")
async def get_player_cumulative_stats(player_id: str, season: str, game_type: str) -> Dict[str, Any]:
    """
    Get cumulative season progression data for a player
    
    Parameters:
    - player_id: NHL player ID (e.g., "8480865")
    - season: Season in format YYYYYYY (e.g., "20242025")
    - game_type: "regular" or "playoffs"
    
    Returns game-by-game cumulative stats for charting
    """
    try:
        # Construct path to cumulative data file (resolve repo root robustly)
        # __file__ -> backend/api/routes/nhl_proxy.py; repo root is parents[3]
        repo_root = Path(__file__).resolve().parents[3]
        data_dir = repo_root / "data/processed/player_profiles/aggregated_stats"
        cumulative_file = data_dir / player_id / f"{season}_{game_type}_cumulative.json"
        
        if not cumulative_file.exists():
            logger.warning(f"Cumulative data not found: {cumulative_file}")
            raise HTTPException(
                status_code=404,
                detail=f"No cumulative data found for player {player_id} in {season} {game_type} season"
            )
        
        with open(cumulative_file, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Served cumulative data for player {player_id} - {season} {game_type}: {len(data.get('games', []))} games")
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading cumulative data for {player_id}/{season}_{game_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading player cumulative data: {str(e)}")

@router.get("/player/{player_id}/game-log/{season}/{game_type}")
async def get_player_game_log(player_id: str, season: str, game_type: str) -> Dict[str, Any]:
    """
    Proxy NHL API player game log endpoint
    
    Parameters:
    - player_id: NHL player ID (e.g., "8480018")
    - season: Season in format YYYYYYYY (e.g., "20242025")
    - game_type: Game type ID as string ("2" for regular season, "3" for playoffs)
    
    Returns:
        Game-by-game statistics for the player
    """
    try:
        # Convert game_type string to NHL API format
        game_type_id = "2" if game_type.lower() in ("regular", "2") else "3"
        
        logger.info(f"Fetching game log for player {player_id} - season {season} type {game_type_id}")
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # NHL API endpoint format: /player/{playerId}/game-log/{season}/{gameType}
            url = f"{NHL_API_BASE}/player/{player_id}/game-log/{season}/{game_type_id}"
            logger.info(f"Requesting: {url}")
            
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.warning(f"NHL API returned status {response.status_code} for game log request")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"NHL API error: {response.status_code}"
                )
            
            data = response.json()
            logger.info(f"Successfully fetched game log for player {player_id}: {len(data.get('gameLog', []))} games")
            return data
            
    except httpx.RequestError as e:
        logger.error(f"Request error fetching game log for player {player_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to NHL API: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching game log for player {player_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
