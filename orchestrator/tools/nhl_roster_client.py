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
from datetime import datetime, timedelta
import asyncio
import logging
from pathlib import Path
import json

import csv
import httpx

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
        self._player_roster_map: Optional[Dict[str, Dict[str, Any]]] = None

        # Resolve repo root to load local data consistently
        from orchestrator.config.settings import settings
        # Use processed data path from settings
        self._data_root = Path(settings.parquet.data_directory)
        # NHL rosters Parquet path
        self._rosters_parquet = self._data_root / "rosters" / "nhl_rosters_latest.parquet"

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
        season_formats = [season_str]
        if season_str == "2025-2026":
            season_formats.extend(["20242025", "2025", "current"])

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
        """Normalize payload into a consistent roster dict and enrich IDs/names."""
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

        # Enrich with roster Parquet data (team, position, jersey number)
        roster_map = self._load_roster_map()
        for p in players:
            pid = str(p.get("nhl_player_id", ""))
            if pid and pid in roster_map:
                # Use roster data for enrichment - more detailed and accurate
                roster_data = roster_map[pid]
                p["full_name"] = roster_data.get("full_name") or p.get("full_name")
                p["team_abbrev"] = roster_data.get("team_abbrev") or team
                p["sweater"] = roster_data.get("sweater") or p.get("sweater")
                p["position"] = roster_data.get("position") or p.get("position")
                p["status"] = roster_data.get("status") or p.get("status")

        return {
            "team": team,
            "season": season,
            "scope": scope,
            "players": players,
            "last_updated": datetime.utcnow().isoformat(),
            "source": source
        }

    def _extract_player_from_nhl_roster(self, p: Dict[str, Any]) -> Dict[str, Any]:
        # Flexible extraction as NHL payloads vary by endpoint
        name = p.get("name") or {}
        if isinstance(name, dict):
            first = name.get("first", name.get("default", ""))
            last = name.get("last", "")
            full_name = f"{first} {last}".strip()
        else:
            full_name = str(name)

        return {
            "nhl_player_id": p.get("id") or p.get("playerId") or p.get("playerID"),
            "full_name": full_name,
            "first_name": p.get("firstName", {}).get("default") if isinstance(p.get("firstName"), dict) else p.get("firstName"),
            "last_name": p.get("lastName", {}).get("default") if isinstance(p.get("lastName"), dict) else p.get("lastName"),
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

    def _load_roster_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Load player roster data from nhl_rosters_latest.parquet.
        Returns mapping of nhl_player_id -> player details (name, team, position, jersey, etc.)
        """
        if self._player_roster_map is not None:
            return self._player_roster_map

        mapping: Dict[str, Dict[str, Any]] = {}
        try:
            if self._rosters_parquet.exists():
                import pandas as pd
                df = pd.read_parquet(self._rosters_parquet)
                
                # Create mapping from NHL player ID to roster details
                for _, row in df.iterrows():
                    nhl_id = str(row.get("nhl_player_id", "")).strip()
                    if not nhl_id:
                        continue
                    
                    mapping[nhl_id] = {
                        "full_name": row.get("full_name", ""),
                        "first_name": row.get("first_name", ""),
                        "last_name": row.get("last_name", ""),
                        "team_abbrev": row.get("team_abbrev", ""),
                        "position": row.get("position", ""),
                        "sweater": row.get("sweater"),
                        "status": row.get("status", "active"),
                        "sync_date": row.get("sync_date", ""),
                        "season": row.get("season", "")
                    }
                logger.info(f"Loaded {len(mapping)} players from nhl_rosters_latest.parquet")
            else:
                logger.warning(f"Roster parquet not found at {self._rosters_parquet}")
        except Exception as e:
            logger.warning(f"Failed to load nhl_rosters_latest.parquet: {e}")

        self._player_roster_map = mapping
        return self._player_roster_map

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
    
    async def get_game_data(
        self,
        game_id: Optional[int] = None,
        team: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get game data by game ID or find game by team and date.
        
        Args:
            game_id: Specific NHL game ID (e.g., 2025020123)
            team: Team abbreviation (e.g., "MTL", "TOR")
            date: Date in YYYY-MM-DD format
            
        Returns:
            Game data including score, period, clock, situation, players
        """
        # If game_id provided, fetch directly
        if game_id:
            return await self._fetch_game_by_id(game_id)
        
        # If team + date provided, find game
        if team and date:
            return await self._find_and_fetch_game(team, date)
        
        # If only team provided, find today's game
        if team:
            today = datetime.utcnow().date().isoformat()
            return await self._find_and_fetch_game(team, today)
        
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
    
    async def _find_and_fetch_game(self, team: str, date: str) -> Dict[str, Any]:
        """Find game involving team on date, then fetch full data."""
        schedule_data = await self.get_todays_games(date)
        
        if "error" in schedule_data:
            return schedule_data
        
        games = schedule_data.get("games", [])
        team_upper = team.upper()
        
        # Find game involving this team
        for game in games:
            home_team = game.get("homeTeam", {}).get("abbrev", "")
            away_team = game.get("awayTeam", {}).get("abbrev", "")
            
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


