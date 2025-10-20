"""
Analytics Gold API Routes

Thin endpoints exposing curated analytics (gold layer) from BigQuery/BigLake
via Ontology views.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from google.cloud import bigquery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics/gold", tags=["analytics-gold"])


def _bq_client() -> bigquery.Client:
    try:
        return bigquery.Client()
    except Exception as e:
        logger.error(f"BigQuery client init failed: {e}")
        raise HTTPException(status_code=500, detail="BigQuery not available")


@router.get("/player-profiles")
async def get_player_profiles_gold(
    player_id: Optional[str] = Query(None, description="Player ID (string or int)"),
    season: Optional[str] = Query(None, description="Season YYYY-YYYY"),
    limit: int = Query(200, ge=1, le=5000)
):
    """Return aggregated player profile records from ontology.player_profiles_agg."""
    client = _bq_client()
    base = "SELECT * FROM `heartbeat-474020.ontology.player_profiles_agg` WHERE 1=1"
    params = []
    if player_id is not None:
        base += " AND CAST(player_id AS STRING) = @player_id"
        params.append(bigquery.ScalarQueryParameter("player_id", "STRING", str(player_id)))
    if season is not None:
        base += " AND season = @season"
        params.append(bigquery.ScalarQueryParameter("season", "STRING", season))
    base += " LIMIT @lim"
    params.append(bigquery.ScalarQueryParameter("lim", "INT64", int(limit)))
    try:
        job = client.query(base, job_config=bigquery.QueryJobConfig(query_parameters=params))
        df = job.result().to_dataframe()
        return {"success": True, "rows": len(df), "data": df.to_dict("records")}
    except Exception as e:
        logger.error(f"player-profiles query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-advanced")
async def get_team_advanced_gold(
    team: str = Query(..., description="Team abbreviation, e.g., MTL"),
    season: Optional[str] = Query(None, description="Season YYYY-YYYY"),
    limit: int = Query(2000, ge=1, le=10000)
):
    """Return team advanced metrics from ontology.team_advanced_metrics."""
    client = _bq_client()
    base = "SELECT * FROM `heartbeat-474020.ontology.team_advanced_metrics` WHERE UPPER(team) = @team"
    params = [bigquery.ScalarQueryParameter("team", "STRING", team.upper())]
    if season is not None:
        base += " AND season = @season"
        params.append(bigquery.ScalarQueryParameter("season", "STRING", season))
    base += " LIMIT @lim"
    params.append(bigquery.ScalarQueryParameter("lim", "INT64", int(limit)))
    try:
        job = client.query(base, job_config=bigquery.QueryJobConfig(query_parameters=params))
        df = job.result().to_dataframe()
        return {"success": True, "rows": len(df), "data": df.to_dict("records")}
    except Exception as e:
        logger.error(f"team-advanced query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

