"""
Market Analytics API Routes.

Provides REST endpoints for NHL contract, cap, trade, and market data.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import hashlib
import json
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
from pathlib import Path
import os

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
    
    # Allow forcing Parquet-only mode via env (dev-friendly)
    if os.environ.get("MARKET_DISABLE_BIGQUERY", "").lower() == "true":
        return MarketDataClient(
            bigquery_client=None,
            parquet_fallback_path=parquet_path
        )
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


def _season_to_formats(season: str) -> tuple[str, str]:
    """Return both dashed (YYYY-YYYY) and compact (YYYYYYYY) formats."""
    s = season.strip()
    if "-" in s and len(s) >= 9:
        start, end = s.split("-")
        dashed = f"{start}-{end}"
        compact = f"{start}{end}"
        return dashed, compact
    if len(s) == 8 and s.isdigit():
        dashed = f"{s[:4]}-{s[4:]}"
        return dashed, s
    # Fallback: try to coerce to current format
    return s, s


@router.get("/salary/progression/{player_id}")
async def get_player_salary_progression(
    player_id: int,
    season: str = Query("2025-2026", description="Season, YYYY-YYYY or YYYYYYYY"),
    client: MarketDataClient = Depends(get_market_client)
):
    """
    Return cumulative salary progression for the given player and season.

    Constructs a per-game cumulative series using the player's annual salary
    (prefers season-specific salary columns if available, else cap_hit/AAV)
    and the player's aggregated games file to align dates and game indices.
    """
    try:
        dashed, compact = _season_to_formats(season)

        # Resolve repo root and aggregated stats path
        repo_root = Path(__file__).resolve().parents[3]
        agg_dir = repo_root / "data/processed/player_profiles/aggregated_stats" / str(player_id)
        agg_file = agg_dir / f"{compact}_regular_cumulative.json"

        games: list[dict] = []
        if agg_file.exists():
            import json as _json
            with open(agg_file, "r") as f:
                agg_data = _json.load(f)
            games = agg_data.get("games", [])

        # Fetch contract data (prefer parquet fallback if BigQuery not configured)
        contract = await client.get_player_contract(nhl_player_id=player_id, season=dashed)
        if "error" in contract:
            raise HTTPException(status_code=404, detail=contract["error"])

        # Determine annual salary for this season
        annual_salary = 0.0
        # Season-specific columns may exist like salary_2025_2026 or cap_hit_2025_26
        season_col_variants = [
            f"salary_{dashed.replace('-', '_')}",
            f"salary_{compact[:4]}_{compact[6:]}",
            f"cap_hit_{dashed.replace('-', '_')}",
            f"cap_hit_{compact[:4]}_{compact[6:]}",
        ]
        for col in season_col_variants:
            if col in contract and contract[col] is not None:
                try:
                    annual_salary = float(contract[col])
                    break
                except Exception:
                    pass
        if not annual_salary:
            for key in ("salary", "base_salary", "cap_hit", "aav"):
                if key in contract and contract[key] is not None:
                    try:
                        annual_salary = float(contract[key])
                        break
                    except Exception:
                        pass
        if not annual_salary:
            raise HTTPException(status_code=404, detail="No salary or cap data available for player/season")

        total_games = max(len(games), 82) if len(games) == 0 else len(games)
        per_game = annual_salary / 82.0  # normalize per 82 for consistency

        # Build progression series aligned to player's cumulative games if available
        series = []
        for i in range(total_games):
            # Use actual game metadata if present
            if i < len(games):
                g = games[i]
                game_date = g.get("gameDate")
                gp = g.get("gamesPlayed", i + 1)
            else:
                game_date = None
                gp = i + 1
            series.append({
                "gamesPlayed": gp,
                "gameDate": game_date,
                "salaryPerGame": per_game,
                "salaryAccrued": per_game * gp,
            })

        return {
            "playerId": str(player_id),
            "season": compact,
            "unit": "USD",
            "annualSalary": annual_salary,
            "perGame": per_game,
            "games": series,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing salary progression: {str(e)}")


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
    client: MarketDataClient = Depends(get_market_client),
    request: Request = None,
):
    """
    Get all contracts for a team based on their roster.
    
    Integrates roster JSON files with contract CSV data.
    Returns active contracts by default, optionally include expired.
    """
    try:
        # Get project root
        repo_root = Path(__file__).resolve().parents[3]
        
        # Convert season format (2025-2026 -> 20252026)
        season_compact = season.replace('-', '')
        
        # Load team roster JSON
        roster_file = repo_root / "data" / "processed" / "rosters" / team_abbrev / season_compact / f"{team_abbrev}_roster_{season_compact}.json"
        
        if not roster_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Roster file not found for {team_abbrev} season {season}"
            )
        
        import json as _json
        with open(roster_file, 'r') as f:
            roster_data = _json.load(f)
        
        # Collect all player IDs from roster
        all_players = []
        for category in ['forwards', 'defensemen', 'goalies']:
            if category in roster_data:
                all_players.extend(roster_data[category])
        
        # For each player, get their contract data from CSV
        contracts_list = []
        contracts_dir = repo_root / "data" / "contracts"
        
        for player in all_players:
            player_id = player.get('id')
            if not player_id:
                continue
            
            # Find contract CSV for this player
            import glob
            pattern = str(contracts_dir / f"*_{player_id}_summary_*.csv")
            matching_files = glob.glob(pattern)
            
            if not matching_files:
                # No contract data, skip
                continue
            
            contract_file = Path(sorted(matching_files)[-1])
            
            # Parse contract CSV
            import csv
            import re
            
            contract_info = {
                "nhl_player_id": player_id,
                "player_name": f"{player.get('firstName', {}).get('default', '')} {player.get('lastName', {}).get('default', '')}".strip(),
                "full_name": f"{player.get('firstName', {}).get('default', '')} {player.get('lastName', {}).get('default', '')}".strip(),
                "position": player.get('positionCode', 'N/A'),
                "roster_status": "NHL",  # From roster, assume NHL
            }
            
            with open(contract_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                lines = list(reader)
                
                # Parse metadata
                for i, row in enumerate(lines):
                    if not row:
                        continue
                    if row[0] == "Position" and len(row) > 1:
                        contract_info["position"] = row[1]
                    elif row[0] == "CONTRACT DETAILS - YEAR BY YEAR":
                        # Found details section, get current season data
                        for j in range(i + 2, len(lines)):  # Skip header
                            detail_row = lines[j]
                            if not detail_row or not detail_row[0].strip():
                                break
                            
                            season_str = detail_row[0] if len(detail_row) > 0 else ""
                            # Check if this is current season (e.g., "2025-26")
                            if season_str.startswith(season[:4]):
                                def parse_currency(val):
                                    if not val or val == '-':
                                        return 0.0
                                    cleaned = re.sub(r'[^\d.]', '', str(val))
                                    try:
                                        return float(cleaned)
                                    except:
                                        return 0.0
                                
                                def parse_percentage(val):
                                    if not val or val == '-':
                                        return 0.0
                                    cleaned = val.replace('%', '').strip()
                                    try:
                                        return float(cleaned)
                                    except:
                                        return 0.0
                                
                                contract_info["clause"] = detail_row[1] if len(detail_row) > 1 else ""
                                contract_info["cap_hit"] = parse_currency(detail_row[2] if len(detail_row) > 2 else "")
                                contract_info["cap_hit_percentage"] = parse_percentage(detail_row[3] if len(detail_row) > 3 else "")
                                contract_info["aav"] = parse_currency(detail_row[4] if len(detail_row) > 4 else "")
                                contract_info["base_salary"] = parse_currency(detail_row[7] if len(detail_row) > 7 else "")
                                contract_info["signing_bonus"] = parse_currency(detail_row[6] if len(detail_row) > 6 else "")
                                contract_info["no_trade_clause"] = "NTC" in contract_info.get("clause", "")
                                contract_info["no_movement_clause"] = "NMC" in contract_info.get("clause", "")
                                break
                        break
            
            # Calculate years remaining (count seasons from current onwards)
            current_season_start = int(season[:4])
            years_remaining = 0
            with open(contract_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                lines = list(reader)
                in_details = False
                for row in lines:
                    if not row:
                        continue
                    if row[0] == "CONTRACT DETAILS - YEAR BY YEAR":
                        in_details = True
                        continue
                    if in_details and row[0] and "-" in row[0]:
                        try:
                            year = int(row[0].split("-")[0])
                            if year >= current_season_start:
                                years_remaining += 1
                        except:
                            pass
            
            contract_info["years_remaining"] = years_remaining
            
            # Calculate age
            from datetime import datetime
            birth_date = player.get('birthDate')
            if birth_date:
                try:
                    birth = datetime.strptime(birth_date, '%Y-%m-%d')
                    today = datetime.now()
                    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
                    contract_info["age"] = age
                except:
                    contract_info["age"] = 0
            else:
                contract_info["age"] = 0
            
            contract_info["contract_type"] = "Standard Contract"
            contract_info["contract_status"] = "Active" if years_remaining > 0 else "Expired"
            
            contracts_list.append(contract_info)
            
        payload = MarketAnalyticsResponse(
            success=True,
            data={
                "team": team_abbrev,
                "season": season,
                "contracts": contracts_list
            },
            source="roster_json_with_contract_csv"
        ).dict()

        return _respond_with_cache(payload, request)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/cap/team/{team_abbrev}", response_model=MarketAnalyticsResponse)
async def get_team_cap_summary(
    team_abbrev: str,
    season: str = Query("2025-2026", description="Season"),
    include_projections: bool = Query(True, description="Include future projections"),
    client: MarketDataClient = Depends(get_market_client),
    request: Request = None,
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
            
        payload = MarketAnalyticsResponse(
            success=True,
            data=cap_data,
            source=cap_data.get("source", "unknown")
        ).dict()
        return _respond_with_cache(payload, request)
        
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
import math


def _sanitize_json_numbers(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, list):
        return [_sanitize_json_numbers(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_json_numbers(v) for k, v in value.items()}
    return value


def _respond_with_cache(payload: dict, request: Request, max_age: int = 120, swr: int = 600):
    """Return a JSONResponse with Cache-Control and ETag/304 support."""
    encoded = _sanitize_json_numbers(jsonable_encoder(payload))
    etag_source = encoded
    if isinstance(etag_source, dict) and 'timestamp' in etag_source:
        etag_source = {**etag_source}
        etag_source.pop('timestamp', None)
    body = json.dumps(etag_source, sort_keys=True)
    etag = hashlib.md5(body.encode("utf-8")).hexdigest()
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match == etag:
        return Response(status_code=304, headers={
            "ETag": etag,
            "Cache-Control": f"public, max-age={max_age}, stale-while-revalidate={swr}",
        })
    return JSONResponse(content=encoded, headers={
        "ETag": etag,
        "Cache-Control": f"public, max-age={max_age}, stale-while-revalidate={swr}",
    })


@router.get("/contracts/csv/{player_id}", response_model=MarketAnalyticsResponse)
async def get_player_contract_from_csv(
    player_id: int,
):
    """
    Get player contract data from CSV summary files.
    
    Returns comprehensive contract history including:
    - Player metadata (name, team, position)
    - All contracts (type, signing date, length, value, cap hit)
    - Year-by-year contract details (cap hit, bonuses, salaries)
    """
    try:
        # Get project root
        repo_root = Path(__file__).resolve().parents[3]
        contracts_dir = repo_root / "data" / "contracts"
        
        # Find contract file for this player ID
        # Format: {lastname}_{playerid}_summary_{timestamp}.csv
        import glob
        pattern = str(contracts_dir / f"*_{player_id}_summary_*.csv")
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            raise HTTPException(
                status_code=404, 
                detail=f"No contract data found for player ID {player_id}"
            )
        
        # If multiple files exist (shouldn't happen after cleanup), use the most recent
        contract_file = Path(sorted(matching_files)[-1])
        
        # Parse the CSV file
        import csv
        import re
        contract_data = {
            "nhl_player_id": player_id,
            "player_name": "",
            "full_name": "",
            "team_abbrev": "",
            "position": "",
            "contracts_list": [],  # Raw contracts from CSV
            "contract_details_list": [],  # Raw details from CSV
        }
        
        with open(contract_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            lines = list(reader)
            
            # Parse player metadata (first section)
            for i, row in enumerate(lines):
                if not row:
                    continue
                if row[0] == "Player Name" and len(row) > 1:
                    contract_data["player_name"] = row[1]
                elif row[0] == "Official Name" and len(row) > 1:
                    contract_data["full_name"] = row[1]
                elif row[0] == "Current Team" and len(row) > 1:
                    contract_data["team_abbrev"] = row[1]
                elif row[0] == "Position" and len(row) > 1:
                    contract_data["position"] = row[1]
                elif row[0] == "CONTRACTS":
                    # Found contracts section
                    contracts_start = i + 2  # Skip header row
                    break
            
            # Parse contracts section
            in_contracts = False
            in_details = False
            
            for i, row in enumerate(lines):
                if not row or not row[0].strip():
                    continue
                    
                # Detect sections
                if row[0] == "CONTRACTS":
                    in_contracts = True
                    in_details = False
                    continue
                elif row[0] == "CONTRACT DETAILS - YEAR BY YEAR":
                    in_contracts = False
                    in_details = True
                    continue
                    
                # Skip header rows
                if row[0] in ["Type", "Season", "Clause"]:
                    continue
                    
                # Parse contracts
                if in_contracts and len(row) >= 3:
                    contract_data["contracts_list"].append({
                        "type": row[0] if len(row) > 0 else "",
                        "team": row[1] if len(row) > 1 else "",
                        "signing_date": row[2] if len(row) > 2 else "",
                        "length_years": row[3] if len(row) > 3 else "",
                        "total_value": row[4] if len(row) > 4 else "",
                        "cap_hit": row[5] if len(row) > 5 else "",
                        "expiry_status": row[6] if len(row) > 6 else "",
                    })
                    
                # Parse contract details
                elif in_details and len(row) >= 3:
                    contract_data["contract_details_list"].append({
                        "season": row[0] if len(row) > 0 else "",
                        "clause": row[1] if len(row) > 1 else "",
                        "cap_hit": row[2] if len(row) > 2 else "",
                        "cap_percentage": row[3] if len(row) > 3 else "",
                        "aav": row[4] if len(row) > 4 else "",
                        "performance_bonuses": row[5] if len(row) > 5 else "",
                        "signing_bonuses": row[6] if len(row) > 6 else "",
                        "base_salary": row[7] if len(row) > 7 else "",
                        "total_salary": row[8] if len(row) > 8 else "",
                        "minors_salary": row[9] if len(row) > 9 else "",
                    })
        
        # Transform to PlayerContract format for frontend compatibility
        def parse_currency(value: str) -> float:
            """Parse currency string like '$13,250,000' to float"""
            if not value or value == '-':
                return 0.0
            # Remove $, commas, and any other non-numeric chars except decimal point
            cleaned = re.sub(r'[^\d.]', '', str(value))
            try:
                return float(cleaned)
            except:
                return 0.0
        
        def parse_percentage(value: str) -> float:
            """Parse percentage string like '14.5%' to float"""
            if not value or value == '-':
                return 0.0
            cleaned = value.replace('%', '').strip()
            try:
                return float(cleaned)
            except:
                return 0.0
        
        # Get the most recent contract (first in list)
        latest_contract = contract_data["contracts_list"][0] if contract_data["contracts_list"] else {}
        latest_details = contract_data["contract_details_list"][0] if contract_data["contract_details_list"] else {}
        
        # Calculate years remaining (count current + future seasons)
        # We're in 2025-26 season, so count all seasons from 2025-26 onwards
        current_season_start = 2025
        
        # Count all seasons >= current season
        remaining_seasons = []
        for detail in contract_data["contract_details_list"]:
            season_str = detail.get("season", "")
            if season_str and "-" in season_str:
                # Parse season like "2025-26" to get year 2025
                try:
                    year = int(season_str.split("-")[0])
                    if year >= current_season_start:
                        remaining_seasons.append(detail)
                except:
                    pass
        
        years_remaining = len(remaining_seasons)
        
        # Build transformed response matching PlayerContract interface
        transformed_data = {
            "nhl_player_id": player_id,
            "player_name": contract_data["player_name"],
            "full_name": contract_data["full_name"],
            "team_abbrev": contract_data["team_abbrev"],
            "position": contract_data["position"],
            "age": 0,  # Not available in CSV
            "cap_hit": parse_currency(latest_details.get("aav", "") or latest_details.get("cap_hit", "")),
            "cap_hit_percentage": parse_percentage(latest_details.get("cap_percentage", "")),
            "years_remaining": years_remaining,
            "contract_type": latest_contract.get("type", "Standard Contract"),
            "no_trade_clause": "NTC" in latest_details.get("clause", ""),
            "no_movement_clause": "NMC" in latest_details.get("clause", ""),
            "contract_status": "Active" if years_remaining > 0 else "Expired",
            "roster_status": "NHL",  # Default assumption
            # Include raw data for advanced displays
            "contracts": contract_data["contracts_list"],
            "contract_details": contract_data["contract_details_list"],
        }
        
        return MarketAnalyticsResponse(
            success=True,
            data=transformed_data,
            source="capwages_csv"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error reading contract file: {str(e)}")


@router.get("/depth-chart/{team_code}")
async def get_team_depth_chart(
    team_code: str,
    roster_status: Optional[str] = Query(None, description="Filter by roster status: roster, non_roster, unsigned"),
    include_contracts: bool = Query(True, description="Include contract data merged with roster")
):
    """
    Get team depth chart roster data from the depth chart database.
    
    Optionally merges with contract data from player_contracts table.
    """
    try:
        from backend.bot import db
        
        team_code = team_code.upper()
        
        # Get roster data from depth chart database
        with db.get_connection(read_only=True) as conn:
            roster = db.get_team_roster(conn, team_code, latest_only=True)
            
            if not roster:
                raise HTTPException(status_code=404, detail=f"No depth chart data found for team {team_code}")
            
            # If include_contracts, fetch contract data from player_contracts + contract_details
            contract_map = {}
            if include_contracts:
                # Get all contracts with latest season cap hit from contract_details
                contracts_result = conn.execute("""
                    SELECT 
                        pc.player_id,
                        pc.player_name,
                        pc.length_years,
                        pc.expiry_status,
                        pc.contract_type,
                        pc.signing_date,
                        pc.total_value,
                        cd.cap_hit,
                        cd.cap_percent,
                        cd.aav,
                        cd.season
                    FROM player_contracts pc
                    LEFT JOIN contract_details cd ON pc.id = cd.contract_id
                    WHERE pc.team_code = ?
                        AND pc.player_id IS NOT NULL
                        AND pc.player_id != ''
                    ORDER BY pc.player_id, pc.signing_date DESC, cd.season DESC
                """, [team_code]).fetchall()
                
                # Build contract lookup by player_id (keep most recent contract with cap hit)
                for row in contracts_result:
                    player_id = str(row[0])
                    if player_id not in contract_map and row[7]:  # Only add if has cap_hit
                        contract_map[player_id] = {
                            'cap_hit': row[7],
                            'cap_percent': row[8],
                            'aav': row[9],
                            'years_remaining': row[2] if row[2] else 0,
                            'expiry_status': row[3],
                            'contract_type': row[5],
                            'signing_date': str(row[5]) if row[5] else None,
                            'total_value': row[6]
                        }
        
        # Filter by roster status if specified
        if roster_status:
            roster = [p for p in roster if p.get('roster_status') == roster_status]
        
        # Transform to API response format with merged contract data
        transformed_roster = []
        for player in roster:
            player_id = str(player.get('player_id')) if player.get('player_id') else None
            contract_data = contract_map.get(player_id, {}) if player_id else {}
            
            transformed_roster.append({
                'player_id': player.get('player_id'),
                'player_name': player.get('player_name'),
                'position': player.get('position'),
                'roster_status': player.get('roster_status'),
                'dead_cap': player.get('dead_cap', False),
                'jersey_number': player.get('jersey_number'),
                'age': player.get('age'),
                'birth_date': player.get('birth_date'),
                'birth_country': player.get('birth_country'),
                'height_inches': player.get('height_inches'),
                'weight_pounds': player.get('weight_pounds'),
                'shoots_catches': player.get('shoots_catches'),
                'drafted_by': player.get('drafted_by'),
                'draft_year': player.get('draft_year'),
                'draft_round': player.get('draft_round'),
                'draft_overall': player.get('draft_overall'),
                'must_sign_date': player.get('must_sign_date'),
                'headshot': player.get('headshot'),
                'scraped_date': str(player.get('scraped_date')) if player.get('scraped_date') else None,
                # Contract data
                'cap_hit': contract_data.get('cap_hit'),
                'cap_percent': contract_data.get('cap_percent'),
                'years_remaining': contract_data.get('years_remaining'),
                'expiry_status': contract_data.get('expiry_status'),
                'contract_type': contract_data.get('contract_type'),
                'signing_date': contract_data.get('signing_date'),
                'total_value': contract_data.get('total_value')
            })
        
        return {
            "success": True,
            "team_code": team_code,
            "total_players": len(transformed_roster),
            "roster_breakdown": {
                "roster": sum(1 for p in roster if p.get('roster_status') == 'roster'),
                "non_roster": sum(1 for p in roster if p.get('roster_status') == 'non_roster'),
                "unsigned": sum(1 for p in roster if p.get('roster_status') == 'unsigned'),
                "dead_cap": sum(1 for p in roster if p.get('dead_cap'))
            },
            "data": transformed_roster
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching depth chart: {str(e)}")
