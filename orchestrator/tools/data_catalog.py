"""
HeartBeat Engine - Data Catalog
Professional data source mapping for Montreal Canadiens analytics

Maps Parquet file locations to query types for intelligent data retrieval.
"""

from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class DataCategory(Enum):
    """Categories of hockey analytics data"""
    POWER_PLAY = "power_play"
    PENALTY_KILL = "penalty_kill"
    LINE_COMBINATIONS = "line_combinations"
    MATCHUPS = "matchups"
    SEASON_RESULTS = "season_results"
    PLAYER_STATS = "player_stats"
    TEAM_STATS = "team_stats"
    ZONE_ENTRIES = "zone_entries"
    ZONE_EXITS = "zone_exits"
    POSSESSION = "possession"
    SHOOTING = "shooting"
    PASSING = "passing"
    DEFENSIVE = "defensive"
    FACEOFFS = "faceoffs"
    GOALIE = "goalie"
    PLAY_BY_PLAY = "play_by_play"
    ROSTERS = "rosters"


class HeartBeatDataCatalog:
    """
    Central catalog of all HeartBeat data sources.
    
    Provides intelligent file mapping based on query intent.
    """
    
    def __init__(self, data_root: str):
        """
        Initialize data catalog.
        
        Args:
            data_root: Root directory for processed data
        """
        self.data_root = Path(data_root)
        self.season_2024_2025 = "2024-2025"
        self.season_2025_2026 = "2025-2026"  # For future data
    
    def get_power_play_file(self, season: str = "2024-2025") -> Path:
        """Get power play units file"""
        return self.data_root / f"analytics/mtl_line_combinations_{season}/Line_Combinations_Metrics_for_PPUnits.parquet"
    
    def get_penalty_kill_file(self, season: str = "2024-2025") -> Path:
        """Get penalty kill units file"""
        return self.data_root / f"analytics/mtl_line_combinations_{season}/Line_Combinations_Metrics_for_SHUnits.parquet"
    
    def get_forward_lines_file(self, season: str = "2024-2025") -> Path:
        """Get forward line combinations file"""
        # Note: File has "(1)" in name - this might need cleanup
        return self.data_root / f"analytics/mtl_line_combinations_{season}/Line_Combinations_Metrics_for_Forwards (1).parquet"
    
    def get_defense_pairs_file(self, season: str = "2024-2025") -> Path:
        """Get defense pairing combinations file"""
        return self.data_root / f"analytics/mtl_line_combinations_{season}/Line_Combinations_Metrics_for_Defencemen.parquet"
    
    def get_matchup_report_file(self, season: str = "2024-2025") -> Path:
        """
        Get unified matchup reports (MTL vs all opponents) with intelligent fallback.
        Falls back to most recent available season if requested season doesn't exist.
        """
        requested_file = self.data_root / f"analytics/mtl_matchup_reports/unified_matchup_reports_{season.replace('-', '_')}.parquet"
        
        # If requested season exists, use it
        if requested_file.exists():
            return requested_file
        
        # Otherwise, find most recent available
        matchup_dir = self.data_root / "analytics/mtl_matchup_reports"
        if matchup_dir.exists():
            available = sorted(matchup_dir.glob("unified_matchup_reports_*.parquet"), reverse=True)
            if available:
                logger.info(f"Season {season} not available, using most recent: {available[0].name}")
                return available[0]
        
        return requested_file  # Return requested even if doesn't exist (will error gracefully)
    
    def get_season_results_file(self, season: str = "2024-2025") -> Path:
        """
        Get game-by-game season results with intelligent fallback.
        Falls back to most recent available season if requested doesn't exist.
        """
        requested_file = self.data_root / f"analytics/mtl_season_results/{season}/mtl_season_game_results_{season}.parquet"
        
        if requested_file.exists():
            return requested_file
        
        # Fallback to most recent
        results_dir = self.data_root / "analytics/mtl_season_results"
        if results_dir.exists():
            available_seasons = sorted([d.name for d in results_dir.iterdir() if d.is_dir()], reverse=True)
            if available_seasons:
                fallback_season = available_seasons[0]
                fallback_file = results_dir / fallback_season / f"mtl_season_game_results_{fallback_season}.parquet"
                if fallback_file.exists():
                    logger.info(f"Season results: using {fallback_season} (requested {season} not found)")
                    return fallback_file
        
        return requested_file
    
    def get_player_stats_file(
        self, 
        team: str = "MTL",
        position: str = "forwards",
        season: str = "2024-2025"
    ) -> Path:
        """
        Get player statistics file.
        
        Args:
            team: Team abbreviation (MTL, TOR, BOS, etc.)
            position: "forwards", "defenseman", or "goalie"
            season: Season string
        """
        position_map = {
            "forwards": "forwards_stats",
            "defense": "defenseman_stats",
            "defenseman": "defenseman_stats",
            "goalie": "goalie_stats"
        }
        
        pos_folder = position_map.get(position.lower(), "forwards_stats")
        return self.data_root / f"analytics/nhl_player_stats/{team}/{season}/{pos_folder}/{team}-{pos_folder.split('_')[0].capitalize()}-Comprehensive-{season}.parquet"
    
    def get_team_stat_file(
        self,
        category: str,
        subcategory: str,
        direction: str = "for",
        season: str = "2024-2025"
    ) -> Path:
        """
        Get team-level statistics file.
        
        Args:
            category: Main category (defensive, passing, shooting, etc.)
            subcategory: Specific metric (all, blocks, bodychecks, etc.)
            direction: "for" (offensive) or "against" (defensive)
            season: Season string
            
        Example:
            get_team_stat_file("shooting", "all_shots", "for") →
            mtl_shooting_all_shots_for_2024-2025.parquet
        """
        return self.data_root / f"analytics/mtl_team_stats/mtl_{category}/mtl_{category}_{subcategory}_{direction}_{season}.parquet"
    
    def get_play_by_play_file(self, season: str = "2024-25") -> Path:
        """Get play-by-play events file"""
        return self.data_root / f"fact/pbp/unified_pbp_{season}.parquet"
    
    def get_roster_file(self, date: Optional[str] = None) -> Path:
        """
        Get NHL roster snapshot file with intelligent fallback.
        
        Args:
            date: Specific date in YYYY_MM_DD format (defaults to latest)
            
        Returns:
            Path to roster Parquet file
        """
        roster_dir = self.data_root / "rosters"
        
        if date:
            # Try specific date
            requested_file = roster_dir / f"nhl_rosters_{date}.parquet"
            if requested_file.exists():
                return requested_file
        
        # Fallback to "latest"
        latest_file = roster_dir / "nhl_rosters_latest.parquet"
        if latest_file.exists():
            return latest_file
        
        # Fallback to most recent dated file
        if roster_dir.exists():
            roster_files = sorted(roster_dir.glob("nhl_rosters_*.parquet"), reverse=True)
            # Filter out "latest" file
            dated_files = [f for f in roster_files if "latest" not in f.name]
            if dated_files:
                logger.info(f"Using most recent roster file: {dated_files[0].name}")
                return dated_files[0]
        
        # Return requested even if doesn't exist (will error gracefully)
        return latest_file if not date else roster_dir / f"nhl_rosters_{date}.parquet"
    
    def get_files_for_query_type(
        self,
        query_keywords: List[str],
        season: str = "2024-2025"
    ) -> List[Path]:
        """
        Intelligent file selection based on query keywords.
        
        Args:
            query_keywords: Keywords from user query (lowercased)
            season: Target season
            
        Returns:
            List of relevant Parquet file paths
        """
        files = []
        
        # Power play queries
        if any(kw in query_keywords for kw in ['power play', 'pp', 'man advantage', 'powerplay']):
            files.append(self.get_power_play_file(season))
        
        # Penalty kill queries
        if any(kw in query_keywords for kw in ['penalty kill', 'pk', 'shorthanded', 'short handed']):
            files.append(self.get_penalty_kill_file(season))
        
        # Matchup queries
        if any(kw in query_keywords for kw in ['vs', 'against', 'matchup', 'versus', 'toronto', 'boston', 'tampa']):
            files.append(self.get_matchup_report_file(season))
        
        # Season/game results
        if any(kw in query_keywords for kw in ['game', 'result', 'score', 'record', 'season', 'won', 'lost']):
            files.append(self.get_season_results_file(season))
        
        # Player-specific queries
        if any(kw in query_keywords for kw in ['suzuki', 'caufield', 'laine', 'hutson', 'slafkovsky', 'player']):
            files.append(self.get_player_stats_file("MTL", "forwards", season))
            files.append(self.get_player_stats_file("MTL", "defenseman", season))
        
        # Shooting queries
        if any(kw in query_keywords for kw in ['shot', 'shooting', 'shots on net', 'sog']):
            files.append(self.get_team_stat_file("shooting", "all_shots", "for", season))
        
        # Passing queries
        if any(kw in query_keywords for kw in ['pass', 'passing', 'assist', 'playmaking']):
            files.append(self.get_team_stat_file("passing", "all", "for", season))
        
        # Defensive queries
        if any(kw in query_keywords for kw in ['defense', 'defensive', 'blocks', 'hits']):
            files.append(self.get_team_stat_file("defensive", "all", "for", season))
        
        # Zone entry/exit queries
        if any(kw in query_keywords for kw in ['zone entry', 'zone exit', 'breakout']):
            files.append(self.get_team_stat_file("dz", "exits_all", "for", season))
            files.append(self.get_team_stat_file("entries", "oz", "for", season))
        
        # Remove duplicates, preserve order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)
        
        return unique_files
    
    def get_all_mtl_stat_categories(self, season: str = "2024-2025") -> Dict[str, List[Path]]:
        """
        Get all MTL team statistics organized by category.
        
        Returns:
            Dict mapping category name to list of file paths
        """
        categories = {
            "power_play": [self.get_power_play_file(season)],
            "penalty_kill": [self.get_penalty_kill_file(season)],
            "shooting": list((self.data_root / f"analytics/mtl_team_stats/mtl_shooting").glob(f"*_{season}.parquet")),
            "passing": list((self.data_root / f"analytics/mtl_team_stats/mtl_passing").glob(f"*_{season}.parquet")),
            "defensive": list((self.data_root / f"analytics/mtl_team_stats/mtl_defensive").glob(f"*_{season}.parquet")),
            "possession": list((self.data_root / f"analytics/mtl_team_stats/mtl_possession").glob(f"*_{season}.parquet")),
            "faceoffs": list((self.data_root / f"analytics/mtl_team_stats/mtl_faceoffs").glob(f"*_{season}.parquet")),
            "zone_exits": list((self.data_root / f"analytics/mtl_team_stats/mtl_dz").glob(f"*_{season}.parquet")),
            "zone_entries": list((self.data_root / f"analytics/mtl_team_stats/mtl_entries").glob(f"*_{season}.parquet")),
        }
        
        return categories
    
    def get_available_seasons(self) -> List[str]:
        """Get list of available seasons in the data"""
        seasons = set()
        
        # Check season results directories
        season_results_dir = self.data_root / "analytics/mtl_season_results"
        if season_results_dir.exists():
            for subdir in season_results_dir.iterdir():
                if subdir.is_dir():
                    seasons.add(subdir.name)
        
        # Check line combinations directories
        line_combos_parent = self.data_root / "analytics"
        if line_combos_parent.exists():
            for subdir in line_combos_parent.glob("mtl_line_combinations_*"):
                season = subdir.name.replace("mtl_line_combinations_", "")
                seasons.add(season)
        
        return sorted(list(seasons))
    
    def file_exists(self, file_path: Path) -> bool:
        """Check if a data file exists"""
        return file_path.exists() and file_path.is_file()
    
    def get_file_info(self, file_path: Path) -> Dict:
        """Get metadata about a data file"""
        if not self.file_exists(file_path):
            return {"exists": False}
        
        try:
            df = pd.read_parquet(file_path)
            return {
                "exists": True,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "size_mb": file_path.stat().st_size / (1024 * 1024)
            }
        except Exception as e:
            return {
                "exists": True,
                "error": str(e)
            }
    
    def get_team_roster_from_snapshot(self, team: str, date: Optional[str] = None) -> pd.DataFrame:
        """
        Get roster for specific team from Parquet snapshot.
        
        Args:
            team: Team abbreviation (e.g., "MTL", "TOR")
            date: Optional specific date (YYYY_MM_DD format)
            
        Returns:
            DataFrame of team's roster
        """
        roster_file = self.get_roster_file(date)
        
        if not roster_file.exists():
            logger.warning(f"Roster file not found: {roster_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_parquet(roster_file)
            return df[df['team_abbrev'] == team.upper()].copy()
        except Exception as e:
            logger.error(f"Error reading roster file: {e}")
            return pd.DataFrame()
    
    def search_player_in_rosters(self, player_name: str, date: Optional[str] = None) -> pd.DataFrame:
        """
        Search for player across all teams in roster snapshot.
        
        Args:
            player_name: Full or partial player name
            date: Optional specific date (YYYY_MM_DD format)
            
        Returns:
            DataFrame of matching players
        """
        roster_file = self.get_roster_file(date)
        
        if not roster_file.exists():
            logger.warning(f"Roster file not found: {roster_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_parquet(roster_file)
            
            # Case-insensitive search in full_name
            mask = df['full_name'].str.contains(player_name, case=False, na=False)
            
            return df[mask].copy()
        except Exception as e:
            logger.error(f"Error searching rosters: {e}")
            return pd.DataFrame()

