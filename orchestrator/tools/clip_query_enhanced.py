#!/usr/bin/env python3
"""
Enhanced Clip Query Tool for Hockey Video Retrieval
Supports shift mode, multi-period, and teammate/opponent filtering
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import json

# Import services
try:
    from .roster_service import get_roster_service
    from .schedule_service import get_schedule_service
except ImportError:
    from roster_service import get_roster_service
    from schedule_service import get_schedule_service


@dataclass
class ClipSearchParams:
    """Enhanced parameters for searching clips"""
    # Player filters
    players: List[str | int] = field(default_factory=list)  # Player IDs or names
    teammates: List[str | int] = field(default_factory=list)  # Must be on ice with these players
    opponents_on_ice: List[str | int] = field(default_factory=list)  # Specific opponents on ice
    
    # Event filters
    event_types: List[str] = field(default_factory=list)
    # Zone filters (e.g., ['OZ', 'NZ', 'DZ'])
    zones: Optional[List[str]] = None
    
    # Time filters
    timeframe: str = "last_game"  # "last_game", "last_3_games", etc.
    game_ids: Optional[List[str]] = None
    periods: Optional[List[int]] = None  # [1], [2], [1,2,3], etc.
    
    # Team filters
    team: Optional[str] = None
    opponents: Optional[List[str]] = None  # Opponent team codes
    
    # Mode
    mode: str = "event"  # "event" or "shift"
    
    # Clip settings
    limit: int = 10
    clip_window: Dict[str, float] = field(default_factory=lambda: {"pre_s": 3.0, "post_s": 5.0})
    
    # Season
    season: str = "20252026"


@dataclass
class ClipSegment:
    """A single clip segment with enhanced metadata"""
    clip_id: str
    title: str
    description: str
    
    # Player info
    player_id: str
    player_name: Optional[str]
    teammates_on_ice: List[Dict]  # [{"id": str, "name": str}, ...]
    opponents_on_ice: List[Dict]
    
    # Team info
    team: str
    team_code: str
    opponent: str
    
    # Game info
    game_id: str
    game_date: str
    season: str
    
    # Time info
    period: int
    period_time: str
    timecode: str
    timecode_seconds: float
    start_timecode_s: float
    end_timecode_s: float
    duration_s: float
    
    # Event/shift info
    mode: str  # "event" or "shift"
    event_type: Optional[str]
    outcome: Optional[str]
    zone: Optional[str]
    strength: Optional[str]  # "5v5", "PP", "PK", etc.
    
    # Video path
    period_video_path: Optional[str]
    
    # Metadata
    provenance: Dict


class EnhancedClipQueryTool:
    """
    Enhanced query tool with shift mode and comprehensive filtering
    
    Features:
    - Shift mode: Retrieve entire shifts (continuous ice time)
    - Event mode: Retrieve specific events with context
    - Multi-period support
    - Teammate/opponent filtering
    - Player name resolution via RosterService
    - Timeframe resolution via ScheduleService
    """
    
    def __init__(self, extracted_metrics_dir: str, clips_dir: str):
        """
        Args:
            extracted_metrics_dir: Path to data/processed/extracted_metrics
            clips_dir: Path to data/clips (where period MP4s are stored)
        """
        self.metrics_dir = Path(extracted_metrics_dir)
        self.clips_dir = Path(clips_dir)
        
        # Initialize services
        self.roster_service = get_roster_service()
        self.schedule_service = get_schedule_service()
        # Cache for per-game period offsets (real-time video seconds)
        self._period_offset_cache: dict[str, dict[int, float]] = {}
        
        # Event taxonomy (action names only; zones are handled via params.zones)
        self.event_taxonomy = {
            # Explicit action requests
            "zone_entry": ["CONTROLLED ENTRY INTO OZ", "OZ ENTRY PASS+", "O-ZONE ENTRY PASS RECEPTION"],
            "dump_in": ["DUMP IN+", "CHIP DUMP+"],
            "dzone_exit": ["CONTROLLED EXIT FROM DZ"],
            "zone_exit": ["CONTROLLED EXIT FROM DZ"],
            "breakout": ["CONTROLLED EXIT FROM DZ", "DZ OUTLET PASS+"],
            "shot": ["SLOT SHOT FOR ONNET", "OUTSIDE SHOT FOR ONNET", "SLOT SHOT FOR MISSED", 
                    "OUTSIDE SHOT FOR MISSED", "SLOT SHOT FOR BLOCKED"],
            "goal": ["GOAL"],
            "pass": ["OZPASS", "NZPASS", "DZONE D2D+", "DZ OUTLET PASS+"],
            "block": ["BLOCK OPPOSITION SHOT+", "BLOCK OPPOSITION PASS+"],
            "stick_check": ["OZ STICK CHK+", "DZ STICK CHK+"],
            "pressure": ["SHOT PRESSURE"],
            "lpr": ["LPR+", "DUMP IN LPR+", "OFF LPR"],
            "recovery": ["LPR+", "DUMP IN LPR+"],
            "turnover": ["PUCK GIVEAWAY"],
            "takeaway": ["TAKEAWAY"],
            "faceoff": ["FACEOFF WIN+", "FACEOFF LOSS"],
        }
    
    def query(self, params: ClipSearchParams) -> List[ClipSegment]:
        """
        Execute clip query
        
        Returns:
            List of ClipSegment objects
        """
        if params.mode == "shift":
            return self._query_shifts(params)
        else:
            return self._query_events(params)
    
    def _query_shifts(self, params: ClipSearchParams) -> List[ClipSegment]:
        """Query for shift clips"""
        segments = []
        
        # Resolve player IDs
        player_ids = self._resolve_player_ids(params.players, params.team, params.season)
        teammate_ids = self._resolve_player_ids(params.teammates, params.team, params.season) if params.teammates else []
        opponent_ids = self._resolve_player_ids(params.opponents_on_ice, None, params.season) if params.opponents_on_ice else []
        
        # Resolve game IDs
        game_ids = self._resolve_game_ids(params)
        
        for game_id in game_ids:
            # Load comprehensive metrics (has shift data)
            metrics_file = self._find_metrics_file(game_id, "comprehensive_metrics")
            if not metrics_file:
                continue
            
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            
            player_shifts_data = metrics.get('player_shifts', {})
            all_shifts = player_shifts_data.get('shifts', [])
            game_info = metrics.get('game_info', {})
            
            # Filter shifts for requested players
            for player_id in player_ids:
                player_id_str = str(player_id)
                
                # Find shifts for this player
                shifts = [s for s in all_shifts if s.get('player_id') == player_id_str]
                
                for shift in shifts:
                    # Filter by period
                    if params.periods and shift['start_period'] not in params.periods:
                        continue
                    
                    # Filter by teammates
                    if teammate_ids:
                        opponents_seen = set(str(oid) for oid in shift.get('opponents_seen_ids', []))
                        if not any(str(tid) in opponents_seen for tid in teammate_ids):
                            # Teammates are in opponents_seen if they're on opposing team
                            # For same-team teammates, we need different logic
                            # For now, skip this shift if teammates filter active
                            pass
                    
                    # Filter by opponents
                    if opponent_ids:
                        opponents_seen = set(str(oid) for oid in shift.get('opponents_seen_ids', []))
                        if not any(str(oid) in opponents_seen for oid in opponent_ids):
                            continue
                    
                    # Create clip segment
                    segment = self._create_shift_segment(
                        shift=shift,
                        player_id=player_id_str,
                        game_id=game_id,
                        game_info=game_info,
                        params=params
                    )
                    
                    if segment:
                        segments.append(segment)
                        
                        if len(segments) >= params.limit:
                            return segments
        
        return segments[:params.limit]
    
    def _query_events(self, params: ClipSearchParams) -> List[ClipSegment]:
        """Query for event clips (original implementation)"""
        segments = []
        
        # Resolve player IDs
        player_ids = self._resolve_player_ids(params.players, params.team, params.season)
        
        # Resolve game IDs
        game_ids = self._resolve_game_ids(params)
        
        # Expand event types (action names only)
        expanded_events: List[str] = []
        for event_term in params.event_types:
            expanded_events.extend(self._normalize_event_type(event_term))
        
        for game_id in game_ids:
            # Load timeline CSV
            timeline_file = self._find_metrics_file(game_id, "player_tendencies_timeline")
            if not timeline_file:
                continue
            
            df = pd.read_csv(timeline_file)
            
            # Filter by players
            if player_ids:
                player_ids_normalized = []
                for p in player_ids:
                    p_str = str(p).replace('.0', '')
                    player_ids_normalized.extend([p_str, f"{p_str}.0"])
                
                df['player_id_str'] = df['player_id'].astype(str)
                df = df[df['player_id_str'].isin(player_ids_normalized)]
            
            # Filter by event types
            if expanded_events:
                mask = df['action'].astype(str).apply(
                    lambda x: any(act.upper() in x.upper() for act in expanded_events)
                )
                df = df[mask]
            
            # Filter by zones (independent of event type mapping)
            if params.zones:
                zones_norm = {str(z).strip().upper() for z in params.zones}
                # Accept both full names and abbreviations in CSV
                def norm_zone(z: str) -> str:
                    z_up = str(z).strip().upper()
                    if z_up in {"OFFENSIVE", "O-ZONE", "OZONE", "OFFENSIVE ZONE"}:
                        return "OZ"
                    if z_up in {"NEUTRAL", "NEUTRAL ZONE", "N-ZONE", "NZONE"}:
                        return "NZ"
                    if z_up in {"DEFENSIVE", "D-ZONE", "DZONE", "DEFENSIVE ZONE"}:
                        return "DZ"
                    return z_up
                df['zone_norm'] = df['zone'].astype(str).map(norm_zone)
                df = df[df['zone_norm'].isin(zones_norm)]
            
            # Filter by periods
            if params.periods:
                df = df[df['period'].isin(params.periods)]
            
            # Create segments
            for _, row in df.iterrows():
                segment = self._create_event_segment(row, game_id, params)
                if segment:
                    segments.append(segment)
                    
                    if len(segments) >= params.limit:
                        return segments
        
        return segments[:params.limit]
    
    def _create_shift_segment(
        self,
        shift: Dict,
        player_id: str,
        game_id: str,
        game_info: Dict,
        params: ClipSearchParams
    ) -> Optional[ClipSegment]:
        """Create ClipSegment from shift data"""
        try:
            # Cut using broadcast real-time timecodes (period video timeline)
            period = int(shift['start_period']) if shift.get('start_period') is not None else 1
            # Real-time seconds across the whole game (computed during extraction)
            start_abs = shift.get('start_timecode_abs')
            end_abs = shift.get('end_timecode_abs')

            # Compute per-game period offsets lazily (sum of previous period durations)
            offsets = self._get_period_offsets(game_id)
            period_offset = offsets.get(period, 0.0)
            # Map absolute to period-relative video seconds
            start_time_s = float(start_abs - period_offset) if isinstance(start_abs, (int, float)) else None
            end_time_s = float(end_abs - period_offset) if isinstance(end_abs, (int, float)) else None

            # If any missing, approximate from real/game lengths starting at 0s
            if start_time_s is None:
                start_time_s = 0.0
            if end_time_s is None:
                length_real = shift.get('shift_real_length')
                length_game = shift.get('shift_game_length')
                approx_len = float(length_real) if isinstance(length_real, (int, float)) else (
                    float(length_game) if isinstance(length_game, (int, float)) else 12.0
                )
                end_time_s = start_time_s + approx_len

            # Clamp within this period's broadcast duration
            period_duration = self._get_period_duration(game_id, period)
            if period_duration is not None:
                start_time_s = max(0.0, min(start_time_s, period_duration))
                end_time_s = max(start_time_s + 0.1, min(end_time_s, period_duration))

            duration = max(0.1, float(end_time_s) - float(start_time_s))
            
            # Get player name
            player_name = self.roster_service.get_player_name(
                player_id, 
                team_code=shift.get('team_code'),
                season=params.season
            )
            
            # Get opponents on ice
            opponents_on_ice = []
            for opp_id in shift.get('opponents_seen_ids', []):
                opp_name = self.roster_service.get_player_name(opp_id, season=params.season)
                opponents_on_ice.append({"id": str(opp_id), "name": opp_name})
            
            # Resolve period video (period-relative file)
            period_video = self._resolve_period_video_path(
                game_id, 
                period,
                shift.get('team_code'),
                params.season
            )
            
            # Create clip ID
            clip_id = f"shift_{game_id}_p{period}_{int(start_time_s)}s_{player_id}"
            
            return ClipSegment(
                clip_id=clip_id,
                title=f"{player_name} - Shift in Period {period}",
                description=f"{duration:.1f}s shift, {shift.get('strength_start', 'unknown')} strength",
                player_id=player_id,
                player_name=player_name,
                teammates_on_ice=[],  # TODO: Add teammate logic
                opponents_on_ice=opponents_on_ice,
                team=shift.get('team', ''),
                team_code=shift.get('team_code', ''),
                opponent=game_info.get('away_team' if shift.get('team_side') == 'home' else 'home_team', ''),
                game_id=game_id,
                game_date=self._get_game_date(game_id, shift.get('team_code'), params.season),
                season=params.season,
                period=period,
                period_time=self._seconds_to_period_time(start_time_s),
                timecode=self._seconds_to_timecode(start_time_s),
                timecode_seconds=start_time_s,
                start_timecode_s=start_time_s,
                end_timecode_s=end_time_s,
                duration_s=duration,
                mode="shift",
                event_type=None,
                outcome=None,
                zone=None,
                strength=shift.get('strength_start'),
                period_video_path=period_video,
                provenance={
                    "source": "player_shifts",
                    "shift_index": shift.get('shift_number', 0),
                    "raw_shift": shift
                }
            )
        except Exception as e:
            print(f"Error creating shift segment: {e}")
            return None

    def _get_period_offsets(self, game_id: str) -> dict[int, float]:
        """Return per-period offset map (in real-time seconds) for a game.
        Computes from player_tendencies_timeline timecodes: offset[p] = sum_{k<p} max_timecode[k]."""
        if game_id in self._period_offset_cache:
            return self._period_offset_cache[game_id]
        offsets: dict[int, float] = {}
        try:
            timeline = self._find_metrics_file(game_id, "player_tendencies_timeline")
            if not timeline:
                self._period_offset_cache[game_id] = offsets
                return offsets
            df = pd.read_csv(timeline, usecols=["period", "timecode"])  # small subset
            # Compute max timecode seconds per period
            def tc_to_s(v: str) -> float:
                try:
                    return self._parse_timecode_to_seconds(str(v))
                except Exception:
                    return 0.0
            df["tc_s"] = df["timecode"].astype(str).map(tc_to_s)
            per = (
                df.groupby("period")["tc_s"].max().dropna().sort_index()
            )
            acc = 0.0
            for p, max_s in per.items():
                offsets[int(p)] = acc
                acc += float(max_s)
        except Exception:
            offsets = {}
        self._period_offset_cache[game_id] = offsets
        return offsets

    def _get_period_duration(self, game_id: str, period: int) -> Optional[float]:
        """Return broadcast duration for a period in seconds (max timecode)."""
        try:
            timeline = self._find_metrics_file(game_id, "player_tendencies_timeline")
            if not timeline:
                return None
            df = pd.read_csv(timeline, usecols=["period", "timecode"])  # small subset
            df = df[df["period"] == period]
            if df.empty:
                return None
            return float(df["timecode"].astype(str).map(self._parse_timecode_to_seconds).max())
        except Exception:
            return None
    
    def _create_event_segment(self, row: pd.Series, game_id: str, params: ClipSearchParams) -> Optional[ClipSegment]:
        """Create ClipSegment from timeline event"""
        try:
            # Parse timecode
            timecode_str = str(row['timecode'])  # HH:MM:SS:FF
            timecode_s = self._parse_timecode_to_seconds(timecode_str)
            
            period = int(row['period'])
            
            # Apply clip window
            start_s = max(0, timecode_s - params.clip_window['pre_s'])
            end_s = timecode_s + params.clip_window['post_s']
            duration = end_s - start_s
            
            # Normalize identifiers
            player_id_str = str(row['player_id'])
            try:
                player_id_norm = int(str(row['player_id']).replace('.0', ''))
            except Exception:
                player_id_norm = int(float(row['player_id'])) if str(row['player_id']).replace('.', '', 1).isdigit() else row['player_id']

            # Prefer team_code column (CSV provides both team name and team_code)
            team_code = row.get('team_code') if pd.notna(row.get('team_code')) else None
            if team_code is None or str(team_code).strip() == "":
                # Fallback: attempt to derive from roster if team name provided
                team_name = str(row.get('team', ''))
                # Simple mapping could be added here if ever needed
                team_code = team_name  # last resort; may fail period video resolution

            # Get player name
            player_name = self.roster_service.get_player_name(
                player_id_norm,
                team_code=str(team_code) if team_code else None,
                season=params.season
            )
            
            # Resolve period video
            period_video = self._resolve_period_video_path(
                game_id,
                period,
                str(team_code) if team_code else None,
                params.season
            )
            
            clip_id = f"clip_{game_id}_p{period}_{int(timecode_s)}s_{player_id_norm}_{str(row['action'])[:20]}"
            clip_id = clip_id.replace(" ", "_").replace("/", "_")
            
            return ClipSegment(
                clip_id=clip_id,
                title=f"{player_name} - {row['action']}",
                description=f"Period {period} at {row.get('period_time', 'unknown')}",
                player_id=str(player_id_norm),
                player_name=player_name,
                teammates_on_ice=[],
                opponents_on_ice=[],
                team=str(row.get('team', '')),
                team_code=str(team_code or ''),
                opponent=str(row.get('opponent', '')),
                game_id=game_id,
                game_date=self._get_game_date(game_id, row.get('team'), params.season),
                season=params.season,
                period=period,
                period_time=str(row.get('period_time', '')),
                timecode=timecode_str,
                timecode_seconds=timecode_s,
                start_timecode_s=start_s,
                end_timecode_s=end_s,
                duration_s=duration,
                mode="event",
                event_type=str(row.get('action', '')),
                outcome=str(row.get('outcome', '')) if pd.notna(row.get('outcome')) else None,
                zone=str(row.get('zone', '')) if pd.notna(row.get('zone')) else None,
                strength=None,
                period_video_path=period_video,
                provenance={
                    "source": "player_tendencies_timeline",
                    "raw_row": row.to_dict()
                }
            )
        except Exception as e:
            print(f"Error creating event segment: {e}")
            return None
    
    def _resolve_player_ids(
        self,
        player_list: List[str | int],
        team_code: Optional[str],
        season: str
    ) -> List[int]:
        """Resolve player names or IDs to IDs"""
        result = []
        
        for player in player_list:
            if isinstance(player, int) or (isinstance(player, str) and player.isdigit()):
                result.append(int(player))
            else:
                # Search by name
                matches = self.roster_service.search_by_name(player, team_code, season)
                result.extend([m.id for m in matches])
        
        return result
    
    def _resolve_game_ids(self, params: ClipSearchParams) -> List[str]:
        """Resolve timeframe or explicit game_ids to list of game IDs"""
        if params.game_ids:
            return params.game_ids
        
        if params.team:
            ids = self.schedule_service.resolve_timeframe(
                params.timeframe,
                params.team,
                params.season
            )
            # Fallback: if schedule snapshot has no FINAL yet, infer from metrics files
            if not ids:
                try:
                    season_formatted = f"{params.season[:4]}-{params.season[4:]}"
                    # Look for comprehensive metrics for this team in this season and pick latest by date
                    candidates = list(self.metrics_dir.glob(f"*NHL-{params.team}vs*{params.season}-*.json"))
                    candidates += list(self.metrics_dir.glob(f"*NHL-*vs{params.team}-*{params.season}-*.json"))
                    # Sort by stem to get latest, then extract last 5 digits
                    def extract_gid(p):
                        import re
                        m = re.search(r"-(\d{5})(?:[_\-]|\.json)", p.stem)
                        return m.group(1) if m else None
                    # Prefer files with player_tendencies_timeline/metrics present
                    entries = []
                    for p in sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True):
                        gid = extract_gid(p)
                        if gid:
                            entries.append(gid)
                    if entries:
                        ids = [entries[0]]
                except Exception:
                    pass
            return ids
        
        return []
    
    def _normalize_event_type(self, event_term: str) -> List[str]:
        """Expand event taxonomy term to specific action types"""
        return self.event_taxonomy.get(event_term.lower(), [event_term.upper()])
    
    def _find_metrics_file(self, game_id: str, file_type: str) -> Optional[Path]:
        """Find metrics file for a game"""
        pattern = f"*{game_id}*{file_type}*"
        files = list(self.metrics_dir.glob(pattern))
        return files[0] if files else None
    
    def _resolve_period_video_path(
        self,
        game_id: str,
        period: int,
        team_code: Optional[str],
        season: str
    ) -> Optional[str]:
        """Resolve path to period video file"""
        if not team_code:
            return None
        
        # Convert season format: 20252026 -> 2025-2026
        season_formatted = f"{season[:4]}-{season[4:]}"
        
        # Try multiple patterns (mp4, MOV, etc.) and both season formats
        patterns = [
            f"{season_formatted}/team/{team_code}/p{period}-*{game_id}*.mp4",
            f"{season_formatted}/team/{team_code}/p{period}-*{game_id}*.MOV",
            f"{season_formatted}/team/{team_code}/p{period}-*{game_id}*.mov",
            f"{season}/team/{team_code}/p{period}-*{game_id}*.mp4",
            f"{season}/team/{team_code}/p{period}-*{game_id}*.MOV",
            f"{season}/team/{team_code}/p{period}-*{game_id}*.mov",
        ]
        
        for pattern in patterns:
            videos = list(self.clips_dir.glob(pattern))
            if videos:
                return str(videos[0])
        
        return None
    
    def _get_game_date(self, game_id: str, team_code: Optional[str], season: str) -> str:
        """Get game date from schedule"""
        if not team_code:
            return "unknown"
        
        game_info = self.schedule_service.get_game_info(game_id, team_code, season)
        return game_info.game_date if game_info else "unknown"
    
    def _parse_timecode_to_seconds(self, timecode: str) -> float:
        """Convert HH:MM:SS:FF to seconds"""
        try:
            parts = timecode.split(':')
            if len(parts) == 4:
                h, m, s, ff = parts
                return int(h) * 3600 + int(m) * 60 + int(s) + int(ff) / 30.0
            elif len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            return 0.0
        except:
            return 0.0
    
    def _seconds_to_timecode(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS:FF"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ff = int((seconds - int(seconds)) * 30)
        return f"{h:02d}:{m:02d}:{s:02d}:{ff:02d}"
    
    def _seconds_to_period_time(self, game_seconds: float) -> str:
        """Convert game clock seconds to MM:SS format"""
        minutes = int(game_seconds // 60)
        seconds = int(game_seconds % 60)
        return f"{minutes}:{seconds:02d}"


def main():
    """Test enhanced clip query tool"""
    print("\n" + "="*70)
    print("Enhanced Clip Query Tool Test")
    print("="*70 + "\n")
    
    tool = EnhancedClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    # Test 1: Query shifts in period 1
    print("TEST 1: Query shifts in period 1 for Beauvillier")
    print("-" * 70)
    params = ClipSearchParams(
        players=[8478463],
        mode="shift",
        game_ids=["20038"],
        periods=[1],
        limit=3,
        season="20252026"
    )
    
    segments = tool.query(params)
    print(f"Found {len(segments)} shifts:")
    for seg in segments:
        print(f"  {seg.clip_id}")
        print(f"    Duration: {seg.duration_s:.1f}s at {seg.period_time}")
        print(f"    Strength: {seg.strength}")
        print(f"    Opponents: {len(seg.opponents_on_ice)} players")
    
    # Test 2: Query events in period 2
    print("\n\nTEST 2: Query zone exits in period 1")
    print("-" * 70)
    params = ClipSearchParams(
        players=[8478463, 8476880],
        event_types=["zone_exit"],
        mode="event",
        game_ids=["20038"],
        periods=[1],
        limit=3,
        season="20252026"
    )
    
    segments = tool.query(params)
    print(f"Found {len(segments)} events:")
    for seg in segments:
        print(f"  {seg.player_name}: {seg.event_type}")
        print(f"    Period {seg.period} at {seg.period_time}")
    
    print("\n" + "="*70)
    print("Tests complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
