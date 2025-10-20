"""
Team Profiles Routes - Advanced Team Metrics

Serves aggregated advanced per-team metrics produced by
scripts/transform/aggregate_team_metrics.py
"""

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import Any, Dict, Optional
import json
import logging
import pandas as pd

router = APIRouter(prefix="/api/v1/team", tags=["team-profiles-advanced"])
logger = logging.getLogger(__name__)

ADVANCED_TEAM_BASE = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "team_profiles" / "advanced_metrics"
ROTATIONS_BASE = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "line_matchup_engine"


def _latest_season_file_for_team(team_abbrev: str) -> Optional[Path]:
    tdir = ADVANCED_TEAM_BASE / team_abbrev.upper()
    if not tdir.exists() or not tdir.is_dir():
        return None
    files = list(tdir.glob("*_team_advanced.json"))
    if not files:
        return None
    files.sort(key=lambda f: f.name.split("_")[0], reverse=True)
    return files[0]


def _normalize_season_token(season: Optional[str]) -> Optional[str]:
    """Return season token in YYYY-YYYY form when possible."""
    if not season:
        return None
    s = str(season)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:]}"
    return s


def _load_game_dates_for_team(team: str, season: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Return { gameId(str) -> { game_date, result, gf, ga, opponent } } for a team/season."""
    result: Dict[str, Dict[str, Any]] = {}
    s = _normalize_season_token(season)
    if not s:
        return result
    tdir = ADVANCED_TEAM_BASE / team
    # Accept both formats
    candidates = [
        tdir / f"{s.replace('-', '')}_team_advanced.json",
        tdir / f"{s}_team_advanced.json",
    ]
    target = next((p for p in candidates if p.exists()), None)
    if not target:
        return result
    try:
        with open(target, 'r') as f:
            data = json.load(f)
        for g in (data or {}).get('games', []):
            gid = str(g.get('gameId'))
            if not gid:
                continue
            gf = int(g.get('goals_for', 0) or 0)
            ga = int(g.get('goals_against', 0) or 0)
            res = 'W' if gf > ga else 'L' if ga > gf else 'T'
            result[gid] = {
                'game_date': g.get('gameDate'),
                'result': res,
                'gf': gf,
                'ga': ga,
                'opponent': g.get('opponent')
            }
    except Exception:
        return {}
    return result


@router.get("/{team_abbrev}/advanced")
async def get_team_advanced_metrics(
    team_abbrev: str,
    season: Optional[str] = Query(None, description="Season as YYYYYYYY, e.g. 20242025"),
    game_type: str = Query("regular", description="Game type, currently 'regular' only")
) -> Dict[str, Any]:
    """
    Return aggregated advanced metrics for a team/season.
    If season is not provided, returns the most recent available file.
    """
    team_abbrev = team_abbrev.upper()
    tdir = ADVANCED_TEAM_BASE / team_abbrev
    if not tdir.exists():
        raise HTTPException(status_code=404, detail="No advanced metrics for this team")

    target_file: Optional[Path] = None
    if season:
        target_file = tdir / f"{season}_team_advanced.json"
        if not target_file.exists():
            raise HTTPException(status_code=404, detail=f"Team advanced metrics not found for season {season}")
    else:
        target_file = _latest_season_file_for_team(team_abbrev)
        if not target_file:
            raise HTTPException(status_code=404, detail="No advanced season files found for this team")

    try:
        with open(target_file, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"Failed to read {target_file}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load team advanced metrics")


@router.get("/{team_abbrev}/rotations")
async def get_team_rotation_events(
    team_abbrev: str,
    season: Optional[str] = Query(None, description="Season label, e.g., 2024-2025 or 20242025"),
    opponent: Optional[str] = Query(None, description="Filter by opponent team abbrev"),
    strength: Optional[str] = Query(None, description="Filter by strength state, e.g., 5v5, 5v4"),
    limit: int = Query(500, ge=1, le=5000, description="Max events to return (most recent first)"),
    aggregate: bool = Query(False, description="Return aggregated from->to counts instead of raw events"),
    groupBy: Optional[str] = Query(None, description="When aggregate=true, optionally group by 'game'")
) -> Dict[str, Any]:
    """
    Return team-level line rotation events with context and player-for-player replacements.

    Source: scripts/transform/extract_team_rotations.py → team_line_rotations.parquet
    """
    team = team_abbrev.upper()
    if aggregate:
        # Per-game transitions require rebuilding from events
        if groupBy and groupBy.lower() == 'game':
            rot_file = ROTATIONS_BASE / 'team_line_rotations.parquet'
            if not rot_file.exists():
                raise HTTPException(status_code=404, detail="Rotation log not generated yet. Run extractor")
            try:
                ev = pd.read_parquet(rot_file)
            except Exception as e:
                logger.error(f"Failed to load rotation events: {e}")
                raise HTTPException(status_code=500, detail="Failed to load rotation events")
            ev = ev.copy()
            ev['team'] = ev['team'].astype(str).str.upper()
            ev = ev[ev['team'] == team]
            if 'source' in ev.columns:
                ev = ev[ev['source'].astype(str) == 'CHE']
            if strength:
                ev = ev[ev['strength_state'].astype(str).str.lower() == strength.lower()]
            if season and 'season' in ev.columns:
                s = str(season)
                s_norm = f"{s[:4]}-{s[4:]}" if len(s) == 8 and s.isdigit() else s
                ev = ev[ev['season'].astype(str).isin([s, s_norm])]
            if opponent and 'opponent' in ev.columns:
                ev['opponent'] = ev['opponent'].astype(str).str.upper()
                ev = ev[ev['opponent'] == opponent.upper()]
            # Build line keys
            def mk_key(fwd, d):
                f = fwd if isinstance(fwd, str) else ''
                dd = d if isinstance(d, str) else ''
                return f"F:{f}_D:{dd}"
            ev = ev.assign(
                from_line=ev.apply(lambda r: mk_key(r.get('from_forwards'), r.get('from_defense')), axis=1),
                to_line=ev.apply(lambda r: mk_key(r.get('to_forwards'), r.get('to_defense')), axis=1),
            )
            group_cols = ['team', 'game_id', 'season', 'opponent', 'strength_state', 'from_line', 'to_line']
            agg_df = ev.groupby(group_cols, as_index=False).size().rename(columns={'size': 'count'})
            # Attach game date and result when available
            meta = _load_game_dates_for_team(team, season)
            if meta:
                agg_df['game_date'] = agg_df['game_id'].apply(lambda gid: (meta.get(str(gid)) or {}).get('game_date'))
                agg_df['result'] = agg_df['game_id'].apply(lambda gid: (meta.get(str(gid)) or {}).get('result'))
            agg_df = agg_df.sort_values('count', ascending=False)
            if limit and len(agg_df) > limit:
                agg_df = agg_df.head(limit)
            return {
                'team': team,
                'count': int(len(agg_df)),
                'transitions': agg_df.to_dict(orient='records')
            }

        # Default aggregate: read transitions parquet (overall counts)
        trans_file = ROTATIONS_BASE / 'team_line_rotation_transitions.parquet'
        if not trans_file.exists():
            raise HTTPException(status_code=404, detail="Rotation transitions not generated. Run scripts/transform/extract_team_rotations.py")
        try:
            df = pd.read_parquet(trans_file)
        except Exception as e:
            logger.error(f"Failed to load rotation transitions: {e}")
            raise HTTPException(status_code=500, detail="Failed to load rotation transitions")
        df = df.copy()
        df['team'] = df['team'].astype(str).str.upper()
        df = df[df['team'] == team]
        if 'source' in df.columns:
            df = df[df['source'].astype(str) == 'CHE']
        if strength:
            df = df[df['strength_state'].astype(str).str.lower() == strength.lower()]
        if season and 'season' in df.columns:
            s = str(season)
            s_norm = f"{s[:4]}-{s[4:]}" if len(s) == 8 and s.isdigit() else s
            df = df[df['season'].astype(str).isin([s, s_norm])]
        df = df.sort_values('count', ascending=False)
        if limit and len(df) > limit:
            df = df.head(limit)
        return {
            'team': team,
            'count': int(len(df)),
            'transitions': df.to_dict(orient='records')
        }

    rot_file = ROTATIONS_BASE / 'team_line_rotations.parquet'
    if not rot_file.exists():
        raise HTTPException(status_code=404, detail="Rotation log not generated yet. Run scripts/transform/extract_team_rotations.py")

    try:
        df = pd.read_parquet(rot_file)
    except Exception as e:
        logger.error(f"Failed to load rotations: {e}")
        raise HTTPException(status_code=500, detail="Failed to load rotation logs")

    # Normalize and filter
    df = df.copy()
    df['team'] = df['team'].astype(str).str.upper()
    df['opponent'] = df['opponent'].astype(str).str.upper()
    df = df[df['team'] == team]
    if 'source' in df.columns:
        df = df[df['source'].astype(str) == 'CHE']

    if season:
        # Support both formats by normalizing parquet season values to 2024-2025 string if possible
        s = str(season)
        if len(s) == 8 and s.isdigit():
            s_norm = f"{s[:4]}-{s[4:]}"
            df = df[df['season'].astype(str).isin([s, s_norm])]
        else:
            df = df[df['season'].astype(str) == s]

    if opponent:
        df = df[df['opponent'] == opponent.upper()]
    if strength:
        df = df[df['strength_state'].astype(str).str.lower() == strength.lower()]

    # Most recent first by game_time; fall back to index
    if 'game_time' in df.columns:
        df = df.sort_values(['game_id', 'game_time'], ascending=[True, True])
    else:
        df = df.sort_index()

    # Limit
    if limit and len(df) > limit:
        df = df.tail(limit)

    # Parse replacement JSON columns to arrays of {out,in}
    def parse_json(s):
        try:
            # Convert numpy arrays to plain Python lists for JSON safety
            import numpy as np
            if isinstance(s, np.ndarray):
                return s.tolist()
            # If it is a JSON string, parse it
            if isinstance(s, str):
                return json.loads(s)
            # Already a list/dict/None is OK
            return s
        except Exception:
            return None

    if 'replacements_f' in df.columns:
        df['replacements_f'] = df['replacements_f'].apply(parse_json)
    if 'replacements_d' in df.columns:
        df['replacements_d'] = df['replacements_d'].apply(parse_json)

    payload = {
        'team': team,
        'count': int(len(df)),
        'events': df.to_dict(orient='records')
    }
    return payload


# ————————————————————————————————————————————————————————————————
# Game-level deployments (enriched with score)
# ————————————————————————————————————————————————————————————————

@router.get("/game/{game_id}/deployments")
async def get_game_deployments(
    game_id: int,
) -> Dict[str, Any]:
    """
    Return whistle-level deployments for a specific game, enriched with score
    at the start of each deployment.

    Source: data/processed/extracted_metrics/*_{game_id}_comprehensive_metrics.json

    Response structure:
      {
        game_id,
        home_team_code,
        away_team_code,
        deployments: [
          {
            deployment_id, whistle_time, whistle_event_index, period,
            home_forwards, home_defense, away_forwards, away_defense,
            strength, manpowerSituation, home_skaters, away_skaters,
            home_zone, away_zone, faceoff_zone, faceoff_winner_team,
            home_score, away_score, score_diff
          }, ...
        ],
        period_openers: [ same enrichment when available ]
      }
    """
    # Locate comprehensive extraction JSON for this game
    repo_root = Path(__file__).resolve().parents[3]
    ex_dir = repo_root / "data/processed/extracted_metrics"

    gstr = str(game_id)
    short_id = gstr[-5:] if len(gstr) > 5 else gstr
    matches = list(ex_dir.glob(f"*{short_id}*_comprehensive_metrics.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="Comprehensive extraction not found for game")
    # Prefer exact game id suffix match if multiple
    target = None
    for p in matches:
        if p.name.endswith(f"-{short_id}_comprehensive_metrics.json") or p.name.endswith(f"-{gstr}_comprehensive_metrics.json"):
            target = p
            break
    if target is None:
        target = matches[0]

    try:
        with open(target, 'r') as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read extraction: {e}")

    game_info = (data or {}).get('game_info') or {}
    wd = ((data or {}).get('whistle_deployments') or {}).get('deployments') or []
    sequences = ((data or {}).get('whistle_sequences') or {}).get('sequences') or []
    period_openers = (data or {}).get('period_openers') or []

    # Build lookup maps
    seq_by_dep: Dict[int, dict] = {}
    seq_by_start_whistle: Dict[int, dict] = {}
    for s in sequences:
        dep_id = s.get('deployment_id')
        if dep_id is not None:
            seq_by_dep[int(dep_id)] = s
        sw = s.get('start_whistle_index')
        if isinstance(sw, int):
            seq_by_start_whistle[sw] = s

    def enrich_with_score(d: dict) -> dict:
        # Try by deployment id, else by whistle index
        seq = None
        dep_id = d.get('deployment_id')
        if dep_id is not None and int(dep_id) in seq_by_dep:
            seq = seq_by_dep[int(dep_id)]
        else:
            widx = d.get('whistle_event_index')
            if isinstance(widx, int):
                seq = seq_by_start_whistle.get(widx)
        if seq:
            gsb = (seq.get('game_state_before') or {})
            d = dict(d)
            d['home_score'] = gsb.get('home_score')
            d['away_score'] = gsb.get('away_score')
            d['score_diff'] = gsb.get('score_diff')
        return d

    deployments_out = [enrich_with_score(d) for d in wd]
    period_out = [enrich_with_score(d) for d in period_openers]

    return {
        'game_id': game_id,
        'home_team_code': game_info.get('home_team') or game_info.get('home_team_code'),
        'away_team_code': game_info.get('away_team') or game_info.get('away_team_code'),
        'deployments': deployments_out,
        'period_openers': period_out,
        'source_file': str(target.name),
    }
