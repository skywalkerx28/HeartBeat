"""
HeartBeat Engine - Parquet Data Client V2
Production-grade data retrieval for Montreal Canadiens analytics

Professionally engineered data access layer with:
- Intelligent file mapping via DataCatalog
- Temporal query support (last night, this season, etc.)
- Comprehensive MTL Canadiens data coverage
- Performance optimization and caching
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from orchestrator.tools.data_catalog import HeartBeatDataCatalog, DataCategory
import httpx

# Module-level lightweight cache for NHL scoreboard payloads reused across requests
_GLOBAL_SCORE_CACHE: Dict[str, Dict[str, Any]] = {}
_GLOBAL_SCORE_TTL_SECONDS: int = 60  # share across requests to dampen bursts

logger = logging.getLogger(__name__)


class ParquetDataClientV2:
    """
    Production data client for HeartBeat Engine.
    
    Handles all data retrieval with intelligent file selection,
    temporal query parsing, and performance optimization.
    """
    
    def __init__(self, data_directory: str):
        """
        Initialize data client.
        
        Args:
            data_directory: Root directory containing processed Parquet files
        """
        self.data_root = Path(data_directory)
        self.catalog = HeartBeatDataCatalog(str(self.data_root))
        
        # Cache for frequently accessed data
        self._cache: Dict[str, pd.DataFrame] = {}
        # Lightweight caches for NHL API results (request-local)
        self._score_cache: Dict[str, Any] = {}  # date -> payload
        self._score_cache_ttl_seconds: int = 120
        self._team_recent_cache: Dict[str, Dict[str, Any]] = {}  # key(team,window) -> {df, expires_at}
        
        logger.info(f"ParquetDataClient V2 initialized: {self.data_root}")
    
    async def get_power_play_stats(
        self,
        opponent: Optional[str] = None,
        season: str = "2024-2025",
        include_sh_context: bool = False
    ) -> Dict[str, Any]:
        """
        Get Montreal Canadiens power play statistics.
        
        Args:
            opponent: Specific opponent (e.g., "Toronto", "TOR")
            season: NHL season (uses intelligent fallback to most recent available)
            include_sh_context: Also include penalty kill data for context
            
        Returns:
            Power play analysis with units, metrics, and performance data
        """
        try:
            # Load PP units data
            pp_file = self.catalog.get_power_play_file(season)
            
            # INTELLIGENT FALLBACK: If requested season doesn't exist, use most recent
            if not pp_file.exists():
                logger.info(f"Season {season} not available, trying fallback...")
                available_seasons = self.catalog.get_available_seasons()
                
                if available_seasons:
                    # Use most recent available season
                    fallback_season = available_seasons[-1]
                    pp_file = self.catalog.get_power_play_file(fallback_season)
                    
                    if pp_file.exists():
                        logger.info(f"Using fallback season: {fallback_season}")
                        season = fallback_season  # Update season variable
                    else:
                        logger.warning(f"Power play file not found even with fallback: {pp_file}")
                        return {
                            "analysis_type": "power_play",
                            "error": f"Power play data not available for any season",
                            "requested_season": season,
                            "available_seasons": available_seasons
                        }
                else:
                    logger.warning(f"No available seasons found")
                    return {
                        "analysis_type": "power_play",
                        "error": f"Power play data not available for {season}",
                        "season": season
                    }
            
            df = pd.read_parquet(pp_file)
            
            # Build comprehensive response
            result = {
                "analysis_type": "power_play",
                "season": season,
                "team": "Montreal Canadiens",
                "total_pp_units": len(df),
                "data_source": str(pp_file.name),
                "note": f"Showing {season} data (most recent available)" if season != "2025-2026" else None
            }
            
            # Add unit-level data
            if len(df) > 0:
                # Sort by XGF% or TOI for best units
                df_sorted = df.sort_values('XGF%', ascending=False) if 'XGF%' in df.columns else df
                
                result["pp_units"] = df_sorted.to_dict('records')
                result["top_unit"] = df_sorted.iloc[0].to_dict() if len(df_sorted) > 0 else None
                
                # Aggregate metrics
                if 'TOI(sec)' in df.columns:
                    result["total_pp_toi_seconds"] = float(df['TOI(sec)'].sum())
                if 'XGF' in df.columns:
                    result["total_xgf"] = float(df['XGF'].sum())
                if 'SOT' in df.columns:
                    result["total_shots_on_target"] = float(df['SOT'].sum())
            
            # Opponent-specific filtering (if needed)
            if opponent:
                result["opponent_filter"] = opponent
                # Note: PP units don't have opponent breakdown - would need matchup data
                result["note"] = "Power play units show overall performance. For opponent-specific PP data, query matchup reports."
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading power play stats: {str(e)}")
            return {
                "analysis_type": "power_play",
                "error": str(e),
                "season": season
            }
    
    async def get_matchup_data(
        self,
        opponent: str,
        season: str = "2024-2025",
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get matchup data for MTL vs specific opponent.
        
        Args:
            opponent: Opponent team name or abbreviation
            season: NHL season
            metrics: Specific metrics to retrieve (None = all)
            
        Returns:
            Matchup analysis with head-to-head metrics
        """
        try:
            matchup_file = self.catalog.get_matchup_report_file(season)
            
            if not matchup_file.exists():
                logger.warning(f"Matchup file not found: {matchup_file}")
                return {
                    "analysis_type": "matchup",
                    "error": f"Matchup data not available for {season}",
                    "opponent": opponent,
                    "season": season
                }
            
            df = pd.read_parquet(matchup_file)
            logger.info(f"Loaded matchup file with {len(df)} rows, {len(df.columns)} columns")
            
            # Extract actual season from filename if fallback was used
            actual_season = season
            if matchup_file.name != f"unified_matchup_reports_{season.replace('-', '_')}.parquet":
                # Fallback was used - extract season from filename
                import re
                season_match = re.search(r'(\d{4}_\d{4})', matchup_file.name)
                if season_match:
                    actual_season = season_match.group(1).replace('_', '-')
                    logger.info(f"Using fallback data from {actual_season} (requested {season})")
            
            # Normalize opponent name to match column name (e.g., "TOR" → "Toronto")
            opponent_normalized = self._normalize_team_name(opponent)
            logger.info(f"Normalized opponent '{opponent}' → '{opponent_normalized}'")
            
            # Check if opponent column exists in the wide-format data
            if opponent_normalized not in df.columns:
                logger.warning(f"Opponent column '{opponent_normalized}' not found in matchup data")
                logger.info(f"Available columns: {df.columns.tolist()}")
                return {
                    "analysis_type": "matchup",
                    "error": f"No matchup data for {opponent_normalized}",
                    "opponent": opponent,
                    "season": season
                }
            
            logger.info(f"✓ Found '{opponent_normalized}' column in matchup data")
            
            # For wide-format data, filter rows with valid Toronto data
            matchup_df = df[['Metric Label', 'Montreal', opponent_normalized]].dropna()
            logger.info(f"✓ Filtered matchup data: {len(matchup_df)} rows with valid {opponent_normalized} metrics")
            
            result = {
                "analysis_type": "matchup",
                "team": "Montreal Canadiens",
                "opponent": opponent_normalized,
                "season": actual_season,  # Use actual season from file, not requested season
                "total_matchup_rows": len(matchup_df),
                "data_source": str(matchup_file.name),
                "note": f"Showing {actual_season} data (most recent available)" if actual_season != season else None
            }
            
            if len(matchup_df) > 0:
                # Extract key metrics in easy-to-read format
                key_metrics = {}
                for _, row in matchup_df.iterrows():
                    metric_label = row['Metric Label']
                    mtl_value = row['Montreal']
                    opp_value = row[opponent_normalized]
                    
                    if metric_label:
                        key_metrics[metric_label] = {
                            "mtl": float(mtl_value) if pd.notna(mtl_value) else 0,
                            "opponent": float(opp_value) if pd.notna(opp_value) else 0,
                            "difference": float(mtl_value - opp_value) if pd.notna(mtl_value) and pd.notna(opp_value) else 0
                        }
                
                result["key_metrics"] = key_metrics
                result["matchups"] = matchup_df.to_dict('records')
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading matchup data: {str(e)}")
            return {
                "analysis_type": "matchup",
                "error": str(e),
                "opponent": opponent,
                "season": season
            }
    
    async def get_season_results(
        self,
        season: str = "2024-2025",
        opponent: Optional[str] = None,
        date_filter: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get season game results.
        
        Args:
            season: NHL season
            opponent: Filter for specific opponent
            date_filter: {"start": "2024-10-01", "end": "2024-12-31"} for date range
            
        Returns:
            Game-by-game results with scores, dates, opponents
        """
        try:
            results_file = self.catalog.get_season_results_file(season)
            
            if not results_file.exists():
                logger.warning(f"Season results file not found: {results_file}")
                return {
                    "analysis_type": "season_results",
                    "error": f"Season results not available for {season}",
                    "season": season
                }
            
            df = pd.read_parquet(results_file)
            
            # Apply filters
            filtered_df = df
            
            if opponent:
                opponent_norm = self._normalize_team_name(opponent)
                filtered_df = filtered_df[filtered_df['Opponent'].str.lower() == opponent_norm.lower()]
            
            if date_filter:
                if 'Date' in df.columns:
                    filtered_df['Date'] = pd.to_datetime(filtered_df['Date'])
                    if 'start' in date_filter:
                        filtered_df = filtered_df[filtered_df['Date'] >= date_filter['start']]
                    if 'end' in date_filter:
                        filtered_df = filtered_df[filtered_df['Date'] <= date_filter['end']]
            
            result = {
                "analysis_type": "season_results",
                "season": season,
                "team": "Montreal Canadiens",
                "total_games": len(filtered_df),
                "data_source": str(results_file.name)
            }
            
            if len(filtered_df) > 0:
                result["games"] = filtered_df.to_dict('records')
                
                # Calculate record
                if 'Result' in filtered_df.columns:
                    wins = len(filtered_df[filtered_df['Result'] == 'W'])
                    losses = len(filtered_df[filtered_df['Result'] == 'L'])
                    ot_losses = len(filtered_df[filtered_df['Result'] == 'OTL'])
                    
                    result["record"] = {
                        "wins": wins,
                        "losses": losses,
                        "ot_losses": ot_losses,
                        "record_string": f"{wins}-{losses}-{ot_losses}"
                    }
                
                # Recent games (last 10)
                result["recent_games"] = filtered_df.tail(10).to_dict('records')
            
            # Filter for opponent if specified
            if opponent:
                result["opponent_filter"] = opponent
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading season results: {str(e)}")
            return {
                "analysis_type": "season_results",
                "error": str(e),
                "season": season
            }
    
    async def get_player_stats(
        self,
        player_name: str,
        season: str = "2024-2025",
        team: str = "MTL"
    ) -> Dict[str, Any]:
        """
        Get comprehensive player statistics.
        
        Args:
            player_name: Player name (e.g., "Nick Suzuki", "Cole Caufield")
            season: NHL season
            team: Team abbreviation
            
        Returns:
            Player performance data with all metrics
        """
        try:
            # Try forwards first, then defensemen
            positions_to_try = ["forwards", "defenseman", "goalie"]
            
            for position in positions_to_try:
                player_file = self.catalog.get_player_stats_file(team, position, season)
                
                if not player_file.exists():
                    continue
                
                df = pd.read_parquet(player_file)
                
                # Find player (case-insensitive)
                if 'Player Name' in df.columns:
                    player_row = df[df['Player Name'].str.lower() == player_name.lower()]
                    
                    if len(player_row) > 0:
                        return {
                            "analysis_type": "player_stats",
                            "player_name": player_name,
                            "team": team,
                            "position": position,
                            "season": season,
                            "stats": player_row.iloc[0].to_dict(),
                            "data_source": str(player_file.name)
                        }
            
            # Player not found
            return {
                "analysis_type": "player_stats",
                "error": f"Player '{player_name}' not found in {team} data for {season}",
                "player_name": player_name,
                "season": season
            }
            
        except Exception as e:
            logger.error(f"Error loading player stats: {str(e)}")
            return {
                "analysis_type": "player_stats",
                "error": str(e),
                "player_name": player_name,
                "season": season
            }
    
    async def query_temporal(
        self,
        query: str,
        current_date: str,
        current_season: str
    ) -> Dict[str, Any]:
        """
        Handle temporal queries like "last night", "this season", "last week".
        
        Args:
            query: User query with temporal references
            current_date: Current date (YYYY-MM-DD)
            current_season: Current NHL season
            
        Returns:
            Data filtered by temporal constraints
        """
        query_lower = query.lower()
        current_dt = datetime.fromisoformat(current_date)
        
        # Parse temporal references
        if "last night" in query_lower or "yesterday" in query_lower:
            # Get game from yesterday
            yesterday = current_dt - timedelta(days=1)
            date_filter = {"start": yesterday.strftime("%Y-%m-%d"), "end": yesterday.strftime("%Y-%m-%d")}
            return await self.get_season_results(current_season, date_filter=date_filter)
        
        elif "last week" in query_lower or "past week" in query_lower:
            # Get games from last 7 days
            week_ago = current_dt - timedelta(days=7)
            date_filter = {"start": week_ago.strftime("%Y-%m-%d"), "end": current_date}
            return await self.get_season_results(current_season, date_filter=date_filter)
        
        elif "this season" in query_lower or "current season" in query_lower:
            # Get all games from current season
            return await self.get_season_results(current_season)
        
        elif "last season" in query_lower or "previous season" in query_lower:
            # Calculate previous season
            parts = current_season.split('-')
            prev_season = f"{int(parts[0])-1}-{int(parts[1])-1}"
            return await self.get_season_results(prev_season)
        
        else:
            # No specific temporal reference - return current season
            return await self.get_season_results(current_season)
    
    def _normalize_team_name(self, team: str) -> str:
        """
        Normalize team names to consistent format.
        
        Args:
            team: Team name or abbreviation
            
        Returns:
            Standardized team name
        """
        team_mappings = {
            'toronto': 'Toronto',
            'tor': 'Toronto',
            'maple leafs': 'Toronto',
            'leafs': 'Toronto',
            'boston': 'Boston',
            'bos': 'Boston',
            'bruins': 'Boston',
            'tampa': 'Tampa Bay',
            'tbl': 'Tampa Bay',
            'lightning': 'Tampa Bay',
            'tampa bay': 'Tampa Bay',
            'florida': 'Florida',
            'fla': 'Florida',
            'panthers': 'Florida',
            'detroit': 'Detroit',
            'det': 'Detroit',
            'red wings': 'Detroit',
            'ottawa': 'Ottawa',
            'ott': 'Ottawa',
            'senators': 'Ottawa',
            'buffalo': 'Buffalo',
            'buf': 'Buffalo',
            'sabres': 'Buffalo',
        }
        
        team_lower = team.lower().strip()
        return team_mappings.get(team_lower, team.title())
    
    def _get_all_nhl_teams(self) -> List[str]:
        """Get list of all NHL team abbreviations from processed data directory."""
        # data_root already points to processed/
        teams_dir = Path(self.data_root) / "analytics/nhl_player_stats"
        if not teams_dir.exists():
            return ["MTL"]  # Fallback to Montreal only
        
        teams = []
        for team_dir in teams_dir.iterdir():
            if team_dir.is_dir() and team_dir.name not in [".DS_Store", "__pycache__"]:
                teams.append(team_dir.name)
        
        # Prioritize MTL first (Montreal-focused assistant)
        if "MTL" in teams:
            teams.remove("MTL")
            teams.insert(0, "MTL")
        
        return teams if teams else ["MTL"]
    
    async def get_player_stats(
        self,
        player_name: str,
        season: str = "2024-2025",
        team: str = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for ANY NHL player.
        AI provides the player name and optionally the team.
        If team not specified, searches ALL NHL teams.
        
        Args:
            player_name: Player name (e.g., "Connor McDavid", "Nick Suzuki")
            season: NHL season (default: "2024-2025")
            team: Team abbreviation (e.g., "EDM", "MTL") - if None, searches all teams
        """
        try:
            requested_season = season
            # Determine which teams to search
            teams_to_search = [team] if team else self._get_all_nhl_teams()
            
            # Try all position files for each team
            # Note: Folder names are "forwards_stats", "defenseman_stats", "goalie_stats"
            for team_abbr in teams_to_search:
                for position_folder in ["forwards_stats", "defenseman_stats", "goalie_stats"]:
                    # Map folder names to file naming convention
                    # "forwards_stats" -> "Forwards", "defenseman_stats" -> "Defensemen", "goalie_stats" -> "Goalies"
                    position_file_map = {
                        "forwards_stats": "Forwards",
                        "defenseman_stats": "Defensemen",
                        "goalie_stats": "Goalies"
                    }
                    position_file_name = position_file_map[position_folder]
                    
                    # data_root already points to processed/, just add analytics path
                    stats_file = Path(self.data_root) / f"analytics/nhl_player_stats/{team_abbr}/{season}/{position_folder}/{team_abbr}-{position_file_name}-Comprehensive-{season}.parquet"
                    
                    # Season fallback (use current team, not hardcoded MTL)
                    if not stats_file.exists() and season != "2024-2025":
                        stats_file = Path(self.data_root) / f"analytics/nhl_player_stats/{team_abbr}/2024-2025/{position_folder}/{team_abbr}-{position_file_name}-Comprehensive-2024-2025.parquet"
                        season = "2024-2025"
                    
                    if not stats_file.exists():
                        continue
                    
                    # Load and search flexibly
                    df = pd.read_parquet(stats_file)
                    
                    # Flexible player name matching (case-insensitive, partial match)
                    if 'Player Name' in df.columns:
                        player_df = df[df['Player Name'].str.contains(player_name, case=False, na=False)]
                        
                        if len(player_df) > 0:
                            # Found the player!
                            player_data = player_df.iloc[0].to_dict()
                            
                            # Get full team name from Current Team column or use abbreviation
                            team_name = player_data.get("Current Team", team_abbr)
                            
                            # Convert folder name to readable position
                            position_display = position_folder.replace("_stats", "").replace("man", "")  # defenseman -> defense
                            
                            logger.info(f"✓ Found {player_name} ({team_name}) in {position_file_name} stats")
                            
                            return {
                                "analysis_type": "player_stats",
                                "player_name": player_data.get("Player Name", player_name),
                                "team": team_name,
                                "team_abbr": team_abbr,
                                "position": position_display,
                                "season": season,
                                "requested_season": requested_season if requested_season != season else requested_season,
                            
                            # Core stats
                            "games_played": player_data.get("GP", 0),
                            "goals": player_data.get("G", 0),
                            "assists": player_data.get("A", 0),
                            "points": player_data.get("PTS", 0),
                            
                        # Ice time (calculate total from components)
                        "es_toi": player_data.get("Player ES TOI (Minutes)", 0),
                        "pp_toi": player_data.get("Player PP TOI (Minutes)", 0),
                        "sh_toi": player_data.get("Player SH TOI (Minutes)", 0),
                        "total_toi": (
                            player_data.get("Player ES TOI (Minutes)", 0) + 
                            player_data.get("Player PP TOI (Minutes)", 0) + 
                            player_data.get("Player SH TOI (Minutes)", 0)
                        ),  # Calculate from components
                        "toi_per_game": player_data.get("TOI/GP (min)", "N/A"),  # Formatted string like "20:04"
                        
                        # All stats for comprehensive analysis
                        "all_stats": {k: v for k, v in player_data.items() if not k.startswith('_')},
                        "data_source": str(stats_file.name)
                    }
            
            # Player not found in any team/position searched
            teams_searched_str = ', '.join(teams_to_search) if len(teams_to_search) <= 5 else f"{len(teams_to_search)} NHL teams"
            logger.warning(f"Player '{player_name}' not found across {teams_searched_str}")
            return {
                "analysis_type": "player_stats",
                "error": f"Player {player_name} not found",
                "player_name": player_name,
                "season": season,
                "requested_season": requested_season,
                "teams_searched": teams_searched_str,
                "note": f"Searched {teams_searched_str}. Player may not be on 2024-2025 roster or name may be misspelled"
            }
            
        except Exception as e:
            logger.error(f"Error loading player stats: {str(e)}")
            return {
                "analysis_type": "player_stats",
                "error": str(e),
                "player_name": player_name,
                "season": season,
                "requested_season": requested_season
            }
    
    async def get_comprehensive_query_data(
        self,
        query: str,
        current_date: str,
        current_season: str
    ) -> List[Dict[str, Any]]:
        """
        Intelligent data retrieval based on query content.
        
        Analyzes query keywords and loads relevant data files.
        
        Args:
            query: User's natural language query
            current_date: Current date for temporal queries
            current_season: Current NHL season
            
        Returns:
            List of data dictionaries from relevant sources
        """
        query_lower = query.lower()
        results = []
        
        # Get relevant files from catalog
        keywords = query_lower.split()
        relevant_files = self.catalog.get_files_for_query_type(keywords, current_season)
        
        # Load each relevant file
        for file_path in relevant_files[:5]:  # Limit to 5 files to avoid overload
            if not file_path.exists():
                continue
            
            try:
                df = pd.read_parquet(file_path)
                
                results.append({
                    "source": str(file_path.name),
                    "rows": len(df),
                    "columns": list(df.columns),
                    "sample_data": df.head(5).to_dict('records'),
                    "file_type": self._categorize_file(file_path)
                })
            except Exception as e:
                logger.warning(f"Could not load {file_path}: {e}")
        
        return results
    
    def _categorize_file(self, file_path: Path) -> str:
        """Categorize file by path structure"""
        path_str = str(file_path).lower()
        
        if 'ppunits' in path_str:
            return "power_play"
        elif 'shunits' in path_str:
            return "penalty_kill"
        elif 'matchup' in path_str:
            return "matchups"
        elif 'season_results' in path_str or 'game_results' in path_str:
            return "season_results"
        elif 'forwards' in path_str or 'defenseman' in path_str or 'goalie' in path_str:
            return "player_stats"
        else:
            return "team_stats"
    
    def get_available_data_summary(self) -> Dict[str, Any]:
        """Get summary of all available data sources"""
        available_seasons = self.catalog.get_available_seasons()
        
        return {
            "data_root": str(self.data_root),
            "available_seasons": available_seasons,
            "current_season_data": {
                "power_play": self.catalog.file_exists(self.catalog.get_power_play_file()),
                "matchups": self.catalog.file_exists(self.catalog.get_matchup_report_file()),
                "season_results": self.catalog.file_exists(self.catalog.get_season_results_file()),
                "mtl_forwards": self.catalog.file_exists(self.catalog.get_player_stats_file("MTL", "forwards")),
            }
        }
    
    async def get_mtl_player_game_logs(
        self,
        season: str = "2024-2025",
        window: int = 10
    ) -> pd.DataFrame:
        """
        Get Montreal Canadiens player game-by-game logs for advanced metrics.
        
        Args:
            season: NHL season
            window: Number of recent games to fetch
            
        Returns:
            DataFrame with player game logs (for PFI calculation)
        """
        try:
            # Load comprehensive player stats (which includes game-by-game if available)
            # For now, aggregate from player stats files
            all_players = []
            
            for position_folder in ["forwards_stats", "defenseman_stats"]:
                position_map = {
                    "forwards_stats": "Forwards",
                    "defenseman_stats": "Defensemen"
                }
                position_name = position_map[position_folder]
                
                stats_file = Path(self.data_root) / f"analytics/nhl_player_stats/MTL/{season}/{position_folder}/MTL-{position_name}-Comprehensive-{season}.parquet"
                
                if not stats_file.exists():
                    continue
                
                df = pd.read_parquet(stats_file)
                all_players.append(df)
            
            if all_players:
                return pd.concat(all_players, ignore_index=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading MTL player game logs: {str(e)}")
            return pd.DataFrame()
    
    async def get_mtl_team_game_logs(
        self,
        season: str = "2024-2025",
        window: int = 10
    ) -> pd.DataFrame:
        """
        Get Montreal Canadiens team game-by-game stats for trend analysis.
        
        Args:
            season: NHL season
            window: Number of recent games
            
        Returns:
            DataFrame with team game logs
        """
        try:
            # Load from season results and team stats
            results_file = Path(self.data_root) / f"analytics/mtl_season_results/{season}/mtl_season_game_results_{season}.parquet"
            
            if results_file.exists():
                df = pd.read_parquet(results_file)
                return df.tail(window)
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error loading MTL team game logs: {str(e)}")
            return pd.DataFrame()
    
    async def get_division_teams_data(
        self,
        division: str = "Atlantic",
        season: str = "2024-2025",
        window: int = 10
    ) -> pd.DataFrame:
        """
        Get data for all teams in a division for rival threat index.
        
        Args:
            division: Division name (Atlantic, Metropolitan, etc.)
            season: NHL season
            window: Number of recent games
            
        Returns:
            DataFrame with division team stats
        """
        try:
            # Atlantic Division teams (fixed set)
            atlantic_teams = ['BOS', 'TOR', 'FLA', 'TBL', 'BUF', 'DET', 'OTT', 'MTL']

            frames: List[pd.DataFrame] = []

            # 1) Use local MTL game results if available
            try:
                results_file = Path(self.data_root) / f"analytics/mtl_season_results/{season}/mtl_season_game_results_{season}.parquet"
                if results_file.exists():
                    df_mtl = pd.read_parquet(results_file)
                    df_mtl = df_mtl.tail(window).copy()
                    df_mtl['Team'] = 'MTL'
                    frames.append(df_mtl)
            except Exception as e:
                logger.warning(f"Could not load MTL season results for division data: {e}")

            # 2) For other teams, derive recent results via NHL API scoreboard (fallback)
            for team in atlantic_teams:
                if team == 'MTL':
                    continue
                key = f"team_recent:{team}:{window}"
                cached = self._team_recent_cache.get(key)
                if cached and cached.get('expires_at', datetime.min) > datetime.utcnow():
                    frames.append(cached['df'])
                    continue

                df_recent = await self._fetch_team_recent_results_via_nhl_api(team, window)
                # Cache briefly to avoid repeated calls within the same request burst
                self._team_recent_cache[key] = {
                    'df': df_recent,
                    'expires_at': datetime.utcnow() + timedelta(seconds=self._score_cache_ttl_seconds)
                }
                frames.append(df_recent)

            if frames:
                # Normalize columns present across frames
                cols = ['Team', 'XGF', 'XGA', 'Points', 'PP%', 'PK%', 'GF_5v5', 'GA_5v5', 'Result']
                norm_frames = []
                for f in frames:
                    for c in cols:
                        if c not in f.columns:
                            f[c] = None
                    norm_frames.append(f[cols])
                return pd.concat(norm_frames, ignore_index=True)

            # Empty fallback
            return pd.DataFrame(columns=['Team', 'XGF', 'XGA', 'Points', 'PP%', 'PK%', 'GF_5v5', 'GA_5v5', 'Result'])

        except Exception as e:
            logger.error(f"Error loading division teams data: {str(e)}")
            return pd.DataFrame(columns=['Team', 'XGF', 'XGA', 'Points', 'PP%', 'PK%', 'GF_5v5', 'GA_5v5', 'Result'])

    async def _fetch_team_recent_results_via_nhl_api(self, team: str, window: int) -> pd.DataFrame:
        """Fetch last N completed games for a team using NHL scoreboard and derive minimal metrics.

        Returns a DataFrame with columns: Team, Points, Result and placeholders for others.
        """
        rows: List[Dict[str, Any]] = []
        # Search back up to 30 days (was 45); combined with global cache this minimizes requests
        days_back = 0
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Limit days scanned (cap at 30) to avoid excessive external requests
            max_days = 30
            while len(rows) < window and days_back < max_days:
                date = (datetime.utcnow() - timedelta(days=days_back)).date().isoformat()
                days_back += 1
                # Per-date cache (local & global to dampen bursts across requests)
                now = datetime.utcnow()
                data = None
                cache = self._score_cache.get(date)
                if cache and cache.get('expires_at', datetime.min) > now:
                    data = cache['data']
                else:
                    gcache = _GLOBAL_SCORE_CACHE.get(date)
                    if gcache and gcache.get('expires_at', datetime.min) > now:
                        data = gcache['data']
                if data is None:
                    try:
                        resp = await client.get(
                            f"https://api-web.nhle.com/v1/score/{date}",
                            headers={"Accept": "application/json"}
                        )
                        if resp.status_code != 200:
                            continue
                        data = resp.json()
                        # Populate both caches
                        self._score_cache[date] = {
                            'data': data,
                            'expires_at': now + timedelta(seconds=self._score_cache_ttl_seconds)
                        }
                        _GLOBAL_SCORE_CACHE[date] = {
                            'data': data,
                            'expires_at': now + timedelta(seconds=_GLOBAL_SCORE_TTL_SECONDS)
                        }
                    except Exception:
                        continue

                games = data.get('games', []) if isinstance(data, dict) else []
                for g in games:
                    try:
                        home = g.get('homeTeam', {}) or g.get('home', {})
                        away = g.get('awayTeam', {}) or g.get('away', {})
                        home_abbr = home.get('abbrev')
                        away_abbr = away.get('abbrev')
                        if home_abbr != team and away_abbr != team:
                            continue
                        if str(g.get('gameState')).upper() not in ("FINAL", "OFF"):
                            # skip non-final games for stable metrics
                            continue
                        home_score = int(home.get('score', 0) or g.get('homeScore', 0))
                        away_score = int(away.get('score', 0) or g.get('awayScore', 0))
                        last_type = (g.get('gameOutcome', {}) or {}).get('lastPeriodType') or ''

                        team_is_home = (home_abbr == team)
                        team_score = home_score if team_is_home else away_score
                        opp_score = away_score if team_is_home else home_score

                        if team_score > opp_score:
                            result = 'W'
                            points = 2
                        else:
                            # Overtime/SO loss earns 1 point
                            result = 'OTL' if str(last_type) in ("OT", "SO") else 'L'
                            points = 1 if result == 'OTL' else 0

                        rows.append({
                            'Team': team,
                            'Points': points,
                            'Result': result,
                            # Placeholders for analytics composites (handled gracefully downstream)
                            'XGF': None,
                            'XGA': None,
                            'PP%': None,
                            'PK%': None,
                            'GF_5v5': None,
                            'GA_5v5': None,
                        })
                        if len(rows) >= window:
                            break
                    except Exception:
                        continue

        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame(columns=['Team', 'XGF', 'XGA', 'Points', 'PP%', 'PK%', 'GF_5v5', 'GA_5v5', 'Result'])
