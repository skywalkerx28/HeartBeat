"""
HeartBeat Engine - Parquet Analytics Node
Montreal Canadiens Advanced Analytics Assistant

Performs real-time analytics queries on Parquet data files.
Provides statistical analysis, player metrics, and game data.
"""

from typing import List, Dict, Any, Optional, Union
import logging
from datetime import datetime
import os
from pathlib import Path

try:
    import pandas as pd
    import pyarrow.parquet as pq
except ImportError:
    pd = None
    pq = None

from orchestrator.utils.state import (
    AgentState,
    ToolResult,
    ToolType,
    update_state_step,
    add_tool_result,
    add_error
)
from orchestrator.config.settings import settings
from orchestrator.tools.parquet_data_client_v2 import ParquetDataClientV2

logger = logging.getLogger(__name__)

# Lazy import for BigQuery client (only loaded if USE_BIGQUERY_ANALYTICS=true)
_AnalyticsDataClientBQ = None

def _get_bq_client_class():
    """Lazy load BigQuery client to avoid import errors if not needed."""
    global _AnalyticsDataClientBQ
    if _AnalyticsDataClientBQ is None:
        try:
            from orchestrator.tools.analytics_data_client_bq import AnalyticsDataClientBQ
            _AnalyticsDataClientBQ = AnalyticsDataClientBQ
        except ImportError as e:
            logger.warning(f"BigQuery client not available: {e}")
            _AnalyticsDataClientBQ = False
    return _AnalyticsDataClientBQ

class ParquetAnalyzerNode:
    """
    Performs analytics queries on Parquet data files.
    
    Capabilities:
    - Player performance statistics
    - Team analytics and metrics
    - Game-by-game analysis
    - Advanced hockey metrics calculation
    - Comparative analysis and matchups
    """
    
    def __init__(self):
        self.data_directory = Path(settings.parquet.data_directory)
        self.cache = {} if settings.parquet.cache_enabled else None
        self.cache_ttl = settings.parquet.cache_ttl_seconds
        
        # Real data client for Montreal Canadiens analytics (Parquet-first)
        self.data_client = ParquetDataClientV2(str(self.data_directory))
        
        # GCP Phase 1: BigQuery analytics client (optional, controlled by env)
        self.use_bigquery = settings.bigquery.enabled
        self.bq_client = None
        
        if self.use_bigquery:
            BQClientClass = _get_bq_client_class()
            if BQClientClass and BQClientClass is not False:
                try:
                    self.bq_client = BQClientClass(
                        project_id=settings.bigquery.project_id,
                        dataset_core=settings.bigquery.dataset_core,
                        dataset_raw=settings.bigquery.dataset_raw
                    )
                    logger.info(
                        f"BigQuery analytics enabled: "
                        f"{settings.bigquery.project_id}.{settings.bigquery.dataset_core}"
                    )
                except Exception as e:
                    logger.warning(f"BigQuery client initialization failed: {e}")
                    logger.info("Falling back to Parquet-only mode")
                    self.use_bigquery = False
                    self.bq_client = None
            else:
                logger.info("BigQuery client not available, using Parquet-only")
                self.use_bigquery = False
        
        # Legacy data files mapping (kept for compatibility)
        self.data_files = {
            "player_stats": "fact/player_game_stats.parquet",
            "team_stats": "fact/team_game_stats.parquet", 
            "play_by_play": "fact/play_by_play_events.parquet",
            "line_combinations": "dim/line_combinations.parquet",
            "player_info": "dim/players.parquet",
            "team_info": "dim/teams.parquet",
            "game_info": "dim/games.parquet"
        }
        
        self._validate_data_availability()
    
    def _validate_data_availability(self) -> None:
        """Validate that required data files are available"""
        
        missing_files = []
        
        for data_type, file_path in self.data_files.items():
            full_path = self.data_directory / file_path
            if not full_path.exists():
                missing_files.append(f"{data_type}: {file_path}")
        
        if missing_files:
            logger.warning(f"Missing Parquet data files: {missing_files}")
        else:
            logger.info("All Parquet data files validated successfully")

    async def analyze(self, query_description: str, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Lightweight analysis entrypoint for agent tool-calls.

        Accepts a natural language description (e.g., "Nick Suzuki 2023-2024 season stats")
        and returns a compact stats payload using ParquetDataClientV2.
        """
        # Determine season
        detected_season = season or self._extract_season_from_text(query_description) or "2024-2025"

        # Try to extract player name robustly
        player_name = self._extract_player_name_from_query(query_description)
        if not player_name:
            player_name = self._extract_capitalized_name(query_description)

        if player_name:
            try:
                stats = await self.data_client.get_player_stats(
                    player_name=player_name,
                    season=detected_season
                )
                # If data client used a fallback season, surface both
                if isinstance(stats, dict):
                    stats.setdefault("requested_season", detected_season)
                return stats
            except Exception as e:
                logger.error(f"analyze() player stats failed: {e}")

        # Fallback: season results (if query looks like season stats without clear player)
        try:
            return await self.data_client.get_season_results(
                season=detected_season
            )
        except Exception as e:
            logger.error(f"analyze() season results failed: {e}")
            return {"error": str(e), "analysis_type": "unknown"}
    
    async def process(self, state: AgentState) -> AgentState:
        """Process Parquet analytics queries"""
        
        state = update_state_step(state, "parquet_analysis")
        start_time = datetime.now()
        
        if not pd or not pq:
            return self._handle_unavailable_libraries(state, start_time)
        
        try:
            # Extract analysis parameters
            query = state["original_query"]
            user_context = state["user_context"]
            intent_analysis = state["intent_analysis"]
            required_tools = state["required_tools"]
            
            logger.info(f"Performing analytics for query: {query[:100]}...")
            
            # Extract time context from state for temporal queries
            current_season = state.get("current_season", "2024-2025")
            current_date = state.get("current_date", "")
            
            # Determine analysis type and execute
            analytics_results = await self._execute_analytics(
                query=query,
                user_context=user_context,
                intent_analysis=intent_analysis,
                required_tools=required_tools,
                current_season=current_season,
                current_date=current_date
            )
            
            # Calculate execution time
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Create tool result
            tool_result = ToolResult(
                tool_type=ToolType.PARQUET_QUERY,
                success=len(analytics_results) > 0,
                data=analytics_results,
                execution_time_ms=execution_time,
                citations=self._generate_citations(analytics_results)
            )
            
            # Update state
            state["analytics_data"] = analytics_results
            state = add_tool_result(state, tool_result)
            
            logger.info(f"Analytics completed in {execution_time}ms with {len(analytics_results)} results")
            
        except Exception as e:
            logger.error(f"Error in Parquet analysis: {str(e)}")
            state = add_error(state, f"Analytics query failed: {str(e)}")
            
            # Add failed tool result
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            tool_result = ToolResult(
                tool_type=ToolType.PARQUET_QUERY,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
            state = add_tool_result(state, tool_result)
        
        return state

    def _extract_season_from_text(self, text: str) -> Optional[str]:
        """Extract season string like 2023-2024 from free text."""
        import re
        m = re.search(r"(20\d{2})[\-\/]?(20\d{2})", text)
        if not m:
            # Try single year pattern (e.g., 2024) → infer season around Oct-Jun is complex; return None
            return None
        y1, y2 = m.group(1), m.group(2)
        # Normalize to YYYY-YYYY
        return f"{y1}-{y2}"

    def _extract_capitalized_name(self, text: str) -> Optional[str]:
        """Best-effort: pick the first two-capitalized-words sequence as a name."""
        import re
        candidates = re.findall(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", text)
        if not candidates:
            return None
        # Filter out common non-player terms
        bad = {"Montreal Canadiens", "New York", "Maple Leafs"}
        for c in candidates:
            if c not in bad:
                return c
        return candidates[0]
    
    async def _execute_analytics(
        self,
        query: str,
        user_context,
        intent_analysis: Dict[str, Any],
        required_tools: List[ToolType],
        current_season: str = "2024-2025",
        current_date: str = ""
    ) -> Dict[str, Any]:
        """Execute appropriate analytics using V2 data client"""
        
        query_lower = query.lower()
        
        # PRIORITY 1: Player-specific queries (check FIRST before anything else)
        player_name = self._extract_player_name_from_query(query)
        if player_name:
            logger.info(f"PLAYER QUERY DETECTED: {player_name}")
            
            # Try BigQuery first if enabled
            if self.use_bigquery and self.bq_client:
                try:
                    logger.info("Attempting BigQuery analytics...")
                    return await self.bq_client.get_player_stats(
                        player_name=player_name,
                        season=current_season
                    )
                except Exception as e:
                    logger.warning(f"BigQuery failed: {e}, falling back to Parquet")
            
            # Fallback to Parquet (current production path)
            return await self.data_client.get_player_stats(
                player_name=player_name,
                season=current_season
            )
        
        # Extract opponent (will be used across multiple query types)
        opponent = self._extract_opponent_from_query(query)
        
        # PRIORITY 2: Power play queries
        if any(kw in query_lower for kw in ['power play', 'pp', 'powerplay', 'man advantage']):
            return await self.data_client.get_power_play_stats(
                opponent=opponent,
                season=current_season
            )
        
        # Matchup queries - COMPREHENSIVE DATA GATHERING!
        elif opponent:  # If opponent detected, gather ALL relevant data
            logger.info(f"Detected matchup query for opponent: {opponent}")
            logger.info(f"Gathering COMPREHENSIVE data: matchup metrics + game results")
            
            # Try BigQuery first if enabled
            if self.use_bigquery and self.bq_client:
                try:
                    logger.info("Attempting BigQuery matchup analytics...")
                    matchup_data = await self.bq_client.get_matchup_data(
                        opponent=opponent,
                        season=current_season
                    )
                    season_data = await self.bq_client.get_season_results(
                        opponent=opponent,
                        season=current_season
                    )
                except Exception as e:
                    logger.warning(f"BigQuery failed: {e}, falling back to Parquet")
                    matchup_data = await self.data_client.get_matchup_data(
                        opponent=opponent,
                        season=current_season
                    )
                    season_data = await self.data_client.get_season_results(
                        opponent=opponent,
                        season=current_season
                    )
            else:
                # Fallback to Parquet
                matchup_data = await self.data_client.get_matchup_data(
                    opponent=opponent,
                    season=current_season
                )
                season_data = await self.data_client.get_season_results(
                    opponent=opponent,
                    season=current_season
                )
            
            logger.info(f"Season data returned: {season_data.get('analysis_type') if season_data else 'None'}, games: {season_data.get('total_games', 0) if season_data else 0}, record: {season_data.get('record') if season_data else 'None'}")
            
            # Combine both data sources for comprehensive view
            comprehensive_matchup = {
                "analysis_type": "comprehensive_matchup",
                "opponent": opponent,
                "season": matchup_data.get("season", current_season),
                
                # Matchup metrics (xG, Corsi, etc.)
                "matchup_metrics": {
                    "total_metrics": matchup_data.get("total_matchup_rows", 0),
                    "key_metrics": matchup_data.get("key_metrics", {}),
                },
                
                # Game results (W/L record)  
                "game_results": {
                    "total_games": season_data.get("total_games", 0) if season_data else 0,
                    "wins": season_data.get("record", {}).get("wins", 0) if (season_data and season_data.get("record")) else 0,
                    "losses": season_data.get("record", {}).get("losses", 0) if (season_data and season_data.get("record")) else 0,
                    "ot_losses": season_data.get("record", {}).get("ot_losses", 0) if (season_data and season_data.get("record")) else 0,
                    "record_string": season_data.get("record", {}).get("record_string", "") if (season_data and season_data.get("record")) else "",
                    "games": season_data.get("games", [])[:10] if season_data else []  # First 10 game details
                },
                
                # Summary
                "summary": f"MTL vs {opponent} ({matchup_data.get('season')}): {season_data.get('record', {}).get('record_string', 'N/A') if season_data else 'N/A'} record, {matchup_data.get('total_matchup_rows', 0)} advanced metrics"
            }
            
            logger.info(f"✓ Comprehensive data: {comprehensive_matchup['summary']}")
            return comprehensive_matchup
        
        # Also catch explicit matchup keywords
        elif any(kw in query_lower for kw in ['vs', 'against', 'matchup', 'versus']):
            # Try to extract opponent again with more flexible matching
            logger.info("Matchup keyword detected, extracting opponent...")
            opponent = self._extract_opponent_from_query(query)
            if opponent:
                return await self.data_client.get_matchup_data(
                    opponent=opponent,
                    season=current_season
                )
        
        # Season/game results
        elif any(kw in query_lower for kw in ['game', 'result', 'record', 'score', 'last night', 'yesterday']):
            # Handle temporal queries
            if "last night" in query_lower or "yesterday" in query_lower:
                return await self.data_client.query_temporal(query, current_date, current_season)
            else:
                opponent = self._extract_opponent_from_query(query)
                return await self.data_client.get_season_results(
                    season=current_season,
                    opponent=opponent
                )
        
        # Player-specific queries
        elif any(name in query_lower for name in ['suzuki', 'caufield', 'laine', 'hutson', 'slafkovsky', 'gallagher']):
            # Extract player name
            for name in ['Nick Suzuki', 'Cole Caufield', 'Patrik Laine', 'Lane Hutson', 'Juraj Slafkovsky', 'Brendan Gallagher']:
                if name.lower() in query_lower:
                    return await self.data_client.get_player_stats(
                        player_name=name,
                        season=current_season
                    )
        
        # Fallback: comprehensive query returns List, wrap in Dict
        comprehensive_data = await self.data_client.get_comprehensive_query_data(
            query=query,
            current_date=current_date,
            current_season=current_season
        )
        
        # Wrap list result in dict for consistent return type
        return {
            "analysis_type": "comprehensive_query",
            "season": current_season,
            "data_sources": comprehensive_data,
            "total_sources": len(comprehensive_data) if comprehensive_data else 0
        }
    
    async def _analyze_player_performance(
        self, 
        query: str, 
        user_context
    ) -> Dict[str, Any]:
        """Analyze individual player performance metrics using real data"""
        
        # Extract player names from query
        players = self._extract_player_names(query)
        timeframe = self._extract_timeframe(query)
        
        try:
            # Use new NHL player stats method for comprehensive data
            real_data = await self.data_client.get_nhl_player_stats(
                team="MTL",
                player_names=players,
                season="2024-2025"
            )
            
            # If real data fails, fallback to mock
            if "error" in real_data:
                logger.warning(f"Real data failed: {real_data['error']}, using fallback")
                return {
                    "analysis_type": "player_performance_fallback",
                    "players": players,
                    "metrics": self._get_mock_player_stats(players),
                    "timeframe": timeframe,
                    "data_source": "fallback_data",
                    "note": "Using fallback data due to: " + real_data['error']
                }
            
            return real_data
            
        except Exception as e:
            logger.error(f"Player analysis failed: {str(e)}")
            return {"error": f"Player analysis failed: {str(e)}"}
    
    async def _analyze_team_performance(
        self, 
        query: str, 
        user_context
    ) -> Dict[str, Any]:
        """Analyze team performance and statistics"""
        
        try:
            # Extract team context (defaulting to MTL for Montreal Canadiens users)
            team = "MTL" if "MTL" in user_context.team_access else "MTL"
            
            results = {
                "analysis_type": "team_performance",
                "team": team,
                "metrics": self._get_mock_team_stats(team),
                "timeframe": self._extract_timeframe(query),
                "data_source": "team_game_stats.parquet"
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Team analysis failed: {str(e)}")
            return {"error": f"Team analysis failed: {str(e)}"}
    
    async def _analyze_game_data(
        self, 
        query: str, 
        user_context
    ) -> Dict[str, Any]:
        """Analyze specific game data and events"""
        
        try:
            # Prefer BigQuery if enabled and available
            team = None
            try:
                # Try to infer team from user context first
                team = getattr(user_context, 'default_team', None) or 'MTL'
            except Exception:
                team = 'MTL'

            if self.use_bigquery and self.bq_client:
                season = self._extract_season_from_text(query) or "2025-2026"
                try:
                    bq = await self.bq_client.get_recent_game_events(team=team, season=season, limit=500)
                    if isinstance(bq, dict) and bq.get('rows', 0) > 0:
                        bq['timeframe'] = self._extract_timeframe(query)
                        return bq
                except Exception as e:
                    logger.warning(f"BigQuery game analysis fallback: {e}")

            # Fallback mock if BigQuery not enabled or no data
            return {
                "analysis_type": "game_analysis",
                "game_data": self._get_mock_game_analysis(),
                "timeframe": self._extract_timeframe(query),
                "data_source": "play_by_play_events.parquet"
            }
            
        except Exception as e:
            logger.error(f"Game analysis failed: {str(e)}")
            return {"error": f"Game analysis failed: {str(e)}"}
    
    async def _analyze_matchups(
        self, 
        query: str, 
        user_context
    ) -> Dict[str, Any]:
        """Analyze player or team matchups and comparisons - USES REAL DATA"""
        
        try:
            # Extract opponent from query
            opponent = self._extract_opponent_from_query(query)
            
            if not opponent:
                # Fallback to general matchup data
                return await self.data_client.get_matchup_analysis("all")
            
            # Check if query is about power play
            is_power_play = any(keyword in query.lower() for keyword in ['power play', 'pp', 'powerplay', 'man advantage'])
            
            if is_power_play:
                # Get power play specific data
                pp_data = await self.data_client.get_power_play_stats(opponent=opponent)
                matchup_data = await self.data_client.get_matchup_analysis(opponent=opponent)
                
                results = {
                    "analysis_type": "power_play_matchup",
                    "opponent": opponent,
                    "power_play_data": pp_data,
                    "matchup_context": matchup_data,
                    "data_source": "real_parquet_data"
                }
            else:
                # General matchup analysis
                results = await self.data_client.get_matchup_analysis(opponent=opponent)
            
            return results
            
        except Exception as e:
            logger.error(f"Matchup analysis failed: {str(e)}")
            return {"error": f"Matchup analysis failed: {str(e)}"}
    
    async def _execute_statistical_query(
        self, 
        query: str, 
        user_context
    ) -> Dict[str, Any]:
        """Execute direct statistical queries"""
        
        try:
            # Parse statistical request
            stat_type = self._identify_stat_type(query)
            
            results = {
                "analysis_type": "statistical_query",
                "stat_type": stat_type,
                "results": self._get_mock_statistical_data(stat_type),
                "data_source": "fact_tables"
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Statistical query failed: {str(e)}")
            return {"error": f"Statistical query failed: {str(e)}"}
    
    async def _execute_general_analytics(
        self, 
        query: str, 
        user_context
    ) -> Dict[str, Any]:
        """Execute general analytics for unclassified queries"""
        
        try:
            results = {
                "analysis_type": "general_analytics",
                "summary": "General hockey analytics data",
                "data": self._get_mock_general_data(),
                "data_source": "multiple_sources"
            }
            
            return results
            
        except Exception as e:
            logger.error(f"General analytics failed: {str(e)}")
            return {"error": f"General analytics failed: {str(e)}"}
    
    def _extract_player_names(self, query: str) -> List[str]:
        """Extract player names from query text"""
        
        # Common Montreal Canadiens players (2024-25 season)
        known_players = [
            "suzuki", "caufield", "hutson", "slafkovsky", "guhle", 
            "matheson", "dach", "newhook", "gallagher", "anderson",
            "montembeault", "primeau", "dvorak", "armia", "evans"
        ]
        
        found_players = []
        query_lower = query.lower()
        
        for player in known_players:
            if player in query_lower:
                found_players.append(player.capitalize())
        
        return found_players
    
    def _extract_timeframe(self, query: str) -> str:
        """Extract timeframe information from query"""
        
        timeframe_patterns = {
            "last game": "last_game",
            "last 5 games": "last_5_games", 
            "last 10 games": "last_10_games",
            "this season": "current_season",
            "career": "career",
            "this month": "current_month"
        }
        
        query_lower = query.lower()
        
        for pattern, timeframe in timeframe_patterns.items():
            if pattern in query_lower:
                return timeframe
        
        return "current_season"  # default
    
    def _extract_player_name_from_query(self, query: str) -> Optional[str]:
        """
        Let the AI TELL US what player name is in the query.
        No hardcoded lists - pure intelligent extraction.
        
        This is a simple heuristic: if query contains words like "player", "stats", "performance"
        followed by capitalized words, extract those as potential player name.
        """
        # Simple detection: if query contains stats/player keywords
        # AND has capitalized words, extract those as player name
        stats_keywords = ['stats', 'statistics', 'performance', 'show me', 'how is', 'how did']
        
        if any(kw in query.lower() for kw in stats_keywords):
            # Extract capitalized words (likely player names)
            import re
            # Find sequences of capitalized words
            pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
            matches = re.findall(pattern, query)
            
            # Filter out common non-names (do not exclude legitimate first names like 'Nick')
            excluded = ['Montreal', 'Canadiens', 'Toronto', 'Season', 'Show']
            player_candidates = [m for m in matches if m not in excluded and len(m.split()) <= 3]
            
            if player_candidates:
                # Take the first capitalized sequence as player name
                player_name = player_candidates[0]
                logger.info(f"AI extracted player name from query: '{player_name}'")
                return player_name
        
        return None
    
    def _extract_opponent_from_query(self, query: str) -> Optional[str]:
        """
        Extract opponent team name from query.
        
        Returns:
            Opponent team name/abbreviation or None
        """
        # NHL team mappings (including common typos)
        team_mappings = {
            'toronto': 'TOR',
            'toronot': 'TOR',  # Common typo
            'maple leafs': 'TOR',
            'leafs': 'TOR',
            'boston': 'BOS',
            'bruins': 'BOS',
            'new york': 'NYR',
            'rangers': 'NYR',
            'tampa': 'TBL',
            'lightning': 'TBL',
            'florida': 'FLA',
            'panthers': 'FLA',
            'detroit': 'DET',
            'red wings': 'DET',
            'buffalo': 'BUF',
            'sabres': 'BUF',
            'ottawa': 'OTT',
            'senators': 'OTT',
            'pittsburgh': 'PIT',
            'penguins': 'PIT',
            'washington': 'WSH',
            'capitals': 'WSH',
            'carolina': 'CAR',
            'hurricanes': 'CAR',
            'columbus': 'CBJ',
            'blue jackets': 'CBJ',
            'new jersey': 'NJD',
            'devils': 'NJD',
            'philadelphia': 'PHI',
            'flyers': 'PHI',
            'islanders': 'NYI',
            'vegas': 'VGK',
            'golden knights': 'VGK',
            'colorado': 'COL',
            'avalanche': 'COL',
            'edmonton': 'EDM',
            'oilers': 'EDM',
            'calgary': 'CGY',
            'flames': 'CGY',
            'vancouver': 'VAN',
            'canucks': 'VAN',
            'seattle': 'SEA',
            'kraken': 'SEA',
            'winnipeg': 'WPG',
            'jets': 'WPG'
        }
        
        query_lower = query.lower()
        
        # Check for team names in query
        for team_name, abbrev in team_mappings.items():
            if team_name in query_lower:
                return abbrev
        
        # Check for common patterns like "vs TOR" or "against TOR"
        import re
        patterns = [
            r'vs\.?\s+([A-Z]{3})',
            r'against\s+([A-Z]{3})',
            r'versus\s+([A-Z]{3})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_comparison_entities(self, query: str) -> List[str]:
        """Extract entities being compared in matchup queries"""
        
        # Simple extraction based on common comparison patterns
        entities = []
        
        # Look for "vs", "versus", "compared to" patterns
        if " vs " in query.lower():
            parts = query.lower().split(" vs ")
            entities = [part.strip() for part in parts[:2]]
        elif " versus " in query.lower():
            parts = query.lower().split(" versus ")
            entities = [part.strip() for part in parts[:2]]
        
        return entities
    
    def _identify_stat_type(self, query: str) -> str:
        """Identify the type of statistic being requested"""
        
        stat_indicators = {
            "goals": ["goal", "goals", "scoring"],
            "assists": ["assist", "assists", "playmaking"],
            "points": ["point", "points", "production"],
            "shots": ["shot", "shots", "shooting"],
            "hits": ["hit", "hits", "physical"],
            "blocks": ["block", "blocks", "blocked"],
            "saves": ["save", "saves", "goaltending"],
            "wins": ["win", "wins", "record"]
        }
        
        query_lower = query.lower()
        
        for stat_type, indicators in stat_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return stat_type
        
        return "general_stats"
    
    # Mock data generation methods (to be replaced with real Parquet queries)
    
    def _get_mock_player_stats(self, players: List[str]) -> Dict[str, Any]:
        """Generate mock player statistics"""
        
        return {
            player: {
                "games_played": 25,
                "goals": 8,
                "assists": 12,
                "points": 20,
                "shots": 65,
                "shooting_percentage": 12.3,
                "plus_minus": 2,
                "time_on_ice_avg": "18:45"
            }
            for player in players
        }
    
    def _get_mock_team_stats(self, team: str) -> Dict[str, Any]:
        """Generate mock team statistics"""
        
        return {
            "record": {"wins": 12, "losses": 10, "overtime": 3},
            "goals_for": 78,
            "goals_against": 75,
            "powerplay_percentage": 22.5,
            "penalty_kill_percentage": 81.2,
            "shots_for_avg": 32.1,
            "shots_against_avg": 29.8,
            "faceoff_percentage": 50.8
        }
    
    def _get_mock_game_analysis(self) -> Dict[str, Any]:
        """Generate mock game analysis data"""
        
        return {
            "last_game": {
                "opponent": "Toronto Maple Leafs",
                "score": "4-2",
                "result": "Win",
                "key_events": ["Power play goal", "Short-handed goal", "Empty net goal"],
                "top_performers": ["Suzuki (2G, 1A)", "Caufield (1G, 1A)"]
            }
        }
    
    def _get_mock_matchup_data(self, entities: List[str]) -> Dict[str, Any]:
        """Generate mock matchup comparison data"""
        
        return {
            "comparison": f"{entities[0] if entities else 'Team A'} vs {entities[1] if len(entities) > 1 else 'Team B'}",
            "metrics": {
                "head_to_head_record": "2-1-0",
                "goals_for_comparison": {"team_a": 3.2, "team_b": 2.8},
                "powerplay_comparison": {"team_a": 25.0, "team_b": 18.5}
            }
        }
    
    def _get_mock_statistical_data(self, stat_type: str) -> Dict[str, Any]:
        """Generate mock statistical data"""
        
        return {
            "stat_type": stat_type,
            "value": 42,
            "rank": "3rd in team",
            "league_average": 38.5,
            "percentile": 75
        }
    
    def _get_mock_general_data(self) -> Dict[str, Any]:
        """Generate mock general analytics data"""
        
        return {
            "team_summary": "Montreal Canadiens current season overview",
            "key_metrics": {
                "record": "12-10-3",
                "points_percentage": 54.0,
                "goal_differential": "+3"
            }
        }
    
    def _generate_citations(self, analytics_results: Dict[str, Any]) -> List[str]:
        """Generate citations for analytics results"""
        
        citations = []
        
        data_source = analytics_results.get("data_source", "parquet_data")
        analysis_type = analytics_results.get("analysis_type", "analytics")
        
        citations.append(f"[{data_source}:{analysis_type}]")
        
        return citations
    
    def _handle_unavailable_libraries(
        self, 
        state: AgentState, 
        start_time: datetime
    ) -> AgentState:
        """Handle case when pandas/pyarrow libraries are unavailable"""
        
        logger.error("Pandas/PyArrow libraries not available")
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        tool_result = ToolResult(
            tool_type=ToolType.PARQUET_QUERY,
            success=False,
            error="Analytics libraries not available. Install with: pip install pandas pyarrow",
            execution_time_ms=execution_time
        )
        
        state = add_tool_result(state, tool_result)
        state = add_error(state, "Parquet analytics unavailable - missing dependencies")
        
        return state
