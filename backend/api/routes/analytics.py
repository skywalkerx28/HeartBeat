"""
HeartBeat Engine - Analytics Routes
Montreal Canadiens Advanced Analytics Assistant

Direct analytics endpoints for specific data queries.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import Dict, Any, List
import httpx
from datetime import datetime


from orchestrator.utils.state import UserContext
from orchestrator.tools.parquet_data_client import ParquetDataClient
from ..models.requests import AnalyticsRequest
from ..models.hockey import PlayerStats, GameInfo, MatchupAnalysis
from ..dependencies import get_current_user_context
from orchestrator.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

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

            return {
                "success": True,
                "games": data.get("games", []),
                "date": target_date,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

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

        # Fetch from NHL API
        url = f"https://api-web.nhle.com/v1/schedule/{target_date}"

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

            # Extract games from gameWeek structure
            games = []
            if "gameWeek" in data and isinstance(data["gameWeek"], list) and len(data["gameWeek"]) > 0:
                games = data["gameWeek"][0].get("games", [])

            return {
                "success": True,
                "games": games,
                "date": target_date,
                "fetched_at": datetime.now().isoformat(),
                "source": "NHL API"
            }

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

