"""
HeartBeat Engine - Video Clip Models
Montreal Canadiens Advanced Analytics Assistant

Data models for video clip management and retrieval.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import os

@dataclass
class ClipMetadata:
    """Metadata for a video clip"""
    clip_id: str
    player_name: str
    player_id: Optional[str] = None
    game_date: str = ""
    opponent: str = ""
    event_type: str = ""  # goals, assists, saves, hits, penalties, other
    period: Optional[int] = None
    game_time: str = ""
    situation: str = ""  # even_strength, power_play, penalty_kill, etc.
    description: str = ""
    file_path: str = ""
    file_size_mb: float = 0.0
    duration_seconds: float = 0.0
    resolution: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    indexed_at: Optional[datetime] = None

@dataclass
class ClipSearchParams:
    """Parameters for searching video clips"""
    player_names: List[str] = field(default_factory=list)
    event_types: List[str] = field(default_factory=list)
    opponents: List[str] = field(default_factory=list)
    game_dates: List[str] = field(default_factory=list)
    time_filter: str = ""  # last_game, last_5_games, etc.
    limit: int = 10
    user_context: Optional[Any] = None

@dataclass
class ClipResult:
    """Result from clip retrieval"""
    clip_id: str
    title: str
    player_name: str
    game_info: str
    event_type: str
    description: str
    file_url: str
    thumbnail_url: str
    duration: float
    metadata: ClipMetadata
    relevance_score: float = 0.0

class ClipIndexManager:
    """Manages video clip indexing and retrieval"""
    
    def __init__(self, clips_base_path: str = "data/clips"):
        # Ensure absolute path to avoid dependency on working directory
        base_path = Path(clips_base_path)
        self.clips_base_path = base_path if base_path.is_absolute() else (Path.cwd() / base_path).resolve()
        self.clip_cache = {}
        self.index_cache_ttl = 300  # 5 minutes
        self.last_indexed = None
        
    def discover_clips(self, season: str = "2024-2025") -> List[ClipMetadata]:
        """Discover all video clips in the directory structure"""
        
        clips = []
        season_path = self.clips_base_path / season
        
        if not season_path.exists():
            return clips
        
        # Search in players directories
        players_path = season_path / "players"
        if players_path.exists():
            clips.extend(self._discover_player_clips(players_path, season))
        
        # Search in game directories
        games_path = season_path / "games"
        if games_path.exists():
            clips.extend(self._discover_game_clips(games_path, season))
            
        # Search in opponent directories
        opponents_path = season_path / "vs_opponents"
        if opponents_path.exists():
            clips.extend(self._discover_opponent_clips(opponents_path, season))
        
        return clips
    
    def _discover_player_clips(self, players_path: Path, season: str) -> List[ClipMetadata]:
        """Discover clips in player directories"""
        
        clips = []
        
        for player_dir in players_path.iterdir():
            if not player_dir.is_dir():
                continue
                
            player_name = player_dir.name.replace('_', ' ').title()
            
            # Search in subdirectories - prioritize vs_ directories as game-specific
            for event_dir in player_dir.iterdir():
                if not event_dir.is_dir():
                    continue
                    
                # Handle vs_ directories as game-specific (not generic event types)
                if event_dir.name.startswith('vs_'):
                    event_type = event_dir.name  # Keep the full vs_opponent_date format
                else:
                    event_type = event_dir.name  # Regular event types like 'goals', 'assists'
                
                clips.extend(self._scan_directory_for_clips(
                    event_dir, player_name, event_type, season
                ))
        
        return clips
    
    def _discover_game_clips(self, games_path: Path, season: str) -> List[ClipMetadata]:
        """Discover clips in game directories"""
        
        clips = []
        
        for game_dir in games_path.iterdir():
            if not game_dir.is_dir():
                continue
                
            clips.extend(self._scan_directory_for_clips(
                game_dir, "team", "game_highlights", season
            ))
        
        return clips
    
    def _discover_opponent_clips(self, opponents_path: Path, season: str) -> List[ClipMetadata]:
        """Discover clips in opponent directories"""
        
        clips = []
        
        for opponent_dir in opponents_path.iterdir():
            if not opponent_dir.is_dir():
                continue
                
            opponent = opponent_dir.name.replace('vs_', '').replace('_', ' ').title()
            clips.extend(self._scan_directory_for_clips(
                opponent_dir, "team", "matchup", season, opponent=opponent
            ))
        
        return clips
    
    def _scan_directory_for_clips(
        self, 
        directory: Path, 
        player_name: str, 
        event_type: str, 
        season: str,
        opponent: str = ""
    ) -> List[ClipMetadata]:
        """Scan a directory for video clip files"""
        
        clips = []
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        
        for file_path in directory.rglob('*'):
            if file_path.suffix.lower() in video_extensions:
                try:
                    clip_metadata = self._create_clip_metadata(
                        file_path, player_name, event_type, season, opponent
                    )
                    clips.append(clip_metadata)
                except Exception as e:
                    # Log error but continue processing other clips
                    continue
        
        return clips
    
    def _create_clip_metadata(
        self, 
        file_path: Path, 
        player_name: str, 
        event_type: str, 
        season: str,
        opponent: str = ""
    ) -> ClipMetadata:
        """Create clip metadata from file path and context"""
        
        # Extract information from file name and path
        file_name = file_path.stem
        
        # Try to extract game date from path
        game_date = self._extract_game_date_from_path(str(file_path))
        
        # Try to extract opponent from path if not provided
        if not opponent:
            opponent = self._extract_opponent_from_path(str(file_path))
        
        # Generate clip ID
        clip_id = f"{season}_{player_name.replace(' ', '_')}_{file_name}"
        
        # Get file stats
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        return ClipMetadata(
            clip_id=clip_id,
            player_name=player_name,
            game_date=game_date,
            opponent=opponent,
            event_type=event_type,
            description=f"{player_name} - {event_type}",
            file_path=str(file_path),
            file_size_mb=round(file_size_mb, 2),
            tags=[event_type, player_name.replace(' ', '_'), season]
        )
    
    def _extract_game_date_from_path(self, path: str) -> str:
        """Extract game date from file path"""
        
        # Look for date patterns like 2024-10-09
        import re
        date_pattern = r'20\d{2}-\d{2}-\d{2}'
        match = re.search(date_pattern, path)
        
        return match.group(0) if match else ""
    
    def _extract_opponent_from_path(self, path: str) -> str:
        """Extract opponent from file path"""
        
        # Look for vs_team patterns or team names in path
        if 'vs_' in path:
            parts = path.split('vs_')
            if len(parts) > 1:
                opponent_part = parts[1].split('/')[0].split('_')[0]
                return opponent_part.replace('_', ' ').title()
        
        # Look for known team names in path
        nhl_teams = [
            'toronto', 'boston', 'buffalo', 'ottawa', 'detroit',
            'florida', 'tampa', 'washington', 'carolina', 'columbus',
            'pittsburgh', 'philadelphia', 'new_jersey', 'ny_rangers',
            'ny_islanders', 'colorado', 'vegas', 'minnesota', 'winnipeg',
            'calgary', 'edmonton', 'vancouver', 'seattle', 'anaheim',
            'los_angeles', 'san_jose', 'arizona', 'utah', 'st_louis',
            'chicago', 'dallas', 'nashville'
        ]
        
        path_lower = path.lower()
        for team in nhl_teams:
            if team in path_lower:
                return team.replace('_', ' ').title()
        
        return ""
    
    async def search_clips(self, search_params: ClipSearchParams) -> List[ClipResult]:
        """Search for clips based on parameters"""
        
        # Get all available clips (with caching)
        all_clips = self._get_cached_clips()
        
        # Filter clips based on search parameters
        filtered_clips = self._filter_clips(all_clips, search_params)
        
        # Convert to ClipResult objects
        results = []
        for clip in filtered_clips[:search_params.limit]:
            result = self._create_clip_result(clip)
            results.append(result)
        
        return results
    
    def _get_cached_clips(self) -> List[ClipMetadata]:
        """Get clips with caching"""
        
        now = datetime.now()
        
        # Check if cache is still valid
        if (self.last_indexed and 
            (now - self.last_indexed).seconds < self.index_cache_ttl and
            self.clip_cache):
            return self.clip_cache
        
        # Rebuild cache
        self.clip_cache = self.discover_clips()
        self.last_indexed = now
        
        return self.clip_cache
    
    def _filter_clips(self, clips: List[ClipMetadata], params: ClipSearchParams) -> List[ClipMetadata]:
        """Filter clips based on search parameters"""
        
        import logging
        logger = logging.getLogger(__name__)
        
        filtered = clips
        logger.info(f"Starting with {len(filtered)} clips")
        
        # Filter by player names
        if params.player_names:
            player_names_lower = [name.lower() for name in params.player_names]
            logger.info(f"Filtering by players: {player_names_lower}")
            
            before_count = len(filtered)
            filtered = [
                clip for clip in filtered 
                if clip.player_name.lower() in player_names_lower
            ]
            logger.info(f"After player filter: {len(filtered)} clips (was {before_count})")
            
            # Debug player matching
            if len(filtered) == 0 and before_count > 0:
                logger.warning("Player filter eliminated all clips!")
                for clip in clips:
                    logger.info(f"Available clip player: '{clip.player_name.lower()}' vs search: {player_names_lower}")
        
        # Filter by event types (skip if generic terms like "shifts")
        if params.event_types:
            event_types_lower = [event.lower() for event in params.event_types]
            
            # Skip event filtering for generic terms that should match all clips
            generic_terms = ['shifts', 'highlights', 'clips', 'video', 'footage']
            is_generic_query = any(term in event_types_lower for term in generic_terms)
            
            if not is_generic_query:
                before_count = len(filtered)
                filtered = [
                    clip for clip in filtered 
                    if clip.event_type.lower() in event_types_lower
                ]
                logger.info(f"After event filter: {len(filtered)} clips (was {before_count})")
            else:
                logger.info(f"Skipping event filter - generic query for all clips")
        
        # Filter by opponents
        if params.opponents:
            opponents_lower = [opp.lower() for opp in params.opponents]
            before_count = len(filtered)
            filtered = [
                clip for clip in filtered 
                if any(opp in clip.opponent.lower() for opp in opponents_lower)
            ]
            logger.info(f"After opponent filter: {len(filtered)} clips (was {before_count})")
        
        # Filter by game dates
        if params.game_dates:
            before_count = len(filtered)
            filtered = [
                clip for clip in filtered 
                if clip.game_date in params.game_dates
            ]
            logger.info(f"After date filter: {len(filtered)} clips (was {before_count})")
        
        # Apply time filter
        if params.time_filter:
            before_count = len(filtered)
            filtered = self._apply_time_filter(filtered, params.time_filter)
            logger.info(f"After time filter '{params.time_filter}': {len(filtered)} clips (was {before_count})")
        
        logger.info(f"Final filtered result: {len(filtered)} clips")
        return filtered
    
    def _apply_time_filter(self, clips: List[ClipMetadata], time_filter: str) -> List[ClipMetadata]:
        """Apply time-based filtering with smart game identification"""
        
        import logging
        logger = logging.getLogger(__name__)
        
        if time_filter == "last_game":
            # Get clips from the most recent game date
            if clips:
                # Find all unique game dates
                game_dates = [clip.game_date for clip in clips if clip.game_date]
                
                if game_dates:
                    latest_date = max(game_dates)
                    logger.info(f"Identified last game date: {latest_date}")
                    
                    last_game_clips = [clip for clip in clips if clip.game_date == latest_date]
                    logger.info(f"Found {len(last_game_clips)} clips from last game ({latest_date})")
                    
                    return last_game_clips
                else:
                    logger.warning("No game dates found in clips")
                    # If no dates, return all clips (fallback)
                    return clips
        elif time_filter in ["last_2_games", "last_3_games", "last_5_games", "last_10_games"]:
            # Extract number of games
            num_games = int(time_filter.split('_')[1])
            
            if clips:
                # Get unique game dates and sort
                game_dates = sorted(set(clip.game_date for clip in clips if clip.game_date), reverse=True)
                recent_dates = game_dates[:num_games]
                
                logger.info(f"Found {len(recent_dates)} recent game dates for {time_filter}")
                
                return [clip for clip in clips if clip.game_date in recent_dates]
        elif time_filter == "this_season":
            # For now, return all clips (assuming they're all from current season)
            logger.info("Returning all clips for 'this_season' filter")
            return clips
        
        # Default: return all clips for unrecognized filters
        return clips
    
    def _create_clip_result(self, clip: ClipMetadata) -> ClipResult:
        """Create a ClipResult from ClipMetadata"""
        
        # Generate web-accessible URLs (this would be handled by your API)
        file_url = f"/api/v1/clips/{clip.clip_id}/video"
        thumbnail_url = f"/api/v1/clips/{clip.clip_id}/thumbnail"
        
        # Create descriptive title
        title = f"{clip.player_name}"
        if clip.event_type and clip.event_type != "various":
            title += f" - {clip.event_type.title()}"
        
        # Create game info
        game_info = ""
        if clip.opponent:
            game_info = f"vs {clip.opponent}"
        if clip.game_date:
            if game_info:
                game_info += f" ({clip.game_date})"
            else:
                game_info = clip.game_date
        
        return ClipResult(
            clip_id=clip.clip_id,
            title=title,
            player_name=clip.player_name,
            game_info=game_info,
            event_type=clip.event_type,
            description=clip.description,
            file_url=file_url,
            thumbnail_url=thumbnail_url,
            duration=clip.duration_seconds,
            metadata=clip,
            relevance_score=1.0  # Basic relevance, can be enhanced later
        )
