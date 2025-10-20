"""
Profiles Routes - Advanced Player Metrics

Serves aggregated advanced per-player metrics produced by
scripts/aggregate_advanced_player_metrics.py
"""

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import Any, Dict, Optional
import json
import logging

router = APIRouter(prefix="/api/v1/player", tags=["profiles-advanced"])
logger = logging.getLogger(__name__)

ADVANCED_BASE = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "player_profiles" / "advanced_metrics"
INDEX_FILE = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "player_profiles" / "player_index.json"

_ID_TO_NAME_CACHE: dict[str, dict] = {}
_INDEX_LOADED = False
_RESOLVE_CACHE: dict[str, dict] = {}

def _load_player_index() -> None:
    global _INDEX_LOADED, _ID_TO_NAME_CACHE
    if _INDEX_LOADED:
        return
    if not INDEX_FILE.exists():
        logger.warning(f"Player index not found: {INDEX_FILE}")
        _INDEX_LOADED = True
        return
    try:
        with open(INDEX_FILE, 'r') as f:
            data = json.load(f)
        # Build cache: id(str) -> {firstName,lastName,teamAbbrev}
        cache: dict[str, dict] = {}
        for row in data:
            pid = str(row.get('playerId'))
            cache[pid] = {
                'firstName': row.get('firstName'),
                'lastName': row.get('lastName'),
                'teamAbbrev': row.get('teamAbbrev'),
            }
        _ID_TO_NAME_CACHE = cache
        _INDEX_LOADED = True
    except Exception as e:
        logger.error(f"Failed to load player index: {e}")
        _INDEX_LOADED = True


def _latest_season_file_for_player(player_id: str) -> Optional[Path]:
    pdir = ADVANCED_BASE / player_id
    if not pdir.exists() or not pdir.is_dir():
        return None
    files = list(pdir.glob("*_regular_advanced.json"))
    if not files:
        return None
    # Sort by season token at start of filename
    files.sort(key=lambda f: f.name.split("_")[0], reverse=True)
    return files[0]


@router.get("/{player_id}/advanced")
async def get_player_advanced_metrics(
    player_id: str,
    season: Optional[str] = Query(None, description="Season as YYYYYYYY, e.g. 20242025"),
    game_type: str = Query("regular", description="Game type: regular or playoffs")
) -> Dict[str, Any]:
    """
    Return aggregated advanced metrics for a player/season.
    If season is not provided, returns the most recent available regular season.
    """
    # Normalize id in case a decimal arrives (8482113.0)
    try:
        player_id = str(int(float(player_id)))
    except Exception:
        player_id = str(player_id)

    pdir = ADVANCED_BASE / player_id
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="No advanced metrics for this player")

    target_file: Optional[Path] = None
    if season:
        target_file = pdir / f"{season}_{game_type}_advanced.json"
        if not target_file.exists():
            raise HTTPException(status_code=404, detail=f"Advanced metrics not found for season {season} ({game_type})")
    else:
        # pick latest regular-season file
        target_file = _latest_season_file_for_player(player_id)
        if not target_file:
            raise HTTPException(status_code=404, detail="No advanced season files found for this player")

    try:
        with open(target_file, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"Failed to read {target_file}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load advanced metrics")


@router.get("/resolve")
async def resolve_player_names(ids: str) -> Dict[str, Any]:
    """
    Resolve one or more NHL player IDs to names (last name returned primarily).

    Query:
      ids: comma-separated string of player IDs
    Response:
      { id: { lastName, firstName, teamAbbrev } }
    """
    if not ids:
        return {}
    _load_player_index()
    # Normalize & de-duplicate ids for stable caching
    id_list = [s.strip() for s in ids.split(',') if s.strip()]
    id_list = sorted(set(id_list), key=lambda x: str(int(float(x))) if x.replace('.','',1).isdigit() else x)
    cache_key = ','.join(id_list)
    # Lightweight TTL cache (60s) to prevent hammering when the frontend re-renders
    import time
    now = time.time()
    cached = _RESOLVE_CACHE.get(cache_key)
    if cached and now < cached.get('expires_at', 0):
        return cached['data']
    result: Dict[str, Any] = {}
    for raw in id_list:
        # normalize like frontend: allow floats
        try:
            pid = str(int(float(raw)))
        except Exception:
            pid = raw
        entry = _ID_TO_NAME_CACHE.get(pid)
        if entry:
            result[pid] = entry
        else:
            # Unknown id; return minimal to avoid failing UI
            result[pid] = {'lastName': pid, 'firstName': None, 'teamAbbrev': None}
    # Store in cache
    _RESOLVE_CACHE[cache_key] = { 'data': result, 'expires_at': now + 60 }
    return result


@router.get("/{player_id}/events/{game_id}")
async def get_player_events_for_game(
    player_id: str,
    game_id: int,
    season: str | None = None,
    team_abbrev: str | None = None,
) -> Dict[str, Any]:
    """
    Return per-event timeline for a player in a specific game, sourced from
    extracted metrics JSON (player_tendencies.events). Includes adjusted coordinates
    so offensive actions plot consistently regardless of period.

    Response: { events: [ { x, y, x_adj, y_adj, zone, playSection, shorthand, outcome, period, gameTime } ] }
    """
    # Normalize id
    try:
        player_id = str(int(float(player_id)))
    except Exception:
        player_id = str(player_id)

    # Search extracted metrics for the requested game JSON
    from pathlib import Path
    import json

    repo_root = Path(__file__).resolve().parents[3]
    ex_dir = repo_root / "data/processed/extracted_metrics"

    # Filenames start with playsequence-<date>-NHL-<match>-<season>-<game_id>_comprehensive_metrics.json
    # Prefer exact season + game match when provided
    # Normalize potential long NHL game id (YYYYTTGGGG) to short (GGGGG)
    gstr = str(game_id)
    short_id = gstr[-5:] if len(gstr) > 5 else gstr

    matches: list[Path] = []
    if season:
        # Allow any extra characters (e.g., " (1)") between short_id and suffix
        pattern = f"*{season}-{short_id}*_comprehensive_metrics.json"
        matches = list(ex_dir.glob(pattern))
    if not matches:
        pattern = f"*{short_id}*_comprehensive_metrics.json"
        matches = list(ex_dir.glob(pattern))
        # If multiple matches (e.g., different teams share the same early game id like 20004),
        # use team_abbrev hint when available to disambiguate (e.g., 'MTLvs', 'vsMTL').
        if team_abbrev and len(matches) > 1:
            t = team_abbrev.upper()
            name = lambda s: s.name
            filtered = [p for p in matches if (f"-{t}vs" in name(p)) or (f"vs{t}-" in name(p))]
            if filtered:
                matches = filtered
    if not matches:
        raise HTTPException(status_code=404, detail="Game extraction not found")

    # Use the first match (after narrowing)
    fpath = matches[0]
    try:
        with open(fpath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read extraction: {e}")

    pt = (data or {}).get('player_tendencies') or {}
    # Try direct lookup, then tolerant lookups (float-string keys etc.)
    pdata = pt.get(player_id) or {}
    if not pdata:
        # Try float-form key like '8480018.0'
        float_key = None
        try:
            float_key = f"{int(float(player_id))}.0"
        except Exception:
            pass
        if float_key and pt.get(float_key):
            pdata = pt.get(float_key)
    if not pdata:
        # As a last resort, search keys whose numeric normalization matches
        norm = None
        try:
            norm = int(float(player_id))
        except Exception:
            norm = None
        if norm is not None:
            for k in list(pt.keys()):
                try:
                    if int(float(str(k))) == norm:
                        pdata = pt[k]
                        break
                except Exception:
                    continue
    events = pdata.get('events') or []
    # Filter to events that have any coordinate to plot
    def has_coord(ev: dict) -> bool:
        return any(ev.get(k) is not None for k in ('x_adj','x','y_adj','y'))
    events = [
        {
            'x': ev.get('x'), 'y': ev.get('y'),
            'x_adj': ev.get('x_adj'), 'y_adj': ev.get('y_adj'),
            'zone': ev.get('zone'), 'playSection': ev.get('playSection'),
            'shorthand': ev.get('shorthand'), 'outcome': ev.get('outcome'),
            'period': ev.get('period'), 'gameTime': ev.get('gameTime'),
        }
        for ev in events if isinstance(ev, dict) and has_coord(ev)
    ]

    # Extract shifts for this player if available
    # player_shifts structure: { 'shifts': [ { player_id, start_game_time, end_game_time, ... }, ... ] }
    shifts: list[dict] = []
    try:
        psh = (data or {}).get('player_shifts') or {}
        sh_list = psh.get('shifts') or []
        # Normalize player_id for comparison (some payloads are strings)
        cmp_pid = None
        try:
            cmp_pid = str(int(float(player_id)))
        except Exception:
            cmp_pid = str(player_id)
        for sh in sh_list:
            if not isinstance(sh, dict):
                continue
            sid = sh.get('player_id')
            if sid is None:
                continue
            try:
                sid_norm = str(int(float(sid)))
            except Exception:
                sid_norm = str(sid)
            if sid_norm != cmp_pid:
                continue
            # Whitelist fields needed by UI
            shifts.append({
                'start_game_time': sh.get('start_game_time'),
                'end_game_time': sh.get('end_game_time'),
                'start_period': sh.get('start_period'),
                'end_period': sh.get('end_period'),
                'start_period_time': sh.get('start_period_time'),
                'end_period_time': sh.get('end_period_time'),
                'shift_game_length': sh.get('shift_game_length'),
                'shift_real_length': sh.get('shift_real_length'),
                'rest_game_next': sh.get('rest_game_next'),
                'rest_real_next': sh.get('rest_real_next'),
                'strength_start': sh.get('strength_start'),
                'manpower_start': sh.get('manpower_start'),
                'sequence_ids': sh.get('sequence_ids') or [],
                'deployment_ids': sh.get('deployment_ids') or [],
            })
    except Exception:
        # If anything goes wrong, just omit shifts
        shifts = []

    # Include an index so frontend can label shifts 1..N in order
    if shifts:
        # Merge micro-gaps so whistles/faceoffs don't split a shift when player stays on-ice
        try:
            MERGE_GAP_GAME_SEC = 3.0
            # sort first
            shifts.sort(key=lambda s: (s.get('start_game_time') or 0.0, s.get('end_game_time') or 0.0))
            merged: list[dict] = []
            for sh in shifts:
                if not merged:
                    merged.append(dict(sh))
                    continue
                prev = merged[-1]
                s_start = float(sh.get('start_game_time') or 0.0)
                p_end = float(prev.get('end_game_time') or 0.0)
                gap = s_start - p_end
                if gap <= MERGE_GAP_GAME_SEC:
                    # extend previous
                    # prefer later end
                    prev_end = prev.get('end_game_time')
                    sh_end = sh.get('end_game_time')
                    if (sh_end is not None) and (prev_end is None or float(sh_end) > float(prev_end)):
                        prev['end_game_time'] = sh_end
                    # carry period info
                    if sh.get('end_period') is not None:
                        prev['end_period'] = sh.get('end_period')
                    if sh.get('end_period_time') is not None:
                        prev['end_period_time'] = sh.get('end_period_time')
                    # union ids
                    for k in ('sequence_ids','deployment_ids'):
                        aset = set(prev.get(k) or [])
                        bset = set(sh.get(k) or [])
                        prev[k] = sorted(list(aset | bset))
                else:
                    merged.append(dict(sh))
            shifts = merged
        except Exception:
            # if merging fails, keep original list
            pass
        # Re-index after merge
        shifts.sort(key=lambda s: (s.get('start_game_time') or 0.0, s.get('end_game_time') or 0.0))
        for i, sh in enumerate(shifts, start=1):
            sh['index'] = i

    return { 'events': events, 'shifts': shifts }
