"""
HeartBeat Engine - NHL Data Clients
Montreal Canadiens Advanced Analytics Assistant

NHL Roster Client:
- Primary source: NHL API roster endpoint (team/season) when available
- Fallback: Next/last game play-by-play rosterSpots when needed
- Overlay: Optional merge with local snapshot data
- Caching: Per-team TTL cache to avoid excessive API calls

NHL Live Game Client:
- Real-time game data from NHL API endpoints
- Score, shots, period, clock, situation updates
- Play-by-play events with coordinates
- Intelligent caching (10-15s for live games, 5min for future games)
- Comprehensive boxscore and player stats
- Video highlight links and game reports
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import asyncio
import logging
from pathlib import Path
import json

import csv
import httpx
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

logger = logging.getLogger(__name__)


@dataclass
class CachedRoster:
    data: Dict[str, Any]
    expires_at: datetime


class NHLRosterClient:
    """
    Lightweight async client for NHL team rosters with TTL caching and Parquet-based player mapping.
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        self._cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, CachedRoster] = {}

        # Resolve repo root to load local data consistently
        from orchestrator.config.settings import settings
        # Use processed data path from settings
        self._data_root = Path(settings.parquet.data_directory)
        # NHL rosters JSON path (team-specific, updated nightly)
        self._rosters_dir = self._data_root / "rosters"

    # ------------------------ Public API ------------------------

    async def get_team_roster(
        self,
        team: str,
        season: Optional[str] = None,
        scope: str = "active"
    ) -> Dict[str, Any]:
        """
        Get roster for an NHL team.

        Args:
            team: Team abbreviation (e.g., "MTL", "TOR")
            season: NHL season (e.g., "2025-2026" or "current")
            scope: "active" | "all" | "organization" (best effort)
        """

        key = self._cache_key(team, season or "current", scope)
        cached = self._cache.get(key)
        if cached and cached.expires_at > datetime.utcnow():
            return cached.data

        roster = await self._fetch_roster_with_fallback(team, season, scope)
        # Map IDs and normalize
        roster_norm = self._normalize_and_enrich(roster, team, season or "current", scope)

        # Cache result
        self._cache[key] = CachedRoster(
            data=roster_norm,
            expires_at=datetime.utcnow() + timedelta(seconds=self._cache_ttl)
        )

        return roster_norm

    async def get_all_rosters(
        self,
        teams: List[str],
        season: Optional[str] = None,
        scope: str = "active",
        max_concurrency: int = 6
    ) -> Dict[str, Any]:
        """Fetch rosters for multiple teams with concurrency limits."""

        semaphore = asyncio.Semaphore(max_concurrency)
        results: Dict[str, Any] = {}

        async def _fetch(team_abbr: str):
            async with semaphore:
                try:
                    results[team_abbr] = await self.get_team_roster(team_abbr, season, scope)
                except Exception as e:
                    logger.error(f"Roster fetch failed for {team_abbr}: {e}")
                    results[team_abbr] = {"team": team_abbr, "error": str(e)}

        await asyncio.gather(*[_fetch(t) for t in teams])
        return results

    # ------------------------ Internals ------------------------

    async def _fetch_roster_with_fallback(
        self,
        team: str,
        season: Optional[str],
        scope: str
    ) -> Dict[str, Any]:
        # 1) Try official roster endpoint (widely used pattern)
        season_str = await self._normalize_season(season)
        roster_found = False

        # Try multiple season formats during preseason
        # Priority: current > formatted season > fallbacks
        if season_str == "2025-2026" or season is None:
            season_formats = ["current", season_str, "20252026", "2025"]
        else:
            season_formats = [season_str, "current"]

        for season_fmt in season_formats:
            try:
                url = f"https://api-web.nhle.com/v1/roster/{team}/{season_fmt}"
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(url, headers={"Accept": "application/json"})
                    if resp.status_code == 200 and isinstance(resp.json(), dict):
                        data = resp.json()
                        return {"source": "nhl_roster", "raw": data}
                    elif resp.status_code != 404:
                        logger.warning(f"Roster endpoint returned {resp.status_code} for {team}/{season_fmt}")
            except Exception as e:
                logger.warning(f"Roster endpoint failed for {team}/{season_fmt}: {e}")

        if not roster_found:
            logger.info(f"No roster data available for {team} - team may not have played preseason games yet")

        # 2) Fallback: derive from next/last game rosterSpots
        try:
            # Strategy: get schedule for next 3 days and previous 3 days, find a game with this team
            game_id = await self._find_nearby_game_id(team)
            if game_id:
                pbp_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(pbp_url, headers={"Accept": "application/json"})
                    if resp.status_code == 200 and isinstance(resp.json(), dict):
                        data = resp.json()
                        return {"source": "rosterSpots", "raw": data.get("rosterSpots", [])}
        except Exception as e:
            logger.error(f"Fallback rosterSpots failed for {team}: {e}")

        # 3) Final fallback: empty structure
        return {"source": "empty", "raw": []}

    async def _find_nearby_game_id(self, team: str) -> Optional[int]:
        """Find a recent game involving team within last 14 days (for daily roster updates)."""
        try:
            today = datetime.utcnow().date()
            # Search recent games for daily roster updates (14 days)
            dates = [today + timedelta(days=d) for d in range(-14, 1)]
            async with httpx.AsyncClient(timeout=10.0) as client:
                for dt in dates:
                    url = f"https://api-web.nhle.com/v1/score/{dt.isoformat()}"
                    resp = await client.get(url, headers={"Accept": "application/json"})
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    games = data.get("games", []) if isinstance(data, dict) else []
                    for g in games:
                        try:
                            if g.get("homeTeam", {}).get("abbrev") == team or g.get("awayTeam", {}).get("abbrev") == team:
                                return g.get("id")
                        except Exception:
                            continue
        except Exception as e:
            logger.warning(f"Nearby game search failed for {team}: {e}")
        return None

    async def _normalize_season(self, season: Optional[str]) -> str:
        if season and season != "current":
            return season
        # Calculate current NHL season based on month
        now = datetime.utcnow()
        if now.month >= 10:
            return f"{now.year}-{now.year + 1}"
        return f"{now.year - 1}-{now.year}"

    def _normalize_and_enrich(
        self,
        roster_payload: Dict[str, Any],
        team: str,
        season: str,
        scope: str
    ) -> Dict[str, Any]:
        """Normalize payload into a consistent roster dict. No parquet enrichment."""
        players: List[Dict[str, Any]] = []

        source = roster_payload.get("source")
        raw = roster_payload.get("raw")

        if source == "nhl_roster" and isinstance(raw, dict):
            # Expected shape: { forwards: [...], defensemen: [...], goalies: [...], ... }
            for group_key in ["forwards", "defensemen", "goalies", "roster", "players"]:
                group = raw.get(group_key, [])
                if isinstance(group, list):
                    for p in group:
                        players.append(self._extract_player_from_nhl_roster(p))
        elif source == "rosterSpots" and isinstance(raw, list):
            for spot in raw:
                # Filter by requested team to avoid including both teams' players
                if spot.get("teamId") == self._get_team_id_from_abbrev(team):
                    players.append(self._extract_player_from_roster_spot(spot))
        else:
            players = []

        return {
            "team": team,
            "season": season,
            "scope": scope,
            "players": players,
            "last_updated": datetime.utcnow().isoformat(),
            "source": source
        }

    def _extract_player_from_nhl_roster(self, p: Dict[str, Any]) -> Dict[str, Any]:
        # Extract first and last names from nested dict structure
        first_name = ""
        last_name = ""
        
        if isinstance(p.get("firstName"), dict):
            first_name = p["firstName"].get("default", "")
        elif p.get("firstName"):
            first_name = str(p.get("firstName"))
        
        if isinstance(p.get("lastName"), dict):
            last_name = p["lastName"].get("default", "")
        elif p.get("lastName"):
            last_name = str(p.get("lastName"))
        
        full_name = f"{first_name} {last_name}".strip()
        
        # Fallback to "name" field if it exists and full_name is empty
        if not full_name and p.get("name"):
            name_obj = p.get("name")
            if isinstance(name_obj, dict):
                full_name = name_obj.get("default", "")
            else:
                full_name = str(name_obj)

        return {
            "nhl_player_id": p.get("id") or p.get("playerId") or p.get("playerID"),
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "sweater": p.get("sweaterNumber") or p.get("sweater") or p.get("number"),
            "position": p.get("positionCode") or p.get("position"),
            "status": p.get("status", "active")
        }

    def _extract_player_from_roster_spot(self, spot: Dict[str, Any]) -> Dict[str, Any]:
        # Try different name field formats
        name_first = None
        name_last = None

        # Format 1: nested dict with "default" key
        if isinstance(spot.get("firstName"), dict):
            name_first = spot["firstName"].get("default")
        else:
            name_first = spot.get("firstName")

        if isinstance(spot.get("lastName"), dict):
            name_last = spot["lastName"].get("default")
        else:
            name_last = spot.get("lastName")

        # Format 2: direct name field
        if not name_first and spot.get("name"):
            full_name = spot.get("name")
            if isinstance(full_name, dict):
                full_name = full_name.get("default", str(full_name))
            # Try to split into first/last
            if " " in full_name:
                parts = full_name.split(" ", 1)
                name_first = parts[0]
                name_last = parts[1]

        player_id = spot.get("playerId") or spot.get("player_id") or spot.get("id")

        return {
            "nhl_player_id": player_id,
            "full_name": f"{name_first or ''} {name_last or ''}".strip() or spot.get("name", ""),
            "first_name": name_first,
            "last_name": name_last,
            "sweater": spot.get("sweaterNumber") or spot.get("sweater"),
            "position": spot.get("positionCode") or spot.get("position"),
            "status": "active"
        }


    def _get_team_id_from_abbrev(self, abbrev: str) -> Optional[int]:
        """Map team abbreviation to NHL team ID."""
        # NHL team ID mapping (this is a subset - add more as needed)
        team_id_map = {
            "ANA": 24, "ARI": 53, "BOS": 6, "BUF": 7, "CAR": 12, "CBJ": 29,
            "CGY": 20, "CHI": 16, "COL": 21, "DAL": 25, "DET": 17, "EDM": 22,
            "FLA": 13, "LAK": 26, "MIN": 30, "MTL": 8, "NJD": 1, "NSH": 18,
            "NYI": 2, "NYR": 3, "OTT": 9, "PHI": 4, "PIT": 5, "SEA": 55,
            "SJS": 28, "STL": 19, "TBL": 14, "TOR": 10, "UTA": 59, "VAN": 23,
            "VGK": 54, "WPG": 52, "WSH": 15
        }
        return team_id_map.get(abbrev.upper())

    def _cache_key(self, team: str, season: str, scope: str) -> str:
        return f"roster:{team.upper()}:{season}:{scope}"


@dataclass
class CachedGameData:
    data: Dict[str, Any]
    expires_at: datetime


class NHLLiveGameClient:
    """
    Lightweight async client for NHL live game data with intelligent caching.
    
    Fetches real-time game data from NHL API with TTL-based caching:
    - Live games: 10-15 second cache
    - Future games: 5 minute cache
    - Final games: 1 hour cache (stats rarely change)
    """
    
    def __init__(self):
        self._cache: Dict[str, CachedGameData] = {}
        self._live_game_ttl = 12  # 12 seconds for live games
        self._future_game_ttl = 300  # 5 minutes for future games
        self._final_game_ttl = 3600  # 1 hour for final games
        # Longer TTL for season schedules (they rarely change after release)
        self._season_schedule_ttl = 6 * 3600  # 6 hours
    
    async def get_game_data(
        self,
        game_id: Optional[int] = None,
        team: Optional[str] = None,
        date: Optional[str] = None,
        tz_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get game data by game ID or find game by team and date.
        
        Args:
            game_id: Specific NHL game ID (e.g., 2025020123)
            team: Team abbreviation (e.g., "MTL", "TOR")
            date: Date in YYYY-MM-DD format
            
        Returns:
            Contract dict with keys: status, game?, candidates?, diagnostics?, payload?
        """
        # If game_id provided, fetch directly
        if game_id:
            payload = await self._fetch_game_by_id(game_id)
            status = "ok" if isinstance(payload, dict) and not payload.get("error") else "api_error"
            game = None
            try:
                g = payload.get("data") or {}
                home = (g.get("homeTeam", {}) or {}).get("abbrev")
                away = (g.get("awayTeam", {}) or {}).get("abbrev")
                game_state = g.get("gameState") or payload.get("game_state")
                game = {"id": game_id, "home": home, "away": away, "state": game_state}
            except Exception:
                pass
            return {"status": status, "game": game, "payload": payload}
        
        # Team-only or with date: use robust finder
        if team:
            return await self.find_game_for_team(team=team, tz_name=tz_name, date=date)
        
        return {"status": "invalid_args", "diagnostics": "Provide game_id or team (and optional date)."}

    async def find_game_for_team(
        self,
        team: str,
        tz_name: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find a game for a team with timezone-aware date probing and return a status contract.

        Returns dict:
          - status: ok | no_game | ambiguous | api_error
          - game: {id, state, period, clock, home, away, date?} when status=ok
          - candidates: list of similar dicts (all matches across probed dates)
          - diagnostics: optional message
          - payload: optional detailed game payload when available
        """
        team_upper = str(team).upper()
        # Build date candidates
        date_candidates: List[str] = []
        if date:
            date_candidates = [date]
        else:
            try:
                # Timezone-aware 'today'
                if tz_name and ZoneInfo is not None:
                    tz = ZoneInfo(tz_name)
                    now_tz = datetime.now(tz)
                    local_date = now_tz.date()
                else:
                    local_date = datetime.now().date()
                utc_date = datetime.now(timezone.utc).date()
                date_candidates = [
                    local_date.isoformat(),
                    utc_date.isoformat(),
                    (local_date - timedelta(days=1)).isoformat(),
                    (local_date + timedelta(days=1)).isoformat(),
                ]
            except Exception:
                d = datetime.utcnow().date()
                date_candidates = [d.isoformat(), (d - timedelta(days=1)).isoformat(), (d + timedelta(days=1)).isoformat()]
        # Deduplicate preserve order
        seen: set[str] = set()
        unique_dates: List[str] = []
        for d in date_candidates:
            if d not in seen:
                seen.add(d)
                unique_dates.append(d)

        def _abbr(obj: Dict[str, Any]) -> str:
            try:
                return (obj or {}).get("abbrev") or (obj or {}).get("teamAbbrev") or ""
            except Exception:
                return ""

        def _extract_summary(g: Dict[str, Any], day: str) -> Dict[str, Any]:
            try:
                home = _abbr(g.get("homeTeam") or g.get("home") or {})
                away = _abbr(g.get("awayTeam") or g.get("away") or {})
                return {
                    "id": g.get("id") or g.get("gameId") or g.get("gamePk"),
                    "state": g.get("gameState") or g.get("status"),
                    "period": (g.get("periodDescriptor") or {}).get("number") or g.get("period"),
                    "clock": g.get("clock") or g.get("gameClock"),
                    "home": home,
                    "away": away,
                    "date": day,
                }
            except Exception:
                return {"id": None, "state": None, "home": None, "away": None, "date": day}

        candidates: List[Dict[str, Any]] = []
        try:
            for day in unique_dates:
                sb = await self.get_todays_games(day)
                games = sb.get("games", []) if isinstance(sb, dict) else []
                for g in games:
                    home = _abbr(g.get("homeTeam") or g.get("home") or {})
                    away = _abbr(g.get("awayTeam") or g.get("away") or {})
                    if home == team_upper or away == team_upper:
                        candidates.append(_extract_summary(g, day))
        except Exception as e:
            return {"status": "api_error", "diagnostics": f"score fetch failed: {e}"}

        if not candidates:
            return {"status": "no_game", "candidates": [], "diagnostics": f"No game found for {team_upper} across {unique_dates}"}

        # Choose best candidate: prefer LIVE/CRIT; else first FUT/PRE/SCHEDULED; else first
        def _rank(c: Dict[str, Any]) -> int:
            s = str(c.get("state") or "").upper()
            if s in ("LIVE", "CRIT"):
                return 0
            if s in ("FUT", "PRE", "SCHEDULED"):
                return 1
            if s in ("FINAL", "OFF"):
                return 2
            return 3
        candidates.sort(key=_rank)
        best = candidates[0]

        # Fetch detailed payload for the best candidate id if present
        payload = None
        if best.get("id"):
            payload = await self._fetch_game_by_id(best["id"])
        return {"status": "ok", "game": best, "candidates": candidates, "payload": payload}
        
        return {"error": "Must provide either game_id or team (optionally with date)"}
    
    async def get_todays_games(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all games for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            All games scheduled for that date
        """
        if not date:
            date = datetime.utcnow().date().isoformat()
        else:
            # Normalize common natural tokens and loose formats
            try:
                d = str(date).strip().lower()
                if d in {"today", "tonight", "now"}:
                    date = datetime.utcnow().date().isoformat()
                elif d in {"tomorrow", "tmr", "tommorow"}:
                    date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
                elif d in {"yesterday", "yday"}:
                    date = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
                else:
                    # Accept YYYY/MM/DD and other common separators
                    s = d.replace("/", "-")
                    # If it already looks like YYYY-MM-DD, keep it; otherwise try to parse few formats
                    def _looks_iso(x: str) -> bool:
                        return len(x) == 10 and x[4] == "-" and x[7] == "-"
                    if not _looks_iso(s):
                        from datetime import datetime as _dt
                        for fmt in ("%Y-%m-%d", "%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y", "%b %d %Y", "%B %d %Y"):
                            try:
                                date = _dt.strptime(s, fmt).date().isoformat()
                                break
                            except Exception:
                                continue
                        # If none matched and it's not ISO, fallback to UTC today
                        if not _looks_iso(str(date)):
                            date = datetime.utcnow().date().isoformat()
            except Exception:
                date = datetime.utcnow().date().isoformat()
        
        cache_key = f"schedule:{date}"
        cached = self._cache.get(cache_key)
        
        if cached and cached.expires_at > datetime.utcnow():
            return cached.data
        
        try:
            url = f"https://api-web.nhle.com/v1/score/{date}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Cache for 5 minutes (games don't appear/disappear frequently)
                    self._cache[cache_key] = CachedGameData(
                        data=data,
                        expires_at=datetime.utcnow() + timedelta(seconds=300)
                    )
                    
                    return data
                else:
                    logger.warning(f"Score endpoint returned {resp.status_code} for {date}")
                    return {"error": f"API returned status {resp.status_code}", "date": date}
        
        except Exception as e:
            logger.error(f"Failed to fetch games for {date}: {e}")
            return {"error": str(e), "date": date}

    async def get_recent_games(self, team: str, limit: int = 5, max_days_back: int = 30) -> Dict[str, Any]:
        """Search backward from today to find a team's most recent completed games.
        
        Args:
            team: Team abbreviation (e.g., "BOS", "MTL", "TOR")
            limit: Number of completed games to return (default 5)
            max_days_back: Maximum days to search backward (default 30)
        
        Returns:
            Dict with keys:
                - team: str
                - games_found: int
                - games: List[Dict] with date, opponent, home/away, score, game_state
        """
        team_abbr = team.upper()
        found_games = []
        current_date = datetime.utcnow().date()
        
        try:
            for days_ago in range(max_days_back + 1):
                if len(found_games) >= limit:
                    break
                
                search_date = current_date - timedelta(days=days_ago)
                date_str = search_date.isoformat()
                
                # Fetch games for this date
                day_data = await self.get_todays_games(date=date_str)
                games = day_data.get("games", [])
                
                if not games or isinstance(games, str):
                    continue
                
                # Find completed games for this team
                for g in games:
                    if len(found_games) >= limit:
                        break
                    
                    try:
                        home_team = (g.get("homeTeam", {}) or {}).get("abbrev", "")
                        away_team = (g.get("awayTeam", {}) or {}).get("abbrev", "")
                        game_state = g.get("gameState", "")
                        
                        # Check if this game involves our team and is completed
                        if team_abbr not in [home_team, away_team]:
                            continue
                        
                        # Only include completed games (FINAL, OFF)
                        if game_state not in ["FINAL", "OFF"]:
                            continue
                        
                        # Extract score
                        home_score = (g.get("homeTeam", {}) or {}).get("score", 0)
                        away_score = (g.get("awayTeam", {}) or {}).get("score", 0)
                        
                        # Determine if team won/lost
                        is_home = (team_abbr == home_team)
                        team_score = home_score if is_home else away_score
                        opp_score = away_score if is_home else home_score
                        opponent = away_team if is_home else home_team
                        location = "HOME" if is_home else "AWAY"
                        
                        result = "W" if team_score > opp_score else ("L" if team_score < opp_score else "OT/SO")
                        
                        found_games.append({
                            "date": date_str,
                            "opponent": opponent,
                            "location": location,
                            "team_score": team_score,
                            "opp_score": opp_score,
                            "result": result,
                            "game_state": game_state,
                            "game_id": g.get("id"),
                        })
                    
                    except Exception as e:
                        logger.warning(f"Error parsing game data: {e}")
                        continue
            
            return {
                "success": True,
                "team": team_abbr,
                "games_found": len(found_games),
                "games": found_games,
            }
        
        except Exception as e:
            logger.error(f"Failed to fetch recent games for {team_abbr}: {e}")
            return {
                "success": False,
                "error": str(e),
                "team": team_abbr,
                "games_found": 0,
                "games": [],
            }

    async def get_team_season_schedule(self, team: str, season: Optional[str] = None) -> Dict[str, Any]:
        """Fetch full season schedule for a team using club-schedule-season endpoint.

        Args:
            team: Team abbreviation (e.g., "MTL")
            season: "YYYY-YYYY" or compact "YYYYYYYY"; if None, infer current NHL season

        Returns:
            Dict with keys: team, season, games: [ { id, date, home, away, game_state, start_time_utc } ]
        """
        try:
            team_abbr = team.upper()
            # Normalize season format
            if not season or season == "current":
                now = datetime.utcnow()
                yr = now.year
                if now.month >= 10:
                    season_compact = f"{yr}{yr+1}"
                else:
                    season_compact = f"{yr-1}{yr}"
            else:
                s = str(season).replace("/", "-")
                if "-" in s:
                    parts = s.split("-")
                    try:
                        season_compact = f"{int(parts[0])}{int(parts[1])}"
                    except Exception:
                        season_compact = s.replace("-", "")
                else:
                    season_compact = s

            cache_key = f"team_schedule:{team_abbr}:{season_compact}"
            cached = self._cache.get(cache_key)
            if cached and cached.expires_at > datetime.utcnow():
                return cached.data

            url = f"https://api-web.nhle.com/v1/club-schedule-season/{team_abbr}/{season_compact}"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                if resp.status_code != 200:
                    logger.warning(f"club-schedule-season returned {resp.status_code} for {team_abbr}/{season_compact}")
                    return {"error": f"status {resp.status_code}", "team": team_abbr, "season": season_compact}
                data = resp.json()

            # Extract and normalize games
            raw_games = []
            try:
                raw_games = data.get("games", []) if isinstance(data, dict) else []
            except Exception:
                raw_games = []

            games: list[dict] = []
            for g in raw_games:
                try:
                    # Prefer canonical keys but be flexible
                    home_team_obj = (g.get("homeTeam", {}) or {})
                    away_team_obj = (g.get("awayTeam", {}) or {})
                    home = home_team_obj.get("abbrev") or (g.get("home", {}) or {}).get("abbrev")
                    away = away_team_obj.get("abbrev") or (g.get("away", {}) or {}).get("abbrev")
                    start_utc = g.get("startTimeUTC") or g.get("startTime")
                    game_date = g.get("gameDate") or g.get("date") or (start_utc[:10] if isinstance(start_utc, str) else None)
                    game_type = g.get("gameType") or g.get("game_type")
                    # Scores if present (final or live)
                    def _to_int(x):
                        try:
                            return int(x) if x is not None and str(x) != '' else None
                        except Exception:
                            return None
                    home_score = _to_int(home_team_obj.get("score") or g.get("homeScore") or g.get("home_goals"))
                    away_score = _to_int(away_team_obj.get("score") or g.get("awayScore") or g.get("away_goals"))
                    games.append({
                        "id": g.get("id") or g.get("gameId") or g.get("gamePk"),
                        "date": game_date,
                        "home": home,
                        "away": away,
                        "game_state": g.get("gameState") or g.get("status"),
                        "game_schedule_state": g.get("gameScheduleState") or g.get("scheduleState"),
                        "start_time_utc": start_utc,
                        "game_type": game_type,
                        "home_score": home_score,
                        "away_score": away_score
                    })
                except Exception:
                    continue

            result = {"team": team_abbr, "season": season_compact, "games": games, "source": "club-schedule-season"}
            self._cache[cache_key] = CachedGameData(data=result, expires_at=datetime.utcnow() + timedelta(seconds=self._season_schedule_ttl))
            return result
        except Exception as e:
            logger.error(f"Failed to fetch team season schedule for {team}/{season}: {e}")
            return {"error": str(e), "team": team, "season": season}
    
    async def _find_and_fetch_game(self, team: str, date: str) -> Dict[str, Any]:
        """Find game involving team on date, then fetch full data."""
        schedule_data = await self.get_todays_games(date)
        
        if "error" in schedule_data:
            return schedule_data
        
        games = schedule_data.get("games", [])
        team_upper = team.upper()
        
        # Find game involving this team
        for game in games:
            # Robust abbreviation extraction across shapes
            def _abbr(obj):
                try:
                    if not isinstance(obj, dict):
                        return ""
                    return obj.get("abbrev") or obj.get("teamAbbrev") or ""
                except Exception:
                    return ""
            home_team = _abbr(game.get("homeTeam")) or _abbr(game.get("home"))
            away_team = _abbr(game.get("awayTeam")) or _abbr(game.get("away"))
            
            if home_team == team_upper or away_team == team_upper:
                game_id = game.get("id")
                if game_id:
                    # Fetch detailed game data
                    return await self._fetch_game_by_id(game_id)
        
        return {
            "error": f"No game found for {team} on {date}",
            "team": team,
            "date": date,
            "games_on_date": len(games)
        }
    
    async def _fetch_game_by_id(self, game_id: int) -> Dict[str, Any]:
        """Fetch detailed game data for specific game ID."""
        cache_key = f"game:{game_id}"
        cached = self._cache.get(cache_key)
        
        if cached and cached.expires_at > datetime.utcnow():
            return cached.data
        
        try:
            # Fetch from score endpoint first (lightest, has most info)
            date = self._extract_date_from_game_id(game_id)
            schedule_data = await self.get_todays_games(date)
            
            games = schedule_data.get("games", [])
            game_data = None
            
            for game in games:
                if game.get("id") == game_id:
                    game_data = game
                    break
            
            if not game_data:
                return {"error": f"Game {game_id} not found", "game_id": game_id}
            
            # Enrich with additional data if needed
            game_state = game_data.get("gameState", "")
            
            # Determine TTL based on game state
            if game_state == "LIVE" or game_state == "CRIT":
                ttl = self._live_game_ttl
            elif game_state == "FINAL" or game_state == "OFF":
                ttl = self._final_game_ttl
            else:
                ttl = self._future_game_ttl
            
            # Cache result
            result = {
                "source": "nhl_api",
                "game_id": game_id,
                "game_state": game_state,
                "data": game_data,
                "cached_until": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat()
            }
            
            self._cache[cache_key] = CachedGameData(
                data=result,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl)
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to fetch game {game_id}: {e}")
            return {"error": str(e), "game_id": game_id}
    
    def _extract_date_from_game_id(self, game_id: int) -> str:
        """
        Extract approximate date from game ID.
        NHL game IDs are structured as: SSSSTTGGGG
        - SSSS: Season (e.g., 2025 for 2025-26)
        - TT: Game type (01=preseason, 02=regular, 03=playoffs)
        - GGGG: Game number
        
        Since we can't get exact date from ID, we'll search recent dates.
        """
        # For now, search today +/- 1 day
        today = datetime.utcnow().date()
        return today.isoformat()
    
    async def get_boxscore(self, game_id: int) -> Dict[str, Any]:
        """
        Get detailed boxscore with player statistics.
        
        Args:
            game_id: NHL game ID
            
        Returns:
            Boxscore data with player stats, TOI, shots, etc.
        """
        cache_key = f"boxscore:{game_id}"
        cached = self._cache.get(cache_key)
        
        if cached and cached.expires_at > datetime.utcnow():
            return cached.data
        
        try:
            url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Cache for 15 seconds (boxscore updates frequently during games)
                    self._cache[cache_key] = CachedGameData(
                        data={"source": "boxscore", "game_id": game_id, "data": data},
                        expires_at=datetime.utcnow() + timedelta(seconds=15)
                    )
                    
                    return {"source": "boxscore", "game_id": game_id, "data": data}
                else:
                    return {"error": f"Boxscore API returned {resp.status_code}", "game_id": game_id}
        
        except Exception as e:
            logger.error(f"Failed to fetch boxscore for {game_id}: {e}")
            return {"error": str(e), "game_id": game_id}
    
    async def get_play_by_play(self, game_id: int) -> Dict[str, Any]:
        """
        Get play-by-play data with event details and coordinates.
        
        Args:
            game_id: NHL game ID
            
        Returns:
            Play-by-play events with coordinates, players, and game flow
        """
        cache_key = f"pbp:{game_id}"
        cached = self._cache.get(cache_key)
        
        if cached and cached.expires_at > datetime.utcnow():
            return cached.data
        
        try:
            url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Cache for 15 seconds
                    self._cache[cache_key] = CachedGameData(
                        data={"source": "play_by_play", "game_id": game_id, "data": data},
                        expires_at=datetime.utcnow() + timedelta(seconds=15)
                    )
                    
                    return {"source": "play_by_play", "game_id": game_id, "data": data}
                else:
                    return {"error": f"PBP API returned {resp.status_code}", "game_id": game_id}
        
        except Exception as e:
            logger.error(f"Failed to fetch play-by-play for {game_id}: {e}")
            return {"error": str(e), "game_id": game_id}
