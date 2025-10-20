
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pathlib import Path
import pandas as pd
import logging

router = APIRouter(prefix="/api/predictions", tags=["predictions"])
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
FORECASTS_BASE = ROOT / 'data/processed/predictions/forecasts'

@router.get("/player/{player_id}/{season}")
async def get_player_season_forecast(player_id: str, season: str, metric: str = 'points', game_type: str = 'regular') -> Dict[str, Any]:
    try:
        season_dir = FORECASTS_BASE / season / game_type / metric / str(player_id)
        union = FORECASTS_BASE / season / game_type / metric / 'forecasts_union.parquet'
        if not season_dir.exists() and not union.exists():
            raise HTTPException(status_code=404, detail="No forecasts found for this season/metric")
        # Prefer per-player file
        if season_dir.exists():
            f = season_dir / 'forecast.parquet'
            if f.exists():
                df = pd.read_parquet(f)
            else:
                raise HTTPException(status_code=404, detail="Forecast file missing for player")
        else:
            dfu = pd.read_parquet(union)
            df = dfu[dfu['playerId'].astype(str) == str(player_id)]
            if df.empty:
                raise HTTPException(status_code=404, detail="Player not found in union forecasts")
        # return compact JSON
        df = df.sort_values('step')
        payload = {
            'playerId': str(player_id),
            'season': season,
            'metric': metric,
            'gameType': game_type,
            'currentTotal': float(df['currentTotal'].iloc[0]) if 'currentTotal' in df.columns else None,
            'steps': df['step'].astype(int).tolist(),
            'p10': [float(x) for x in df['p10'].tolist()],
            'p50': [float(x) for x in df['p50'].tolist()],
            'p90': [float(x) for x in df['p90'].tolist()],
            'projectedTotal_p50': [float(x) for x in df['projectedTotal_p50'].tolist()],
            'projectedTotal_mean': [float(x) for x in df['projectedTotal_mean'].tolist()],
        }
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
