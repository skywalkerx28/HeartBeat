"""
Market Analytics API Routes.

Provides REST endpoints for NHL contract, cap, trade, and market data.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime, timedelta

from backend.api.models.market import (
    PlayerContract,
    TeamCapSummary,
    ContractComparable,
    Trade,
    LeagueMarketOverview,
    ContractAlert,
    MarketAnalyticsResponse,
    ContractEfficiency
)
from orchestrator.tools.market_data_client import MarketDataClient
from orchestrator.tools.market_metrics import ContractMetricsCalculator
from google.cloud import bigquery

router = APIRouter(prefix="/api/v1/market", tags=["market"])


# Dependency for MarketDataClient
async def get_market_client() -> MarketDataClient:
    """Get MarketDataClient instance."""
    import os
    # Use absolute path to ensure it works regardless of working directory
    # __file__ is in backend/api/routes/market.py, so go up 4 levels to project root
    api_routes_dir = os.path.dirname(os.path.abspath(__file__))  # backend/api/routes
    api_dir = os.path.dirname(api_routes_dir)  # backend/api
    backend_dir = os.path.dirname(api_dir)  # backend
    project_root = os.path.dirname(backend_dir)  # HeartBeat
    parquet_path = os.path.join(project_root, "data", "processed", "market")
    
    try:
        bq_client = bigquery.Client(project="heartbeat-474020")
        return MarketDataClient(
            bigquery_client=bq_client,
            parquet_fallback_path=parquet_path
        )
    except Exception:
        # Fallback to Parquet-only mode
        return MarketDataClient(
            bigquery_client=None,
            parquet_fallback_path=parquet_path
        )


@router.get("/contracts/player/{player_id}", response_model=MarketAnalyticsResponse)
async def get_player_contract_details(
    player_id: int,
    season: str = Query("2025-2026", description="Season"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get comprehensive contract details for a player.
    
    Returns contract information, performance metrics, and efficiency analysis.
    """
    try:
        contract_data = await client.get_player_contract(
            nhl_player_id=player_id,
            season=season
        )
        
        if "error" in contract_data:
            raise HTTPException(status_code=404, detail=contract_data["error"])
            
        return MarketAnalyticsResponse(
            success=True,
            data=contract_data,
            source=contract_data.get("source", "unknown")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/contracts/player/name/{player_name}", response_model=MarketAnalyticsResponse)
async def get_player_contract_by_name(
    player_name: str,
    team: Optional[str] = Query(None, description="Team abbreviation for disambiguation"),
    season: str = Query("2025-2026", description="Season"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get contract details by player name.
    
    Supports partial name matching. Use team parameter if multiple matches.
    """
    try:
        contract_data = await client.get_player_contract(
            player_name=player_name,
            team=team,
            season=season
        )
        
        if "error" in contract_data:
            raise HTTPException(status_code=404, detail=contract_data["error"])
            
        return MarketAnalyticsResponse(
            success=True,
            data=contract_data,
            source=contract_data.get("source", "unknown")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/contracts/team/{team_abbrev}", response_model=MarketAnalyticsResponse)
async def get_team_contracts(
    team_abbrev: str,
    season: str = Query("2025-2026", description="Season"),
    include_expired: bool = Query(False, description="Include expired contracts"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get all contracts for a team.
    
    Returns active contracts by default, optionally include expired.
    """
    try:
        cap_summary = await client.get_team_cap_summary(
            team=team_abbrev,
            season=season,
            include_projections=False
        )
        
        if "error" in cap_summary:
            raise HTTPException(status_code=404, detail=cap_summary["error"])
            
        return MarketAnalyticsResponse(
            success=True,
            data={
                "team": team_abbrev,
                "season": season,
                "contracts": cap_summary.get("contracts", [])
            },
            source=cap_summary.get("source", "unknown")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/cap/team/{team_abbrev}", response_model=MarketAnalyticsResponse)
async def get_team_cap_summary(
    team_abbrev: str,
    season: str = Query("2025-2026", description="Season"),
    include_projections: bool = Query(True, description="Include future projections"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get team cap space, commitments, and multi-year projections.
    
    Includes current cap situation and optional future season projections.
    """
    try:
        cap_data = await client.get_team_cap_summary(
            team=team_abbrev,
            season=season,
            include_projections=include_projections
        )
        
        if "error" in cap_data:
            raise HTTPException(status_code=404, detail=cap_data["error"])
            
        return MarketAnalyticsResponse(
            success=True,
            data=cap_data,
            source=cap_data.get("source", "unknown")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/efficiency", response_model=MarketAnalyticsResponse)
async def get_contract_efficiency_rankings(
    position: Optional[str] = Query(None, description="Filter by position (C, RW, LW, D, G)"),
    team: Optional[str] = Query(None, description="Filter by team"),
    min_cap_hit: float = Query(1000000, description="Minimum cap hit filter"),
    limit: int = Query(50, description="Maximum results"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get contract efficiency rankings (performance vs cap hit).
    
    Returns top contracts by efficiency index across the league.
    """
    try:
        # This would need a dedicated query in MarketDataClient
        # For now, return a placeholder structure
        return MarketAnalyticsResponse(
            success=True,
            data={
                "rankings": [],
                "filters": {
                    "position": position,
                    "team": team,
                    "min_cap_hit": min_cap_hit
                },
                "message": "Efficiency rankings coming soon - requires player stats integration"
            },
            source="placeholder"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/comparables/{player_id}", response_model=MarketAnalyticsResponse)
async def get_contract_comparables(
    player_id: int,
    limit: int = Query(10, description="Maximum comparables to return"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Find comparable contracts for market analysis.
    
    Returns similar players by age, position, and production with similarity scores.
    """
    try:
        comparables = await client.get_contract_comparables(
            player_id=player_id,
            position="",  # Will be determined from player data
            limit=limit
        )
        
        return MarketAnalyticsResponse(
            success=True,
            data={
                "player_id": player_id,
                "comparables": comparables,
                "count": len(comparables)
            },
            source="bigquery"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/trades", response_model=MarketAnalyticsResponse)
async def get_recent_trades(
    team: Optional[str] = Query(None, description="Filter by team"),
    days_back: int = Query(30, description="Days to look back"),
    season: str = Query("2025-2026", description="Season filter"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get recent NHL trades with cap implications.
    
    Returns trades within the specified timeframe, optionally filtered by team.
    """
    try:
        trades = await client.get_recent_trades(
            team=team,
            days_back=days_back,
            include_cap_impact=True
        )
        
        return MarketAnalyticsResponse(
            success=True,
            data={
                "trades": trades,
                "count": len(trades),
                "filters": {
                    "team": team,
                    "days_back": days_back
                }
            },
            source="bigquery"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/league/overview", response_model=MarketAnalyticsResponse)
async def get_league_market_overview(
    position: Optional[str] = Query(None, description="Filter by position"),
    season: str = Query("2025-2026", description="Season"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get league-wide market statistics.
    
    Returns average AAV by position, market tiers, and contract distributions.
    """
    try:
        market_data = await client.get_league_market_summary(
            position=position,
            season=season
        )
        
        if "error" in market_data:
            raise HTTPException(status_code=404, detail=market_data["error"])
            
        return MarketAnalyticsResponse(
            success=True,
            data=market_data,
            source=market_data.get("source", "unknown")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/alerts/{team_abbrev}", response_model=MarketAnalyticsResponse)
async def get_contract_alerts(
    team_abbrev: str,
    alert_types: Optional[List[str]] = Query(
        None, 
        description="Filter by alert type: expiring, rfa_eligible, ufa_eligible, arbitration"
    ),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get contract alerts for a team.
    
    Returns upcoming contract decisions: expirations, RFA/UFA eligibility, arbitration cases.
    """
    try:
        # This would query contracts expiring soon and eligibility
        # Placeholder for now
        return MarketAnalyticsResponse(
            success=True,
            data={
                "team": team_abbrev,
                "alerts": [],
                "message": "Contract alerts coming soon - requires contract date calculations"
            },
            source="placeholder"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/efficiency/player/{player_id}", response_model=MarketAnalyticsResponse)
async def get_player_efficiency_analysis(
    player_id: int,
    season: str = Query("2025-2026", description="Season"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Get detailed contract efficiency analysis for a player.
    
    Returns efficiency components, market value estimate, and surplus value.
    """
    try:
        efficiency_data = await client.calculate_contract_efficiency(
            player_id=player_id,
            season=season
        )
        
        if "error" in efficiency_data:
            raise HTTPException(status_code=404, detail=efficiency_data["error"])
            
        return MarketAnalyticsResponse(
            success=True,
            data=efficiency_data,
            source=efficiency_data.get("source", "unknown")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/health")
async def market_api_health():
    """Health check endpoint for market analytics API."""
    return {
        "status": "healthy",
        "service": "market_analytics",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "contracts": "/api/v1/market/contracts/",
            "cap": "/api/v1/market/cap/",
            "trades": "/api/v1/market/trades",
            "league": "/api/v1/market/league/overview",
            "efficiency": "/api/v1/market/efficiency"
        }
    }

