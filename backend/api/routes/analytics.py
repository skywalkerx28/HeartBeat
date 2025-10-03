"""
HeartBeat Engine - Analytics Routes
Montreal Canadiens Advanced Analytics Assistant

Direct analytics endpoints for specific data queries.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import Dict, Any, List


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

