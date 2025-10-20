#!/usr/bin/env python3
"""
Clip Query Tool for Hockey Video Retrieval
Maps player events to period video timestamps using extracted metrics
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import json


@dataclass
class ClipSearchParams:
    """Parameters for searching clips"""
    players: List[str]
    event_types: List[str]
    timeframe: str  # "last_game", "last_3_games", "last_5_games", "this_season", "date_range"
    date_range: Optional[Dict[str, str]] = None
    game_ids: Optional[List[str]] = None
    opponents: Optional[List[str]] = None
    team: Optional[str] = None
    limit: int = 10
    clip_window: Dict[str, float] = None  # {"pre_s": 3.0, "post_s": 5.0}
    mode: str = "event"  # "event" or "shift"
    
    def __post_init__(self):
        if self.clip_window is None:
            self.clip_window = {"pre_s": 3.0, "post_s": 5.0}


@dataclass
class ClipSegment:
    """A single clip segment with metadata"""
    clip_id: str
    title: str
    description: str
    player_id: str
    player_name: Optional[str]
    team: str
    team_code: str
    opponent: str
    game_id: str
    game_date: str
    period: int
    period_time: str
    timecode: str  # HH:MM:SS:FF
    timecode_seconds: float  # seconds since period start
    start_timecode_s: float
    end_timecode_s: float
    duration_s: float
    event_type: str
    outcome: Optional[str]
    zone: Optional[str]
    period_video_path: Optional[str]
    provenance: Dict


class ClipQueryTool:
    """Query extracted metrics to find clip segments"""
    
    def __init__(self, extracted_metrics_dir: str, clips_dir: str):
        """
        Args:
            extracted_metrics_dir: Path to data/processed/extracted_metrics
            clips_dir: Path to data/clips (where period MP4s are stored)
        """
        self.metrics_dir = Path(extracted_metrics_dir)
        self.clips_dir = Path(clips_dir)
        
        # Event taxonomy mapping (hockey terms → action types)
        self.event_taxonomy = {
            # Zone entries
            "ozone": ["CONTROLLED ENTRY INTO OZ", "OZ ENTRY PASS+", "O-ZONE ENTRY PASS RECEPTION"],
            "zone_entry": ["CONTROLLED ENTRY INTO OZ", "OZ ENTRY PASS+", "O-ZONE ENTRY PASS RECEPTION"],
            "dump_in": ["DUMP IN+", "CHIP DUMP+"],
            
            # Zone exits
            "dzone_exit": ["CONTROLLED EXIT FROM DZ"],
            "zone_exit": ["CONTROLLED EXIT FROM DZ"],
            "breakout": ["CONTROLLED EXIT FROM DZ", "DZ OUTLET PASS+"],
            
            # Shots
            "shot": ["SLOT SHOT FOR ONNET", "OUTSIDE SHOT FOR ONNET", "SLOT SHOT FOR MISSED", 
                    "OUTSIDE SHOT FOR MISSED", "SLOT SHOT FOR BLOCKED"],
            "goal": ["GOAL"],
            
            # Passes
            "pass": ["OZPASS", "NZPASS", "DZONE D2D+", "DZ OUTLET PASS+"],
            
            # Defensive
            "block": ["BLOCK OPPOSITION SHOT+", "BLOCK OPPOSITION PASS+"],
            "stick_check": ["OZ STICK CHK+", "DZ STICK CHK+"],
            "pressure": ["SHOT PRESSURE"],
            
            # Recoveries
            "lpr": ["LPR+", "DUMP IN LPR+", "OFF LPR"],
            "recovery": ["LPR+", "DUMP IN LPR+"],
            
            # Faceoffs
            "faceoff": ["Face-Off", "FACE OFF+", "FACE OFF-"],
        }
    
    def _timecode_to_seconds(self, timecode: str) -> float:
        """Convert HH:MM:SS:FF timecode to seconds since period start"""
        if not timecode or pd.isna(timecode):
            return 0.0
        
        parts = str(timecode).split(":")
        if len(parts) >= 3:
            hh = int(parts[0])
            mm = int(parts[1])
            ss = float(parts[2])
            # Ignore frames (parts[3]) for now
            return hh * 3600 + mm * 60 + ss
        return float(timecode)
    
    def _normalize_event_type(self, query_term: str) -> List[str]:
        """Map user query term to action types"""
        query_lower = query_term.lower().replace("-", "_").replace(" ", "_")
        
        # Direct match
        if query_lower in self.event_taxonomy:
            return self.event_taxonomy[query_lower]
        
        # Partial match (e.g., "exit" matches "zone_exit")
        matches = []
        for key, actions in self.event_taxonomy.items():
            if query_lower in key or key in query_lower:
                matches.extend(actions)
        
        if matches:
            return list(set(matches))
        
        # Return as-is if no match (user may have provided exact action name)
        return [query_term]
    
    def _find_timeline_csv(self, game_id: str) -> Optional[Path]:
        """Find the player_tendencies_timeline.csv for a given game"""
        pattern = f"*{game_id}*player_tendencies_timeline.csv"
        matches = list(self.metrics_dir.glob(pattern))
        return matches[0] if matches else None
    
    def _find_game_info(self, game_id: str) -> Optional[Dict]:
        """Load game_info from comprehensive_metrics.json"""
        pattern = f"*{game_id}*comprehensive_metrics.json"
        matches = list(self.metrics_dir.glob(pattern))
        if not matches:
            return None
        
        with open(matches[0], 'r') as f:
            data = json.load(f)
            return data.get('game_info')
    
    def _resolve_period_video_path(self, game_id: str, period: int, team_code: str, season: str = "2025-2026") -> Optional[Path]:
        """
        Resolve the path to the period MP4 file
        Format: data/clips/{season}/team/{team_code}/p{period}-{date}-NHL-{matchup}-{season}-{game_id}.mp4
        """
        # Search pattern
        pattern = f"p{period}*{game_id}*"
        
        # Try season-specific directory
        season_dir = self.clips_dir / season / "team" / team_code
        if season_dir.exists():
            matches = list(season_dir.glob(pattern))
            if matches:
                return matches[0]
        
        # Fallback: search all subdirectories
        matches = list(self.clips_dir.rglob(pattern))
        if matches:
            # Prefer .mp4, then .MOV
            mp4_matches = [m for m in matches if m.suffix.lower() in ['.mp4', '.mov']]
            if mp4_matches:
                return mp4_matches[0]
        
        return None
    
    def query_events(self, params: ClipSearchParams) -> List[ClipSegment]:
        """
        Query extracted metrics for matching events
        
        Returns:
            List of ClipSegment objects with timecode offsets
        """
        # For now, implement simple last_game query
        # TODO: Expand to handle other timeframes
        
        if not params.game_ids:
            print("Warning: game_ids not specified, cannot query")
            return []
        
        segments = []
        
        for game_id in params.game_ids[:params.limit]:
            timeline_csv = self._find_timeline_csv(game_id)
            if not timeline_csv:
                print(f"No timeline CSV found for game {game_id}")
                continue
            
            game_info = self._find_game_info(game_id)
            if not game_info:
                print(f"No game_info found for game {game_id}")
                continue
            
            # Load timeline
            df = pd.read_csv(timeline_csv)
            
            # Filter by players
            if params.players:
                # Normalize player IDs (handle both "8480018" and "8480018.0" formats)
                player_ids_normalized = []
                for p in params.players:
                    p_str = str(p).replace('.0', '')
                    player_ids_normalized.extend([p_str, f"{p_str}.0"])
                
                df['player_id_str'] = df['player_id'].astype(str)
                df = df[df['player_id_str'].isin(player_ids_normalized)]
            
            print(f"After player filter: {len(df)} rows")
            
            # Filter by event types
            if params.event_types:
                # Expand event types using taxonomy
                all_actions = []
                for event_term in params.event_types:
                    all_actions.extend(self._normalize_event_type(event_term))
                
                print(f"Looking for actions: {all_actions}")
                
                # Partial match on action column
                mask = df['action'].astype(str).apply(
                    lambda x: any(act.upper() in x.upper() for act in all_actions)
                )
                df = df[mask]
            
            print(f"After event filter: {len(df)} rows")
            
            if len(df) == 0:
                print(f"No matching events found for game {game_id}")
                continue
            
            # Filter by opponents if specified
            if params.opponents:
                # Determine opponent from game_info
                home_team = game_info.get('home_team')
                away_team = game_info.get('away_team')
                # This logic needs team inference - skip for now
            
            # Sort by game_time
            df = df.sort_values('gameTime')
            
            # Build clip segments
            for idx, row in df.head(params.limit).iterrows():
                timecode_s = self._timecode_to_seconds(row['timecode'])
                start_s = max(0, timecode_s - params.clip_window['pre_s'])
                end_s = timecode_s + params.clip_window['post_s']
                duration_s = end_s - start_s
                
                # Determine opponent
                team_code = row.get('team_code', '')
                home_team_code = game_info.get('home_team', '')
                away_team_code = game_info.get('away_team', '')
                opponent = away_team_code if team_code == home_team_code else home_team_code
                
                # Resolve period video path
                period = int(row['period']) if pd.notna(row['period']) else 1
                period_video = self._resolve_period_video_path(
                    game_id, 
                    period, 
                    team_code
                )
                
                clip_id = f"clip_{game_id}_p{period}_{int(timecode_s)}s_{row['player_id']}_{row['action'].replace(' ', '_')}"
                
                segment = ClipSegment(
                    clip_id=clip_id,
                    title=f"{row.get('action', 'Event')} - Period {period}",
                    description=f"{row.get('action')} by player {row['player_id']} ({row.get('outcome', 'N/A')})",
                    player_id=str(row['player_id']),
                    player_name=None,  # TODO: resolve from roster
                    team=row.get('team', ''),
                    team_code=team_code,
                    opponent=opponent,
                    game_id=game_id,
                    game_date=game_id[:8] if len(game_id) >= 8 else "",  # Extract date from game_id
                    period=period,
                    period_time=str(row.get('periodTime', '')),
                    timecode=str(row.get('timecode', '')),
                    timecode_seconds=timecode_s,
                    start_timecode_s=start_s,
                    end_timecode_s=end_s,
                    duration_s=duration_s,
                    event_type=str(row.get('action', '')),
                    outcome=str(row.get('outcome', '')) if pd.notna(row.get('outcome')) else None,
                    zone=str(row.get('zone', '')) if pd.notna(row.get('zone')) else None,
                    period_video_path=str(period_video) if period_video else None,
                    provenance={
                        'source_csv': str(timeline_csv),
                        'event_index': int(idx),
                        'game_info': game_info
                    }
                )
                
                segments.append(segment)
        
        return segments


def main():
    """Demo query"""
    tool = ClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    # Example: Find zone exits for a specific player in a game
    params = ClipSearchParams(
        players=["8480018", "8473422"],  # Player IDs - will match with or without .0
        event_types=["zone_exit"],
        timeframe="last_game",
        game_ids=["20031"],  # MTL vs CHI game
        limit=5
    )
    
    segments = tool.query_events(params)
    
    print(f"\nFound {len(segments)} clip segments:\n")
    for seg in segments:
        print(f"  {seg.clip_id}")
        print(f"    Event: {seg.event_type} ({seg.outcome})")
        print(f"    Period {seg.period} @ {seg.timecode} ({seg.timecode_seconds:.1f}s)")
        print(f"    Clip window: {seg.start_timecode_s:.1f}s - {seg.end_timecode_s:.1f}s ({seg.duration_s:.1f}s)")
        print(f"    Video: {seg.period_video_path}")
        print()


if __name__ == "__main__":
    main()

