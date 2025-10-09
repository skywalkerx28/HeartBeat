"""
Live Analytics Engine

Deterministic compute for real-time NHL game analytics. Aggregates live feeds
and computes coach-grade, lightweight metrics suitable for fast synthesis.

This module intentionally keeps calculations simple and robust to schema drift
in upstream NHL APIs. It prefers safe fallbacks over exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import logging

from orchestrator.tools.nhl_roster_client import NHLLiveGameClient
import math
import time
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# -------------------- Rate limiting & caching (top-level) --------------------
class RateLimitError(Exception):
    pass

_rate_limit_lock = asyncio.Lock()
_rate_limit_window: Dict[int, List[float]] = defaultdict(list)
_MAX_REQUESTS_PER_MINUTE = 30
_RATE_LIMIT_WINDOW_SECONDS = 60

_live_aggregate_cache: Dict[int, CachedLiveAggregate] = {}
_LIVE_CACHE_TTL_SECONDS = 8  # short TTL for freshness

# Prevent duplicate concurrent fetches for the same game
_aggregate_locks: Dict[int, asyncio.Lock] = {}
_aggregate_locks_guard = asyncio.Lock()

async def _get_game_lock(game_id: int) -> asyncio.Lock:
    async with _aggregate_locks_guard:
        lock = _aggregate_locks.get(game_id)
        if lock is None:
            lock = asyncio.Lock()
            _aggregate_locks[game_id] = lock
        return lock


def rate_limited(max_per_minute: int = _MAX_REQUESTS_PER_MINUTE):
    """Decorator to rate-limit function calls per game_id per minute."""
    def decorator(func):
        @wraps(func)
        async def wrapper(game_id: int, *args, **kwargs):
            now = time.time()
            window_start = now - _RATE_LIMIT_WINDOW_SECONDS
            async with _rate_limit_lock:
                # prune old
                _rate_limit_window[game_id] = [t for t in _rate_limit_window[game_id] if t > window_start]
                if len(_rate_limit_window[game_id]) >= max_per_minute:
                    oldest = min(_rate_limit_window[game_id])
                    wait_time = int(_RATE_LIMIT_WINDOW_SECONDS - (now - oldest) + 1)
                    raise RateLimitError(
                        f"Rate limit exceeded for game {game_id}: max {max_per_minute}/min. Try again in {wait_time}s."
                    )
                _rate_limit_window[game_id].append(now)
            return await func(game_id, *args, **kwargs)
        return wrapper
    return decorator


@dataclass
class LiveAggregate:
    game_id: int
    scoreboard: Dict[str, Any]
    boxscore: Dict[str, Any]
    play_by_play: Dict[str, Any]


@dataclass
class CachedLiveAggregate:
    """Cached live aggregate with expiration."""
    data: LiveAggregate
    expires_at: datetime


@dataclass
class TeamTotals:
    team: Optional[str] = None
    score: Optional[int] = None
    shots_on_goal: Optional[int] = None
    goals: Optional[int] = None
    attempts_approx: Optional[int] = None  # SOG + missed + blocked + goals
    penalties: Optional[int] = None
    # Strength splits (best-effort): keys 'EV', 'PP', 'PK' with per-strength counts
    strength_splits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # Per-60 rates (if elapsed available): attempts_per60, sog_per60
    attempts_per60: Optional[float] = None
    sog_per60: Optional[float] = None


@dataclass
class LiveTeamMetrics:
    game_id: int
    state: Optional[str]
    home: TeamTotals
    away: TeamTotals
    elapsed_minutes_est: Optional[float] = None
    # Short-window momentum (last 5 minutes): attempt differential home-away
    momentum_last5_attempt_diff: Optional[int] = None
    momentum_last5_sog_diff: Optional[int] = None
    momentum_last5_deep_attempt_diff: Optional[int] = None  # events <= 25 ft to opponent net
    # Zone presence (last 5 minutes)
    last5_zone_counts_home: 'ZoneCounts' = field(default_factory=lambda: ZoneCounts())
    last5_zone_counts_away: 'ZoneCounts' = field(default_factory=lambda: ZoneCounts())
    momentum_last5_zone_tilt_home: Optional[int] = None  # OZ - DZ
    momentum_last5_zone_tilt_away: Optional[int] = None


@dataclass
class ZoneCounts:
    OZ: int = 0
    NZ: int = 0
    DZ: int = 0


@dataclass
class PlayerSimple:
    full_name: str
    team: Optional[str]
    shots_on_goal: Optional[int]
    goals: Optional[int]


@dataclass
class LivePlayerMetrics:
    game_id: int
    top_skaters_by_shots: List[PlayerSimple]
    top_skaters_by_goals: List[PlayerSimple]
    # Power play unit approximation (top PP TOI skaters)
    pp_units: Dict[str, List[PlayerSimple]] = field(default_factory=dict)  # team_abbr -> players
    # Goalie workload and xGA proxies
    goalie_workload: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # 'home'/'away' -> metrics


@rate_limited(max_per_minute=30)
async def aggregate_live_feeds(game_id: int, use_cache: bool = True) -> LiveAggregate:
    """Fetch scoreboard, boxscore, and play-by-play concurrently for a game.

    Args:
        game_id: NHL game ID (10-digit integer SSSSTTGGGG)
        use_cache: Use short-lived cache to reduce API load

    Raises:
        ValueError: if game_id is not 10-digit integer
    """
    # Validate game_id format
    if not isinstance(game_id, int):
        raise ValueError(f"game_id must be integer, got {type(game_id).__name__}")
    if game_id < 1000000000 or game_id > 9999999999:
        raise ValueError(
            f"Invalid NHL game ID: {game_id}. Must be 10-digit integer (e.g., 2025020123)"
        )

    # Cache check
    if use_cache:
        cached = _live_aggregate_cache.get(game_id)
        if cached and cached.expires_at > datetime.utcnow():
            logger.debug(f"Using cached live aggregate for game {game_id}")
            return cached.data

    client = NHLLiveGameClient()

    async def _safe_fetch(coro, label: str) -> Dict[str, Any]:
        try:
            return await coro
        except Exception as e:
            logger.error(f"{label} fetch failed: {e}")
            return {"error": str(e)}

    # Per-game in-flight guard to prevent duplicate upstream calls
    lock = await _get_game_lock(game_id)
    async with lock:
        # Re-check cache after acquiring lock
        if use_cache:
            cached = _live_aggregate_cache.get(game_id)
            if cached and cached.expires_at > datetime.utcnow():
                logger.debug(f"Using cached live aggregate for game {game_id} (post-lock)")
                return cached.data

        scoreboard_c = _safe_fetch(client.get_game_data(game_id=game_id), "scoreboard")
        boxscore_c = _safe_fetch(client.get_boxscore(game_id), "boxscore")
        pbp_c = _safe_fetch(client.get_play_by_play(game_id), "play_by_play")

        scoreboard_raw, boxscore, pbp = await asyncio.gather(scoreboard_c, boxscore_c, pbp_c)

        # Normalize scoreboard to raw payload 'data' for downstream consumers
        sb_data = None
        try:
            sb_data = (scoreboard_raw.get("payload", {}) or {}).get("data")
        except Exception:
            sb_data = None
        if sb_data is None:
            try:
                sb_data = scoreboard_raw.get("data") if isinstance(scoreboard_raw, dict) else None
            except Exception:
                sb_data = None
        if sb_data is None:
            sb_data = scoreboard_raw
            logger.debug("Scoreboard normalization used fallback to raw contract")
        else:
            logger.debug("Scoreboard normalization used payload.data or data")

        agg = LiveAggregate(game_id=game_id, scoreboard=sb_data, boxscore=boxscore, play_by_play=pbp)

        # Cache write
        if use_cache:
            _live_aggregate_cache[game_id] = CachedLiveAggregate(
                data=agg,
                expires_at=datetime.utcnow() + timedelta(seconds=_LIVE_CACHE_TTL_SECONDS)
            )

        return agg


def _get_team_abbrevs_from_scoreboard(scoreboard: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    try:
        # scoreboard is expected normalized to the payload 'data'; still be defensive
        g = (scoreboard.get("data") if isinstance(scoreboard, dict) else None) or scoreboard
        home = (g.get("homeTeam") or {}).get("abbrev") or (g.get("home", {}) or {}).get("abbrev")
        away = (g.get("awayTeam") or {}).get("abbrev") or (g.get("away", {}) or {}).get("abbrev")
        return str(home) if home else None, str(away) if away else None
    except Exception:
        return None, None


def _get_scores_from_scoreboard(scoreboard: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    try:
        g = (scoreboard.get("data") if isinstance(scoreboard, dict) else None) or scoreboard
        hs = (g.get("homeTeam") or {}).get("score") or g.get("homeScore")
        as_ = (g.get("awayTeam") or {}).get("score") or g.get("awayScore")
        return (int(hs) if hs is not None else None, int(as_) if as_ is not None else None)
    except Exception:
        return None, None


def _extract_events(pbp: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Try common shapes: { data: { plays: [...] }} or { plays: [...] } or { events: [...] }
    try:
        if "data" in pbp and isinstance(pbp["data"], dict):
            for key in ("plays", "events"):
                if isinstance(pbp["data"].get(key), list):
                    return pbp["data"][key]
        for key in ("plays", "events"):
            if isinstance(pbp.get(key), list):
                return pbp[key]
    except Exception:
        pass
    return []


# Rink geometry (feet). Sportlogiq-like convention, origin at center ice.
# X runs [-100, +100], Y runs [-42.5, +42.5].
# Nets are ~11 ft from the end boards, so at ±89 ft on the x‑axis.
RINK_X_HALF = 100.0
RINK_Y_HALF = 42.5
NET_X_ABS = 89.0
NET_POS_PLUS = (NET_X_ABS, 0.0)
NET_POS_MINUS = (-NET_X_ABS, 0.0)


def _event_xy(e: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Extract (x, y) coordinates from common PBP fields; returns feet.

    Checks multiple shapes: top-level x/y, details.xCoord/yCoord, details.x/y,
    coordinates.{x,y}, result.coordinates.{x,y}.
    """
    try:
        # Top-level
        x = e.get("x")
        y = e.get("y")
        if x is not None and y is not None:
            return float(x), float(y)
    except Exception:
        pass
    try:
        d = e.get("details") or {}
        for kx, ky in (("xCoord", "yCoord"), ("x", "y")):
            x = d.get(kx)
            y = d.get(ky)
            if x is not None and y is not None:
                return float(x), float(y)
    except Exception:
        pass
    try:
        c = e.get("coordinates") or {}
        x = c.get("x")
        y = c.get("y")
        if x is not None and y is not None:
            return float(x), float(y)
    except Exception:
        pass
    try:
        rc = (e.get("result") or {}).get("coordinates") or {}
        x = rc.get("x")
        y = rc.get("y")
        if x is not None and y is not None:
            return float(x), float(y)
    except Exception:
        pass
    return None


def _distance_angle_to_net(x: float, y: float, net_x: float) -> Tuple[float, float]:
    """Distance and angle (deg) to a given net center on goal line.

    Angle is absolute angle relative to goal centerline (0 = straight on, 90 = fully lateral).
    """
    dx = net_x - float(x)
    dy = 0.0 - float(y)
    dist = math.hypot(dx, dy)
    # absolute angle from centerline; use |dy| for symmetry
    angle = math.degrees(math.atan2(abs(dy), abs(dx))) if dist > 0 else 0.0
    return dist, angle


def _infer_attacking_sides(events: List[Dict[str, Any]], home_abbr: Optional[str], away_abbr: Optional[str]) -> Dict[str, Dict[int, int]]:
    """Infer attacking net side for each team per period.

    Returns map: team_abbr -> {period_number -> +1 for +x net (right), -1 for -x net (left)}
    Uses goal or on-target shot locations; falls back to default: home +x in 1/3, -x in 2.
    """
    mapping: Dict[str, Dict[int, int]] = {t: {} for t in (home_abbr, away_abbr) if t}
    # pass 1: use goals / on-target shots with coordinates
    for e in events:
        et = _event_type_lower(e)
        if not ("goal" in et or ("shot" in et and ("on goal" in et or et == "shot" or "shot-on-goal" in et))):
            continue
        xy = _event_xy(e)
        if not xy:
            continue
        x, y = xy
        team = _event_team_abbrev(e)
        if not team:
            continue
        period = _event_period(e) or 1
        # Assign side by proximity to nets
        d_plus, _ = _distance_angle_to_net(x, y, NET_POS_PLUS[0])
        d_minus, _ = _distance_angle_to_net(x, y, NET_POS_MINUS[0])
        side = +1 if d_plus <= d_minus else -1
        if team not in mapping:
            mapping[team] = {}
        mapping[team][period] = side
    # pass 2: fill gaps with default heuristic
    for team in (home_abbr, away_abbr):
        if not team:
            continue
        if team not in mapping:
            mapping[team] = {}
        for p in (1, 2, 3):
            if p in mapping[team]:
                continue
            if team == home_abbr:
                mapping[team][p] = +1 if p in (1, 3) else -1
            else:
                mapping[team][p] = -1 if p in (1, 3) else +1
    return mapping


# (duplicate removed; defined at top of file)


def _parse_mmss_to_minutes(val: Any) -> Optional[float]:
    try:
        s = str(val)
        if ":" not in s:
            # value may already be minutes as numeric
            f = float(s)
            return f if f >= 0 else None
        mm, ss = s.split(":")
        return int(mm) + int(ss) / 60.0
    except Exception:
        return None


def _event_period(e: Dict[str, Any]) -> Optional[int]:
    try:
        p = e.get("period")
        if p is None:
            p = (e.get("about") or {}).get("period")
        if p is None:
            pd = e.get("periodDescriptor") or {}
            p = pd.get("number")
        if p is None:
            p = (e.get("details") or {}).get("periodNumber")
        return int(p) if p is not None else None
    except Exception:
        return None


def _event_elapsed_in_period_minutes(e: Dict[str, Any]) -> Optional[float]:
    # Prefer elapsed time (time since start of period). Otherwise, convert from remaining.
    for key in ("timeInPeriod", "periodTime", "timeElapsed"):
        v = (e.get("details") or {}).get(key) or e.get(key)
        m = _parse_mmss_to_minutes(v)
        if m is not None:
            return m
    # Try remaining time fields
    for key in ("timeRemaining", "clock", "gameClock"):
        v = (e.get("details") or {}).get(key) or e.get(key)
        m = _parse_mmss_to_minutes(v)
        if m is not None:
            try:
                return max(0.0, 20.0 - m)
            except Exception:
                return None
    return None


def _event_game_minute(e: Dict[str, Any]) -> Optional[float]:
    p = _event_period(e)
    m = _event_elapsed_in_period_minutes(e)
    if p is None or m is None:
        return None
    try:
        return (int(p) - 1) * 20.0 + float(m)
    except Exception:
        return None


def _extract_skaters_counts(e: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    d = e.get("details") or {}
    for hk, ak in (("homeSkaters", "awaySkaters"), ("homeTeamSkaters", "awayTeamSkaters")):
        try:
            h = d.get(hk)
            a = d.get(ak)
            if h is not None and a is not None:
                return int(h), int(a)
        except Exception:
            continue
    return None, None


def _strength_for_team(team_is_home: bool, home_skaters: Optional[int], away_skaters: Optional[int]) -> Optional[str]:
    if home_skaters is None or away_skaters is None:
        return None
    if home_skaters == away_skaters:
        return "EV"
    if team_is_home:
        return "PP" if home_skaters > away_skaters else "PK"
    else:
        return "PP" if away_skaters > home_skaters else "PK"


def _event_type_lower(e: Dict[str, Any]) -> str:
    cand = e.get("type") or e.get("typeDescKey") or e.get("eventType") or e.get("event") or e.get("result", {}).get("eventTypeId")
    return str(cand).lower() if cand is not None else ""


def _is_sog_event_type(et: str) -> bool:
    et = et or ""
    return ("goal" in et) or ("shot" in et and ("on goal" in et or et == "shot" or "shot-on-goal" in et))


def _is_attempt_event_type(et: str) -> bool:
    et = et or ""
    return ("goal" in et) or ("shot" in et) or ("miss" in et) or ("block" in et)


def _event_team_abbrev(e: Dict[str, Any]) -> Optional[str]:
    try:
        t = (e.get("team") or {}).get("abbrev")
        if t:
            return str(t)
    except Exception:
        pass
    try:
        d = e.get("details") or {}
        for k in ("eventOwnerTeamAbbrev", "teamAbbrev", "abbrev"):
            if d.get(k):
                return str(d[k])
    except Exception:
        pass
    return None


def _count_events_by_team(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {}
    for e in events:
        et = _event_type_lower(e)
        team = _event_team_abbrev(e)
        if not team:
            continue
        team = str(team)
        if team not in counts:
            counts[team] = {"sog": 0, "missed": 0, "blocked": 0, "goal": 0, "penalty": 0}
        if "goal" in et:
            counts[team]["goal"] += 1
        elif _is_sog_event_type(et):
            counts[team]["sog"] += 1
        elif "miss" in et:
            counts[team]["missed"] += 1
        elif "block" in et:
            counts[team]["blocked"] += 1
        elif "penalt" in et:
            counts[team]["penalty"] += 1
    return counts


def _estimate_elapsed_minutes(scoreboard: Dict[str, Any]) -> Optional[float]:
    try:
        g = (scoreboard.get("data") if isinstance(scoreboard, dict) else None) or scoreboard
        state = str(g.get("gameState") or g.get("status") or "").upper()
        if state not in {"LIVE", "CRIT"}:
            return None
        # Attempt to derive from period number and clock
        # Many score APIs expose: periodDescriptor.number and gameClock (MM:SS)
        pd = g.get("periodDescriptor") or {}
        num = pd.get("number") or g.get("period")
        clock = g.get("clock") or g.get("gameClock") or g.get("timeRemaining")
        minutes = 0
        try:
            minutes = (int(num) - 1) * 20
        except Exception:
            minutes = 0
        if isinstance(clock, str) and ":" in clock:
            # time remaining in current period; convert to elapsed in period
            try:
                mm, ss = clock.split(":")
                rem = int(mm) + int(ss) / 60.0
                minutes += max(0.0, 20.0 - rem)
            except Exception:
                pass
        return round(minutes, 2) if minutes >= 0 else None
    except Exception:
        return None


def compute_live_team_metrics(agg: LiveAggregate) -> LiveTeamMetrics:
    home_abbr, away_abbr = _get_team_abbrevs_from_scoreboard(agg.scoreboard)
    if not home_abbr or not away_abbr:
        logger.debug("Could not determine team abbreviations from scoreboard payload")
    hs, as_ = _get_scores_from_scoreboard(agg.scoreboard)
    state = None
    try:
        g = (agg.scoreboard.get("data") if isinstance(agg.scoreboard, dict) else None) or agg.scoreboard
        state = str(g.get("gameState") or g.get("status") or "").upper()
    except Exception:
        state = None

    events = _extract_events(agg.play_by_play)
    counts = _count_events_by_team(events)

    def _mk_totals(team_abbr: Optional[str], score: Optional[int]) -> TeamTotals:
        c = counts.get(team_abbr or "", {}) if team_abbr else {}
        attempts = None
        if c:
            attempts = c.get("sog", 0) + c.get("missed", 0) + c.get("blocked", 0) + c.get("goal", 0)
        return TeamTotals(
            team=team_abbr,
            score=score,
            shots_on_goal=(c.get("sog") if c else None),
            goals=(c.get("goal") if c else None),
            attempts_approx=attempts,
            penalties=(c.get("penalty") if c else None),
        )

    # Initialize totals
    home = _mk_totals(home_abbr, hs)
    away = _mk_totals(away_abbr, as_)
    elapsed = _estimate_elapsed_minutes(agg.scoreboard)

    # Strength splits
    try:
        for e in events:
            et = _event_type_lower(e)
            # We only split shot attempts categories + goals + penalties
            is_attempt = _is_attempt_event_type(et)
            is_penalty = "penalt" in et
            if not (is_attempt or is_penalty):
                continue
            h_skaters, a_skaters = _extract_skaters_counts(e)
            # Determine event team and assign to corresponding split
            t_abbr = _event_team_abbrev(e)
            if t_abbr is None:
                continue
            t_is_home = (t_abbr == home_abbr)
            split = _strength_for_team(t_is_home, h_skaters, a_skaters) or "EV"
            bucket = home if t_is_home else away
            if split not in bucket.strength_splits:
                bucket.strength_splits[split] = {"attempts": 0, "sog": 0, "goals": 0, "penalties": 0}
            b = bucket.strength_splits[split]
            if "goal" in et:
                b["goals"] += 1
                b["attempts"] += 1
            elif _is_sog_event_type(et):
                b["sog"] += 1
                b["attempts"] += 1
            elif "miss" in et or "block" in et:
                b["attempts"] += 1
            if is_penalty:
                b["penalties"] += 1
    except Exception:
        pass

    # Momentum window (last 5 minutes) with coordinate-aware deep attempts and zone presence
    momentum_last5_attempt_diff = None
    momentum_last5_sog_diff = None
    momentum_last5_deep_attempt_diff = None
    last5_zone_counts_home = ZoneCounts()
    last5_zone_counts_away = ZoneCounts()
    momentum_last5_zone_tilt_home = None
    momentum_last5_zone_tilt_away = None
    try:
        if elapsed is not None and elapsed > 0:
            start = max(0.0, elapsed - 5.0)
            home_attempts_5 = 0
            away_attempts_5 = 0
            home_sog_5 = 0
            away_sog_5 = 0
            home_deep_5 = 0
            away_deep_5 = 0
            sides_map = _infer_attacking_sides(events, home_abbr, away_abbr)
            for e in events:
                t = _event_game_minute(e)
                if t is None or t < start or t > elapsed + 0.5:
                    continue
                et = _event_type_lower(e)
                if not _is_attempt_event_type(et):
                    continue
                is_sog = _is_sog_event_type(et)
                team_abbr = _event_team_abbrev(e)
                # deep attempt if distance to opponent net <= 25 ft when coords available
                is_deep = False
                xy = _event_xy(e)
                if xy is not None and team_abbr in (home_abbr, away_abbr):
                    x, y = xy
                    period = _event_period(e) or 1
                    net_x = None
                    try:
                        if team_abbr in sides_map and period in sides_map[team_abbr]:
                            net_x = NET_POS_PLUS[0] if sides_map[team_abbr][period] == +1 else NET_POS_MINUS[0]
                    except Exception:
                        net_x = None
                    if net_x is None:
                        # Fallback: closer net
                        d_plus, _ = _distance_angle_to_net(x, y, NET_POS_PLUS[0])
                        d_minus, _ = _distance_angle_to_net(x, y, NET_POS_MINUS[0])
                        dist = min(d_plus, d_minus)
                    else:
                        dist, _ = _distance_angle_to_net(x, y, net_x)
                    if dist is not None and dist <= 25.0:
                        is_deep = True

                    # Zone presence for last 5: classify physical x vs team sides
                    # Home team zone classification
                    try:
                        h_side = sides_map.get(home_abbr, {}).get(period)
                        if h_side is None:
                            h_side = +1 if period in (1, 3) else -1
                        if h_side == +1:
                            # Home OZ at x > +25, DZ at x < -25
                            if x > 25.0:
                                last5_zone_counts_home.OZ += 1
                            elif x < -25.0:
                                last5_zone_counts_home.DZ += 1
                            else:
                                last5_zone_counts_home.NZ += 1
                        else:
                            # Home OZ at x < -25, DZ at x > +25
                            if x < -25.0:
                                last5_zone_counts_home.OZ += 1
                            elif x > 25.0:
                                last5_zone_counts_home.DZ += 1
                            else:
                                last5_zone_counts_home.NZ += 1
                    except Exception:
                        pass

                    # Away team zone classification
                    try:
                        a_side = sides_map.get(away_abbr, {}).get(period)
                        if a_side is None:
                            a_side = -1 if period in (1, 3) else +1
                        if a_side == +1:
                            if x > 25.0:
                                last5_zone_counts_away.OZ += 1
                            elif x < -25.0:
                                last5_zone_counts_away.DZ += 1
                            else:
                                last5_zone_counts_away.NZ += 1
                        else:
                            if x < -25.0:
                                last5_zone_counts_away.OZ += 1
                            elif x > 25.0:
                                last5_zone_counts_away.DZ += 1
                            else:
                                last5_zone_counts_away.NZ += 1
                    except Exception:
                        pass
                if team_abbr == home_abbr:
                    home_attempts_5 += 1
                    if is_sog:
                        home_sog_5 += 1
                    if is_deep:
                        home_deep_5 += 1
                elif team_abbr == away_abbr:
                    away_attempts_5 += 1
                    if is_sog:
                        away_sog_5 += 1
                    if is_deep:
                        away_deep_5 += 1
            momentum_last5_attempt_diff = home_attempts_5 - away_attempts_5
            momentum_last5_sog_diff = home_sog_5 - away_sog_5
            momentum_last5_deep_attempt_diff = home_deep_5 - away_deep_5
            momentum_last5_zone_tilt_home = last5_zone_counts_home.OZ - last5_zone_counts_home.DZ
            momentum_last5_zone_tilt_away = last5_zone_counts_away.OZ - last5_zone_counts_away.DZ
    except Exception:
        pass

    # Per-60 rates
    try:
        if elapsed and elapsed > 0:
            factor = 60.0 / float(elapsed)
            if home.attempts_approx is not None:
                home.attempts_per60 = round(home.attempts_approx * factor, 2)
            if home.shots_on_goal is not None:
                home.sog_per60 = round(home.shots_on_goal * factor, 2)
            if away.attempts_approx is not None:
                away.attempts_per60 = round(away.attempts_approx * factor, 2)
            if away.shots_on_goal is not None:
                away.sog_per60 = round(away.shots_on_goal * factor, 2)
    except Exception:
        pass

    return LiveTeamMetrics(
        game_id=agg.game_id,
        state=state,
        home=home,
        away=away,
        elapsed_minutes_est=elapsed,
        momentum_last5_attempt_diff=momentum_last5_attempt_diff,
        momentum_last5_sog_diff=momentum_last5_sog_diff,
        momentum_last5_deep_attempt_diff=momentum_last5_deep_attempt_diff,
        last5_zone_counts_home=last5_zone_counts_home,
        last5_zone_counts_away=last5_zone_counts_away,
        momentum_last5_zone_tilt_home=momentum_last5_zone_tilt_home,
        momentum_last5_zone_tilt_away=momentum_last5_zone_tilt_away,
    )


def _top_players_from_boxscore(box: Dict[str, Any]) -> Tuple[List[PlayerSimple], List[PlayerSimple]]:
    top_shots: List[PlayerSimple] = []
    top_goals: List[PlayerSimple] = []
    try:
        data = box.get("data") or {}
        for team_key in ("homeTeam", "home", "awayTeam", "away"):
            team_obj = data.get(team_key) or {}
            abbrev = (team_obj.get("abbrev") or team_obj.get("teamAbbrev") or
                      (team_obj.get("team", {}) or {}).get("abbrev"))
            players = (team_obj.get("players") or team_obj.get("playerByGameStats") or {}).values() if isinstance(team_obj.get("players") or team_obj.get("playerByGameStats"), dict) else []
            for p in players:
                try:
                    name = p.get("name") or p.get("firstName", {}).get("default", "") + " " + p.get("lastName", {}).get("default", "")
                    sog = int(p.get("shots", 0) or p.get("sog", 0))
                    goals = int(p.get("goals", 0))
                    if sog:
                        top_shots.append(PlayerSimple(full_name=name.strip(), team=str(abbrev) if abbrev else None, shots_on_goal=sog, goals=goals))
                    if goals:
                        top_goals.append(PlayerSimple(full_name=name.strip(), team=str(abbrev) if abbrev else None, shots_on_goal=sog, goals=goals))
                except Exception:
                    continue
    except Exception:
        pass
    # Sort and cap
    top_shots.sort(key=lambda x: (x.shots_on_goal or 0), reverse=True)
    top_goals.sort(key=lambda x: (x.goals or 0), reverse=True)
    return top_shots[:5], top_goals[:5]


def _extract_pp_toi_seconds(p: Dict[str, Any]) -> int:
    # Try multiple likely keys for PP time on ice
    keys = [
        "ppTimeOnIceSeconds", "powerPlayTimeOnIceSeconds", "ppToiSec",
        "ppToi", "powerPlayToi", "powerPlayTimeOnIce"
    ]
    for k in keys:
        v = p.get(k)
        if v is None:
            continue
        # If already numeric seconds
        try:
            if isinstance(v, (int, float)):
                return int(v)
        except Exception:
            pass
        # Parse MM:SS
        mins = _parse_mmss_to_minutes(v)
        if mins is not None:
            try:
                return int(mins * 60)
            except Exception:
                continue
    # Try nested dicts
    try:
        st = p.get("specialTeams") or {}
        return int(st.get("powerPlayTimeOnIceSeconds") or 0)
    except Exception:
        return 0


def _extract_teams_players_from_box(box: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    teams: Dict[str, List[Dict[str, Any]]] = {}
    try:
        data = box.get("data") or {}
        for team_key in ("homeTeam", "home", "awayTeam", "away"):
            team_obj = data.get(team_key) or {}
            abbrev = (team_obj.get("abbrev") or team_obj.get("teamAbbrev") or
                      (team_obj.get("team", {}) or {}).get("abbrev"))
            if not abbrev:
                continue
            players_map = team_obj.get("players") or team_obj.get("playerByGameStats")
            players: List[Dict[str, Any]] = []
            if isinstance(players_map, dict):
                players = list(players_map.values())
            teams[str(abbrev)] = players
    except Exception:
        pass
    return teams


def _compute_goalie_workload(
    events: List[Dict[str, Any]],
    home_abbr: Optional[str],
    away_abbr: Optional[str],
    window_end_min: Optional[float],
    sides_map: Optional[Dict[str, Dict[int, int]]] = None,
) -> Dict[str, Dict[str, Any]]:
    # Define on-target and xG proxy
    def is_on_target(et: str) -> bool:
        return _is_sog_event_type(et)

    def shot_xg_proxy(e: Dict[str, Any], sides_map: Dict[str, Dict[int, int]]) -> float:
        d_details = e.get("details") or {}
        # Empty-net handling: near-certain goal probability against empty net
        try:
            if d_details.get("emptyNet") or d_details.get("empty_net") or d_details.get("isEmptyNet"):
                return 0.95
        except Exception:
            pass
        st = (d_details.get("shotType") or d_details.get("shotTypeCode") or d_details.get("shotTypeDescKey") or "").lower()
        # Baseline by shot type
        base = {
            "wrist": 0.08, "snap": 0.09, "slap": 0.05, "backhand": 0.07,
            "tip": 0.11, "deflected": 0.10, "wrap-around": 0.09, "wraparound": 0.09
        }.get(st, 0.07)

        # Prefer coordinate-derived distance/angle
        xy = _event_xy(e)
        dist = None
        angle = None
        if xy is not None:
            x, y = xy
            team = _event_team_abbrev(e)
            period = _event_period(e) or 1
            net_x = None
            try:
                if team in sides_map and period in sides_map[team]:
                    net_x = NET_POS_PLUS[0] if sides_map[team][period] == +1 else NET_POS_MINUS[0]
            except Exception:
                net_x = None
            if net_x is None:
                # Fallback: use closer net
                d_plus, _ = _distance_angle_to_net(x, y, NET_POS_PLUS[0])
                d_minus, _ = _distance_angle_to_net(x, y, NET_POS_MINUS[0])
                net_x = NET_POS_PLUS[0] if d_plus <= d_minus else NET_POS_MINUS[0]
            dist, angle = _distance_angle_to_net(x, y, net_x)
        else:
            # Secondary fallback: try distance fields if provided
            for k in ("shotDistance", "distanceFt", "shotDistanceFt"):
                try:
                    v = d_details.get(k)
                    if v is not None:
                        dist = float(v)
                        break
                except Exception:
                    continue

        # Apply modifiers
        if dist is not None:
            if dist < 10:
                base *= 1.6
            elif dist < 25:
                base *= 1.2
            elif dist > 45:
                base *= 0.75
            else:
                base *= 0.9
        if angle is not None:
            if angle > 60:
                base *= 0.7
            elif angle > 40:
                base *= 0.85

        # Mild rebound bonus if detectable in details
        try:
            if any(k in d_details and bool(d_details.get(k)) for k in ("rebound", "isRebound", "reboundShot")):
                base *= 1.1
        except Exception:
            pass

        # Clamp and return
        if base < 0.01:
            base = 0.01
        if base > 0.7:
            base = 0.7
        return round(base, 4)

    # Time window for last 5 minutes
    start_min = None
    if window_end_min is not None:
        start_min = max(0.0, window_end_min - 5.0)

    result = {
        "home": {"shots_against_total": 0, "shots_against_5min": 0, "xga_total": 0.0, "xga_5min": 0.0},
        "away": {"shots_against_total": 0, "shots_against_5min": 0, "xga_total": 0.0, "xga_5min": 0.0},
    }
    # Precompute attacking sides map for distance/angle orientation if not provided
    if sides_map is None:
        sides_map = _infer_attacking_sides(events, home_abbr, away_abbr)

    for e in events:
        et = _event_type_lower(e)
        if not is_on_target(et):
            continue
        t_min = _event_game_minute(e)
        team_abbr = _event_team_abbrev(e)
        # Assign shot against the opposing goalie
        if team_abbr == home_abbr:
            side = "away"
        elif team_abbr == away_abbr:
            side = "home"
        else:
            continue
        result[side]["shots_against_total"] += 1
        xg = shot_xg_proxy(e, sides_map)
        result[side]["xga_total"] = round(result[side]["xga_total"] + xg, 3)
        if start_min is not None and t_min is not None and start_min <= t_min <= (window_end_min + 0.5):
            result[side]["shots_against_5min"] += 1
            result[side]["xga_5min"] = round(result[side]["xga_5min"] + xg, 3)

    return result


def _compute_pp_units(box: Dict[str, Any]) -> Dict[str, List[PlayerSimple]]:
    teams_players = _extract_teams_players_from_box(box)
    pp_units: Dict[str, List[PlayerSimple]] = {}
    for team_abbr, players in teams_players.items():
        scored = []
        for p in players:
            try:
                pp_sec = _extract_pp_toi_seconds(p)
            except Exception:
                pp_sec = 0
            if pp_sec and pp_sec > 0:
                name = p.get("name") or (
                    (p.get("firstName", {}) or {}).get("default", "") + " " + (p.get("lastName", {}) or {}).get("default", "")
                )
                if name:
                    scored.append((pp_sec, name.strip()))
        # Sort by PP TOI desc and take top 5 as a proxy PP unit
        scored.sort(key=lambda x: x[0], reverse=True)
        unit_players = [PlayerSimple(full_name=n, team=team_abbr, shots_on_goal=None, goals=None) for (sec, n) in scored[:5]]
        if unit_players:
            pp_units[team_abbr] = unit_players
    return pp_units


def compute_live_player_unit_metrics(agg: LiveAggregate) -> LivePlayerMetrics:
    shots, goals = _top_players_from_boxscore(agg.boxscore)
    pp_units = _compute_pp_units(agg.boxscore)
    home_abbr, away_abbr = _get_team_abbrevs_from_scoreboard(agg.scoreboard)
    events = _extract_events(agg.play_by_play)
    elapsed = _estimate_elapsed_minutes(agg.scoreboard)
    # Reuse sides map for consistency
    sides_map = _infer_attacking_sides(events, home_abbr, away_abbr)
    goalie_workload = _compute_goalie_workload(events, home_abbr, away_abbr, elapsed, sides_map)
    return LivePlayerMetrics(
        game_id=agg.game_id,
        top_skaters_by_shots=shots,
        top_skaters_by_goals=goals,
        pp_units=pp_units,
        goalie_workload=goalie_workload,
    )


def compute_contextual_insights(team_metrics: LiveTeamMetrics) -> List[str]:
    insights: List[str] = []
    # Sample-size guard
    if team_metrics.elapsed_minutes_est is not None and team_metrics.elapsed_minutes_est < 5:
        insights.append("Small sample: <5 minutes elapsed; interpret rates cautiously.")
    # Lead/deficit context
    try:
        hs = team_metrics.home.score or 0
        as_ = team_metrics.away.score or 0
        if hs > as_:
            insights.append("Home team leading; expect more defensive posture late in periods.")
        elif as_ > hs:
            insights.append("Away team leading; trailing team may increase forecheck pressure.")
    except Exception:
        pass
    # Shot pressure proxy
    try:
        if (team_metrics.home.attempts_approx or 0) > (team_metrics.away.attempts_approx or 0) + 10:
            insights.append("Home team driving shot attempts; territorial edge indicated.")
        elif (team_metrics.away.attempts_approx or 0) > (team_metrics.home.attempts_approx or 0) + 10:
            insights.append("Away team driving shot attempts; territorial edge indicated.")
    except Exception:
        pass
    # Momentum last 5
    try:
        md = team_metrics.momentum_last5_attempt_diff
        if md is not None:
            if md >= 6:
                insights.append("Strong home momentum in last 5 minutes (attempts +6 or more).")
            elif md <= -6:
                insights.append("Strong away momentum in last 5 minutes (attempts +6 or more).")
    except Exception:
        pass
    # Special teams edge
    try:
        hv = team_metrics.home.strength_splits.get("PP", {})
        av = team_metrics.away.strength_splits.get("PP", {})
        if (hv.get("attempts", 0) >= av.get("attempts", 0) + 5):
            insights.append("Home power play has generated materially more attempts so far.")
        elif (av.get("attempts", 0) >= hv.get("attempts", 0) + 5):
            insights.append("Away power play has generated materially more attempts so far.")
    except Exception:
        pass
    # Zone tilt in last 5 minutes
    try:
        ht = team_metrics.momentum_last5_zone_tilt_home
        at = team_metrics.momentum_last5_zone_tilt_away
        if ht is not None and at is not None:
            if ht >= 4:
                insights.append("Home zone tilt (last 5) indicates sustained OZ presence.")
            elif at >= 4:
                insights.append("Away zone tilt (last 5) indicates sustained OZ presence.")
    except Exception:
        pass
    return insights


def to_dict(obj: Any) -> Any:
    try:
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
    except Exception:
        pass
    return obj
