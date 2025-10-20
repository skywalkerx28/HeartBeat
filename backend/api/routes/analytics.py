"""
HeartBeat Engine - Analytics Routes
Montreal Canadiens Advanced Analytics Assistant

Direct analytics endpoints for specific data queries.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import Dict, Any, List
import httpx
from datetime import datetime, timedelta


from orchestrator.utils.state import UserContext
from orchestrator.tools.parquet_data_client_v2 import ParquetDataClientV2 as ParquetDataClient
from ..models.requests import AnalyticsRequest
from ..models.hockey import PlayerStats, GameInfo, MatchupAnalysis
from ..dependencies import get_current_user_context
from orchestrator.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# -----------------------------
# Lightweight in-process caches
# -----------------------------
_ADVANCED_CACHE: dict = {}
_ADVANCED_TTL_SECONDS: int = 600  # 10 minutes for heavy parquet analytics

_STANDINGS_CACHE: dict = {}
_STANDINGS_TTL_SECONDS: int = 120  # 2 minutes for NHL surface data

# Lightweight caches for live schedule/scores
_SCHEDULE_CACHE: dict = {}
_SCHEDULE_TTL_SECONDS: int = 45
_SCORES_CACHE: dict = {}
_SCORES_TTL_SECONDS: int = 15

@router.get("/players")
async def get_players(
    user_context: UserContext = Depends(get_current_user_context)
):
    """Get list of available players"""
    
    try:
        # For now, return Montreal Canadiens roster
        # In production, query from parquet data
        mtl_players = [
            {"id": "nick_suzuki", "name": "Nick Suzuki", "position": "C", "number": 14},
            {"id": "cole_caufield", "name": "Cole Caufield", "position": "RW", "number": 13},
            {"id": "lane_hutson", "name": "Lane Hutson", "position": "D", "number": 48},
            {"id": "mike_matheson", "name": "Mike Matheson", "position": "D", "number": 8},
            {"id": "kaiden_guhle", "name": "Kaiden Guhle", "position": "D", "number": 21},
            {"id": "david_reinbacher", "name": "David Reinbacher", "position": "D", "number": 92},
            {"id": "juraj_slafkovsky", "name": "Juraj Slafkovsky", "position": "LW", "number": 20},
            {"id": "kirby_dach", "name": "Kirby Dach", "position": "C", "number": 77},
            {"id": "alex_newhook", "name": "Alex Newhook", "position": "C", "number": 15}
        ]
        
        return {
            "success": True,
            "players": mtl_players,
            "team": "MTL",
            "season": "2024-25"
        }
        
    except Exception as e:
        logger.error(f"Error fetching players: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch player data"
        )

@router.get("/teams")
async def get_teams(
    user_context: UserContext = Depends(get_current_user_context)
):
    """Get available teams based on user permissions"""
    
    try:
        # Return teams based on user access
        available_teams = [
            {"id": "MTL", "name": "Montreal Canadiens", "division": "Atlantic"},
        ]
        
        # Add opponent teams if user has access
        permissions = settings.get_user_permissions(user_context.role)
        if permissions.get("opponent_data", False):
            opponent_teams = [
                {"id": "TOR", "name": "Toronto Maple Leafs", "division": "Atlantic"},
                {"id": "BOS", "name": "Boston Bruins", "division": "Atlantic"},
                {"id": "OTT", "name": "Ottawa Senators", "division": "Atlantic"},
                # Add more as needed
            ]
            available_teams.extend(opponent_teams)
        
        return {
            "success": True,
            "teams": available_teams,
            "user_access": user_context.team_access
        }
        
    except Exception as e:
        logger.error(f"Error fetching teams: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team data"
        )

@router.post("/query")
async def direct_analytics_query(
    request: AnalyticsRequest,
    user_context: UserContext = Depends(get_current_user_context)
):
    """
    Direct analytics query without going through LLM orchestrator.
    For specific metrics and data requests.
    """
    
    try:
        logger.info(f"Direct analytics query: {request.metric_type}")
        
        # For now, return placeholder data
        # In production, this would query parquet files directly
        placeholder_data = {
            "metric_type": request.metric_type,
            "data": {
                "goals": 12,
                "assists": 18, 
                "points": 30,
                "games_played": 25,
                "shooting_percentage": 15.8,
                "plus_minus": 8
            },
            "filters_applied": request.filters,
            "data_source": "parquet://data/processed/analytics/",
            "processing_time_ms": 45
        }
        
        return {
            "success": True,
            "analytics": placeholder_data,
            "user_role": user_context.role.value
        }
        
    except Exception as e:
        logger.error(f"Error in direct analytics query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics query failed"
        )

@router.get("/nhl/scores")
async def get_nhl_scores(
    date: str = None
):
    """
    Get NHL game scores for a specific date.
    If no date provided, uses today's date.
    """
    try:
        # Use provided date or today's date
        target_date = date or datetime.now().strftime("%Y-%m-%d")

        # Validate date format
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        logger.info(f"Fetching NHL scores for date: {target_date}")

        # Cache fast-changing live scores briefly to avoid hammering
        cache_key = f"scores:{target_date}"
        cached = _SCORES_CACHE.get(cache_key)
        if cached and cached["expires_at"] > datetime.utcnow():
            return cached["data"]

        # Fetch from NHL API
        url = f"https://api-web.nhle.com/v1/score/{target_date}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})

            if response.status_code != 200:
                logger.error(f"NHL API returned status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch data from NHL API"
                )

            data = response.json()

            # Validate response structure
            if not isinstance(data, dict) or "games" not in data:
                logger.error(f"Unexpected NHL API response format: {data}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response format from NHL API"
                )

            result = {
                "success": True,
                "games": data.get("games", []),
                "date": target_date,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

            _SCORES_CACHE[cache_key] = {
                "data": result,
                "expires_at": datetime.utcnow() + timedelta(seconds=_SCORES_TTL_SECONDS)
            }
            return result

    except httpx.TimeoutException:
        logger.error("Timeout fetching NHL scores")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to NHL API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching NHL scores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error communicating with NHL API"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching NHL scores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching NHL scores"
        )

@router.get("/nhl/schedule")
async def get_nhl_schedule(
    date: str = None
):
    """
    Get NHL game schedule for a specific date.
    If no date provided, uses today's date.
    """
    try:
        # Use provided date or today's date
        target_date = date or datetime.now().strftime("%Y-%m-%d")

        # Validate date format
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        logger.info(f"Fetching NHL schedule for date: {target_date}")

        cache_key = f"schedule:{target_date}"
        cached = _SCHEDULE_CACHE.get(cache_key)
        if cached and cached["expires_at"] > datetime.utcnow():
            return cached["data"]

        # Use the score endpoint because it consistently returns a 'games' array
        url = f"https://api-web.nhle.com/v1/score/{target_date}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})

            if response.status_code != 200:
                logger.error(f"NHL API returned status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch data from NHL API"
                )

            data = response.json()

            # Validate response structure
            if not isinstance(data, dict):
                logger.error(f"Unexpected NHL API response format: {data}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response format from NHL API"
                )

            # 'score' endpoint returns the day's games under top-level 'games'
            games = data.get("games", []) if isinstance(data.get("games"), list) else []

            result = {
                "success": True,
                "games": games,
                "date": target_date,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

            _SCHEDULE_CACHE[cache_key] = {
                "data": result,
                "expires_at": datetime.utcnow() + timedelta(seconds=_SCHEDULE_TTL_SECONDS)
            }
            return result

    except httpx.TimeoutException:
        logger.error("Timeout fetching NHL schedule")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to NHL API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching NHL schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error communicating with NHL API"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching NHL schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching NHL schedule"
        )

@router.get("/nhl/game/{game_id}/boxscore")
async def get_game_boxscore(game_id: int):
    """
    Get detailed boxscore for a specific NHL game.
    Includes all player statistics, goalie stats, and team totals.
    """
    try:
        logger.info(f"Fetching boxscore for game: {game_id}")

        url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})

            if response.status_code != 200:
                logger.error(f"NHL API returned status {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch boxscore from NHL API"
                )

            data = response.json()

            return {
                "success": True,
                "data": data,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

    except httpx.TimeoutException:
        logger.error("Timeout fetching game boxscore")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to NHL API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching boxscore: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error communicating with NHL API"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching boxscore: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching boxscore"
        )

@router.get("/nhl/game/{game_id}/play-by-play")
async def get_game_play_by_play(game_id: int):
    """
    Get complete play-by-play data for a specific NHL game.
    Includes all events with ice coordinates, shot types, and detailed information.
    """
    try:
        logger.info(f"Fetching play-by-play for game: {game_id}")

        url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})

            if response.status_code != 200:
                logger.error(f"NHL API returned status {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch play-by-play from NHL API"
                )

            data = response.json()

            return {
                "success": True,
                "data": data,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

    except httpx.TimeoutException:
        logger.error("Timeout fetching play-by-play")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to NHL API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching play-by-play: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error communicating with NHL API"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching play-by-play: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching play-by-play"
        )

@router.get("/nhl/game/{game_id}/landing")
async def get_game_landing(game_id: int):
    """
    Get game landing page data with summary information.
    """
    try:
        logger.info(f"Fetching game landing data for: {game_id}")

        url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/landing"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})

            if response.status_code != 200:
                logger.error(f"NHL API returned status {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch game landing from NHL API"
                )

            data = response.json()

            return {
                "success": True,
                "data": data,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

    except httpx.TimeoutException:
        logger.error("Timeout fetching game landing")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to NHL API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching game landing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error communicating with NHL API"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching game landing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching game landing"
        )


@router.get("/nhl/standings")
async def get_nhl_standings(
    date: str = None
):
    """
    Get NHL standings with division and conference breakdowns.
    """
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Fetching NHL standings for date: {target_date}")

        # Simple TTL cache
        cache_key = f"standings:{target_date}"
        cached = _STANDINGS_CACHE.get(cache_key)
        if cached and cached["expires_at"] > datetime.utcnow():
            return cached["data"]

        url = f"https://api-web.nhle.com/v1/standings/{target_date}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})

            if response.status_code != 200:
                logger.error(f"NHL API returned status {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch standings from NHL API"
                )

            data = response.json()

            # Normalize team records to the structure expected by the UI
            raw = data.get("standings", []) if isinstance(data, dict) else []
            normalized = []
            for t in raw if isinstance(raw, list) else []:
                try:
                    # Robust field extraction across possible NHL shapes
                    def g(obj, *keys, default=None):
                        cur = obj
                        for k in keys:
                            if isinstance(cur, dict) and k in cur:
                                cur = cur[k]
                            else:
                                return default
                        return cur

                    team_name = g(t, "teamName", "default") or g(t, "teamName") or g(t, "team", "name", "default") or ""
                    team_abbrev = g(t, "teamAbbrev", "default") or g(t, "teamAbbrev") or g(t, "team", "abbrev") or ""
                    division = g(t, "divisionName") or g(t, "division", "name") or ""

                    wins = g(t, "wins") or g(t, "record", "wins") or 0
                    losses = g(t, "losses") or g(t, "record", "losses") or 0
                    otl = g(t, "otLosses") or g(t, "ot") or g(t, "record", "ot") or 0
                    points = g(t, "points") or g(t, "pts") or 0
                    gp = g(t, "gamesPlayed") or g(t, "gp") or (int(wins) + int(losses) + int(otl))
                    gf = g(t, "goalsFor") or 0
                    ga = g(t, "goalsAgainst") or 0
                    gd = g(t, "goalDifferential") or g(t, "goalDiff")
                    if gd is None:
                        try:
                            gd = int(gf) - int(ga)
                        except Exception:
                            gd = 0

                    normalized.append({
                        "teamName": {"default": str(team_name)},
                        "teamAbbrev": {"default": str(team_abbrev)},
                        "divisionName": str(division),
                        "wins": int(wins or 0),
                        "losses": int(losses or 0),
                        "otLosses": int(otl or 0),
                        "points": int(points or 0),
                        "gamesPlayed": int(gp or 0),
                        "goalDifferential": int(gd or 0),
                    })
                except Exception:
                    continue

            # Sort by points desc, then goal differential desc, then wins
            normalized.sort(key=lambda r: (r.get("points", 0), r.get("goalDifferential", 0), r.get("wins", 0)), reverse=True)

            result = {
                "success": True,
                "standings": normalized,
                "date": target_date,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

            _STANDINGS_CACHE[cache_key] = {
                "data": result,
                "expires_at": datetime.utcnow() + timedelta(seconds=_STANDINGS_TTL_SECONDS)
            }

            return result

    except httpx.TimeoutException:
        logger.error("Timeout fetching NHL standings")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to NHL API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching standings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error communicating with NHL API"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching standings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching standings"
        )


@router.get("/nhl/leaders")
async def get_nhl_leaders(
    category: str = "points",
    limit: int = 10
):
    """
    Get NHL league leaders (points, goals, assists, etc).
    """
    try:
        logger.info(f"Fetching NHL leaders for category: {category}")

        # NHL API endpoint for current season stats leaders
        url = "https://api-web.nhle.com/v1/skater-stats-leaders/current"

        # Lightweight cache
        cache_key = f"leaders:{category}:{limit}"
        cached = _STANDINGS_CACHE.get(cache_key)  # reuse same simple cache dict
        if cached and cached["expires_at"] > datetime.utcnow():
            return cached["data"]

        # NHL sometimes issues 3xx (e.g., 307) redirects for these leaders endpoints.
        # Enable redirect following explicitly.
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"Accept": "application/json"})

            if response.status_code != 200:
                logger.error(f"NHL API returned status {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch leaders from NHL API"
                )

            data = response.json()

            # Extract relevant category with robust fallbacks
            category_map = {
                "points": ["points", "pointsAll"],
                "goals": ["goals"],
                "assists": ["assists"],
            }

            candidates = category_map.get(category, ["points"])  # default to points
            leaders_list = []
            for key in candidates:
                try:
                    val = data.get(key)
                    if isinstance(val, list):
                        leaders_list = val
                        break
                    if isinstance(val, dict):
                        # Some variants nest under 'leaders' or 'skaters'
                        if isinstance(val.get("leaders"), list):
                            leaders_list = val.get("leaders")
                            break
                        if isinstance(val.get("skaters"), list):
                            leaders_list = val.get("skaters")
                            break
                except Exception:
                    continue

            leaders = leaders_list[:limit] if isinstance(leaders_list, list) else []

            result = {
                "success": True,
                "category": category,
                "leaders": leaders,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

            _STANDINGS_CACHE[cache_key] = {
                "data": result,
                "expires_at": datetime.utcnow() + timedelta(seconds=_STANDINGS_TTL_SECONDS)
            }

            return result

    except httpx.TimeoutException:
        logger.error("Timeout fetching NHL leaders")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to NHL API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching leaders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error communicating with NHL API"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching leaders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching leaders"
        )


@router.get("/mtl/advanced")
async def get_mtl_advanced_analytics(
    window: int = 10,
    season: str = "2024-2025"
):
    """
    Get comprehensive advanced analytics for Montreal Canadiens.
    
    Returns:
    - Player Form Index (PFI) top performers
    - Team Trends (xGF%, special teams, pace, PDO)
    - Rival Threat Index (Atlantic Division)
    - Fan Sentiment Proxy (FSP)
    """
    try:
        logger.info(f"Computing MTL advanced analytics for season {season}, window {window}")

        # TTL cache
        cache_key = f"mtl_adv:{season}:{window}"
        cached = _ADVANCED_CACHE.get(cache_key)
        if cached and cached["expires_at"] > datetime.utcnow():
            data = cached["data"]
            # Validate cached payload to guard against earlier NaN→null entries
            def _valid_adv(d: Dict[str, Any]) -> bool:
                try:
                    rti = d.get("rival_threat_index", []) or []
                    for item in rti:
                        v = item.get("rti_score", None)
                        if v is None:
                            return False
                        # ensure numeric
                        float(v)
                    return True
                except Exception:
                    return False
            if _valid_adv(data):
                return data
            else:
                # Evict stale/invalid cache and recompute
                _ADVANCED_CACHE.pop(cache_key, None)

        # Initialize data client using configured data directory
        data_client = ParquetDataClient(settings.parquet.data_directory)
        
        # Import advanced metrics module
        from orchestrator.tools.advanced_metrics import (
            compute_player_form_index,
            compute_team_trends,
            compute_rival_threat_index,
            compute_fan_sentiment_proxy
        )
        
        # Load data
        player_logs = await data_client.get_mtl_player_game_logs(season=season, window=window)
        team_logs = await data_client.get_mtl_team_game_logs(season=season, window=window)
        division_data = await data_client.get_division_teams_data(division="Atlantic", season=season, window=window)
        
        # Compute metrics
        player_form = compute_player_form_index(player_logs, window=window)
        team_trends = compute_team_trends(team_logs, window=window)
        rival_index = compute_rival_threat_index(division_data, division="Atlantic", window=window)
        fan_sentiment = compute_fan_sentiment_proxy(team_trends, player_form)
        
        result = {
            "success": True,
            "season": season,
            "window_games": window,
            "player_form": player_form[:10],
            "team_trends": team_trends,
            "rival_threat_index": rival_index,
            "fan_sentiment_proxy": fan_sentiment,
            "fetched_at": datetime.now().isoformat(),
            "source": "HeartBeat Engine - Advanced Analytics"
        }

        def _clean_nans(obj):
            from math import isnan, isinf
            if isinstance(obj, dict):
                return {k: _clean_nans(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_clean_nans(v) for v in obj]
            if isinstance(obj, float):
                try:
                    if isnan(obj) or isinf(obj):
                        return None
                except Exception:
                    return obj
            return obj

        result = _clean_nans(result)

        # Final validation (post-sanitize). We expect all rti_score values to be numeric now.

        _ADVANCED_CACHE[cache_key] = {
            "data": result,
            "expires_at": datetime.utcnow() + timedelta(seconds=_ADVANCED_TTL_SECONDS)
        }

        return result
        
    except Exception as e:
        logger.error(f"Error computing MTL advanced analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute advanced analytics: {str(e)}"
        )
