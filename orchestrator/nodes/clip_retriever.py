"""
HeartBeat Engine - Video Clip Retriever Node
Montreal Canadiens Advanced Analytics Assistant

Retrieves video clips based on natural language queries.
Provides player-specific highlights, game footage, and event clips.
Supports hockey-specific terminology: "shifts" = sequences of play/clips.

UPDATED: Now uses clip_query and clip_cutter tools for period-based clip extraction
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import re
from pathlib import Path
import sys

from orchestrator.utils.state import (
    AgentState,
    ToolResult,
    ToolType,
    update_state_step,
    add_tool_result,
    add_error
)
from orchestrator.config.settings import settings

# Import our clip tools
sys.path.append(str(Path(__file__).parent.parent))
from tools.clip_query import ClipQueryTool, ClipSearchParams as QuerySearchParams, ClipSegment
from tools.clip_cutter import FFmpegClipCutter, ClipCutRequest

logger = logging.getLogger(__name__)

class ClipRetrieverNode:
    """
    Retrieves video clips based on natural language queries.
    
    Capabilities:
    - Player-specific clip retrieval
    - Event-based clip filtering
    - Time-based clip searches
    - Game-specific highlights
    - Team-wide clip collections
    """
    
    def __init__(self):
        # Initialize clip query and cutter tools
        workspace_root = Path(__file__).parent.parent.parent
        self.query_tool = ClipQueryTool(
            extracted_metrics_dir=str(workspace_root / "data/processed/extracted_metrics"),
            clips_dir=str(workspace_root / "data/clips")
        )
        self.cutter = FFmpegClipCutter(
            output_base_dir=str(workspace_root / "data/clips/generated"),
            max_workers=3
        )
        
        # Cache for recent queries
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Montreal Canadiens players for name matching
        self.mtl_players = {
            # Forwards
            'nick suzuki', 'cole caufield', 'juraj slafkovsky', 'kirby dach',
            'alex newhook', 'brendan gallagher', 'josh anderson', 'jake evans',
            'joel armia', 'christian dvorak', 'emil heineman', 'oliver kapanen',
            'owen beck', 'joshua roy', 'rafael harvey-pinard',
            
            # Defensemen
            'lane hutson', 'kaiden guhle', 'mike matheson', 'david savard',
            'arber xhekaj', 'jayden struble', 'justin barron', 'logan mailloux',
            'adam engstrom',
            
            # Goalies
            'samuel montembeault', 'cayden primeau', 'jakub dobes',
            
            # Common short names and nicknames
            'suzuki', 'caufield', 'slafkovsky', 'dach', 'hutson', 'guhle',
            'matheson', 'gallagher', 'anderson', 'montembeault', 'primeau'
        }
        
        # NHL opponents for filtering
        self.nhl_teams = {
            'toronto', 'boston', 'buffalo', 'ottawa', 'detroit', 'florida',
            'tampa bay', 'washington', 'carolina', 'columbus', 'pittsburgh',
            'philadelphia', 'new jersey', 'ny rangers', 'ny islanders',
            'colorado', 'vegas', 'minnesota', 'winnipeg', 'calgary',
            'edmonton', 'vancouver', 'seattle', 'anaheim', 'los angeles',
            'san jose', 'arizona', 'utah', 'st louis', 'chicago',
            'dallas', 'nashville'
        }
        
        logger.info("ClipRetrieverNode initialized with query and cutter tools")
    
    async def process(self, state: AgentState) -> AgentState:
        """Process video clip retrieval queries"""
        
        state = update_state_step(state, "clip_retrieval")
        start_time = datetime.now()
        
        try:
            # Extract analysis parameters
            query = state["original_query"]
            user_context = state["user_context"]
            intent_analysis = state["intent_analysis"]
            required_tools = state["required_tools"]
            
            logger.info(f"Processing clip retrieval for query: {query[:100]}...")
            logger.info(f"User context: {user_context.name} ({user_context.role.value})")
            
            # Parse clip query parameters
            search_params = self._parse_clip_query(query, user_context, intent_analysis)
            logger.info(f"Search params: players={search_params.get('player_ids', [])}, events={search_params.get('event_types', [])}")
            
            # Execute clip search and cutting
            clip_results = await self._execute_clip_search_and_cut(
                search_params=search_params,
                user_context=user_context
            )
            
            logger.info(f"Clip search and cut returned {len(clip_results)} results")
            
            # Calculate execution time
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Create tool result
            tool_result = ToolResult(
                tool_type=ToolType.CLIP_RETRIEVAL,
                success=len(clip_results) > 0,
                data={
                    "clips": [self._clip_result_to_dict(clip) for clip in clip_results],
                    "search_params": self._search_params_to_dict(search_params),
                    "total_found": len(clip_results)
                },
                execution_time_ms=execution_time,
                citations=self._generate_citations(clip_results)
            )
            
            # Update state (ensure analytics_data is properly initialized)
            if "analytics_data" not in state:
                state["analytics_data"] = {}
            state["analytics_data"]["clips"] = clip_results
            state = add_tool_result(state, tool_result)
            
            logger.info(f"Clip retrieval completed in {execution_time}ms - found {len(clip_results)} clips")
            
        except Exception as e:
            logger.error(f"Error in clip retrieval: {str(e)}")
            state = add_error(state, f"Clip retrieval failed: {str(e)}")
            
            # Add failed tool result
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            tool_result = ToolResult(
                tool_type=ToolType.CLIP_RETRIEVAL,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
            state = add_tool_result(state, tool_result)
        
        return state
    
    def _parse_clip_query(
        self, 
        query: str, 
        user_context, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse natural language query into clip search parameters"""
        
        query_lower = query.lower()
        
        # Extract player names and map to IDs
        player_names = self._extract_player_names(query_lower, user_context)
        player_ids = self._map_player_names_to_ids(player_names)
        
        # Extract event types (will be mapped by taxonomy in query_tool)
        event_types = self._extract_event_types(query_lower)
        
        # Extract opponents
        opponents = self._extract_opponents(query_lower)
        
        # Extract time filter and map to game_ids
        time_filter = self._extract_time_filter(query_lower)
        game_ids = self._resolve_game_ids(time_filter, user_context)
        
        # Extract limit
        limit = self._extract_limit(query_lower)
        
        return {
            'player_names': player_names,
            'player_ids': player_ids,
            'event_types': event_types,
            'opponents': opponents,
            'time_filter': time_filter,
            'game_ids': game_ids,
            'limit': limit
        }
    
    def _map_player_names_to_ids(self, player_names: List[str]) -> List[str]:
        """Map player names to IDs (placeholder - should use roster data)"""
        # For now, return empty - will be handled by user_context in actual use
        # In production, query player IDs from roster or database
        return []
    
    def _resolve_game_ids(self, time_filter: str, user_context) -> List[str]:
        """Resolve time filter to actual game IDs"""
        # For now, return sample game ID for testing
        # TODO: Query schedule/games from database based on time_filter
        if time_filter in ['last_game', 'recent']:
            return ['20038']  # WSH vs NYR - clean test video
        return ['20038']  # Default for testing
    
    def _extract_player_names(self, query: str, user_context) -> List[str]:
        """Extract player names from query"""
        
        found_players = []
        
        # Check for "my" or "me" indicating user's own clips
        if any(word in query for word in ['my', 'me', 'i ']):
            user_name = getattr(user_context, 'name', '').lower()
            if user_name:
                # Convert user name to match clip naming convention
                formatted_name = user_name.replace(' ', '_').lower()
                if formatted_name in [p.replace(' ', '_') for p in self.mtl_players]:
                    found_players.append(user_name.title())
        
        # Check for explicit player names
        for player in self.mtl_players:
            if player in query:
                found_players.append(player.title())
        
        return list(set(found_players))  # Remove duplicates
    
    def _extract_event_types(self, query: str) -> List[str]:
        """Extract event types from query with enhanced hockey terminology"""
        
        # Map user terms to our internal taxonomy keys
        # These will be expanded by the query_tool's event_taxonomy
        event_mapping = {
            # Zone play (most common requests)
            'zone_exit': ['d-zone exit', 'dzone exit', 'zone exit', 'exit', 'exits', 'breakout', 'clear', 'clearing'],
            'zone_entry': ['o-zone entry', 'ozone entry', 'zone entry', 'entry', 'entries', 'carry in', 'controlled entry'],
            'ozone': ['ozone', 'o-zone', 'offensive zone', 'oz'],
            'dzone_exit': ['d-zone', 'dzone', 'defensive zone', 'dz exit'],
            
            # Scoring
            'goal': ['goal', 'goals', 'scoring', 'scored', 'tally', 'tallies'],
            'shot': ['shot', 'shots', 'shooting', 'wrist shot', 'slap shot'],
            
            # Passes and playmaking
            'pass': ['pass', 'passes', 'passing', 'dish', 'feed'],
            
            # Defensive
            'block': ['block', 'blocks', 'blocked shot', 'shot block'],
            'stick_check': ['stick check', 'poke check', 'check'],
            'pressure': ['pressure', 'forecheack', 'backcheck'],
            
            # Recoveries
            'lpr': ['loose puck', 'recovery', 'recoveries', 'puck battle'],
            
            # Special situations
            'faceoff': ['faceoff', 'faceoffs', 'draw', 'draws', 'face-off'],
            
            # Generic (mode=shift)
            'shifts': ['shift', 'shifts', 'ice time']
        }
        
        found_events = []
        query_lower = query.lower()
        
        for event_type, keywords in event_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                if event_type == 'shifts':
                    # Handle shifts separately with mode parameter
                    continue
                found_events.append(event_type)
        
        return found_events if found_events else ['zone_exit']  # Default to zone exits for testing
    
    def _extract_opponents(self, query: str) -> List[str]:
        """Extract opponent team names from query"""
        
        found_opponents = []
        
        for team in self.nhl_teams:
            if team in query:
                found_opponents.append(team.title())
        
        # Check for "vs" or "against" patterns
        vs_patterns = [r'vs\s+(\w+)', r'against\s+(\w+)', r'versus\s+(\w+)']
        
        for pattern in vs_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if match.lower() in self.nhl_teams:
                    found_opponents.append(match.title())
        
        return list(set(found_opponents))  # Remove duplicates
    
    def _extract_time_filter(self, query: str) -> str:
        """Extract time-based filters from query with enhanced hockey terminology"""
        
        time_patterns = {
            # Basic time patterns
            'last_game': r'last\s+game|previous\s+game|most\s+recent\s+game|tonight\'?s\s+game|yesterday\'?s\s+game',
            'last_2_games': r'last\s+2\s+games|past\s+2\s+games|last\s+couple\s+games',
            'last_3_games': r'last\s+3\s+games|past\s+3\s+games',
            'last_5_games': r'last\s+5\s+games|past\s+5\s+games',
            'last_10_games': r'last\s+10\s+games|past\s+10\s+games',
            
            # Hockey-specific time periods
            'this_season': r'this\s+season|current\s+season|2024-25\s+season|2024-2025\s+season',
            'last_season': r'last\s+season|previous\s+season|2023-24\s+season|2023-2024\s+season',
            'this_month': r'this\s+month|current\s+month|past\s+month',
            'this_week': r'this\s+week|past\s+week|recent\s+games',
            'recent': r'recent|lately|recently',
            
            # Game situation contexts
            'playoffs': r'playoff|playoffs|postseason|post\s+season',
            'regular_season': r'regular\s+season|season\s+games',
            'home_games': r'home\s+games?|at\s+home|bell\s+centre',
            'away_games': r'away\s+games?|on\s+the\s+road|road\s+games?',
            
            # Period-specific
            'overtime': r'overtime|OT|extra\s+time',
            'shootout': r'shootout|SO|penalty\s+shots?'
        }
        
        for time_filter, pattern in time_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                return time_filter
        
        return ""
    
    def _extract_limit(self, query: str) -> int:
        """Extract result limit from query"""
        
        # Look for patterns like "show me 5 clips" or "first 10"
        limit_patterns = [
            r'show\s+me\s+(\d+)',
            r'first\s+(\d+)',
            r'top\s+(\d+)',
            r'(\d+)\s+clips?'
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return min(int(match.group(1)), 20)  # Cap at 20
        
        return 10  # Default limit
    
    async def _execute_clip_search_and_cut(
        self, 
        search_params: Dict[str, Any],
        user_context
    ) -> List[Dict[str, Any]]:
        """Execute clip search and cut using our tools"""
        
        # Build QuerySearchParams for clip_query tool
        query_params = QuerySearchParams(
            players=search_params.get('player_ids', []) or ['8478463', '8476880'],  # WSH players with exits
            event_types=search_params.get('event_types', ['zone_exit']),
            timeframe=search_params.get('time_filter', 'last_game'),
            game_ids=search_params.get('game_ids', ['20038']),
            limit=search_params.get('limit', 10)
        )
        
        # Query event segments
        logger.info(f"Querying events: {query_params.event_types} for players {query_params.players}")
        segments = self.query_tool.query_events(query_params)
        
        if not segments:
            logger.warning("No event segments found")
            return []
        
        logger.info(f"Found {len(segments)} event segments, cutting clips...")
        
        # Build cut requests
        cut_requests = []
        for seg in segments[:query_params.limit]:
            if not seg.period_video_path:
                logger.warning(f"No video path for segment {seg.clip_id}, skipping")
                continue
            
            output_dir = self.cutter.output_base_dir / seg.game_date / seg.game_id / f"p{seg.period}"
            output_path = output_dir / f"{seg.clip_id}.mp4"
            
            request = ClipCutRequest(
                source_video=Path(seg.period_video_path),
                start_seconds=seg.start_timecode_s,
                end_seconds=seg.end_timecode_s,
                output_path=output_path,
                clip_id=seg.clip_id,
                metadata={
                    'player_id': seg.player_id,
                    'player_name': seg.player_name,
                    'event_type': seg.event_type,
                    'game_id': seg.game_id,
                    'game_date': seg.game_date,
                    'season': '2025-2026',  # Extract from game_id or config
                    'period': seg.period,
                    'team_code': seg.team_code,
                    'opponent_code': seg.opponent,
                    'outcome': seg.outcome,
                    'zone': seg.zone
                }
            )
            cut_requests.append((seg, request))
        
        # Cut clips in parallel
        clip_results = []
        if cut_requests:
            cut_results = self.cutter.cut_clips_parallel([req for _, req in cut_requests])
            
            # Combine segment metadata with cut results
            for (segment, _), cut_result in zip(cut_requests, cut_results):
                if cut_result.success:
                    clip_results.append({
                        'clip_id': cut_result.clip_id,
                        'title': segment.title,
                        'description': segment.description,
                        'player_id': segment.player_id,
                        'player_name': segment.player_name or segment.player_id,
                        'event_type': segment.event_type,
                        'outcome': segment.outcome,
                        'game_id': segment.game_id,
                        'game_date': segment.game_date,
                        'period': segment.period,
                        'period_time': segment.period_time,
                        'team': segment.team,
                        'opponent': segment.opponent,
                        'duration': cut_result.duration_s,
                        'file_path': str(cut_result.output_path),
                        'file_url': f"/api/v1/clips/{cut_result.clip_id}/video",
                        'thumbnail_path': str(cut_result.thumbnail_path),
                        'thumbnail_url': f"/api/v1/clips/{cut_result.clip_id}/thumbnail",
                        'file_size_bytes': cut_result.file_size_bytes,
                        'processing_time_s': cut_result.processing_time_s,
                        'relevance_score': 1.0  # Placeholder
                    })
                else:
                    logger.warning(f"Failed to cut clip {cut_result.clip_id}: {cut_result.error_message}")
        
        return clip_results
    
    def _clip_result_to_dict(self, clip_result: Dict[str, Any]) -> Dict[str, Any]:
        """Clip results are already dicts, just return as-is"""
        return clip_result
    
    def _search_params_to_dict(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert search params to dictionary"""
        return {
            "player_names": search_params.get('player_names', []),
            "player_ids": search_params.get('player_ids', []),
            "event_types": search_params.get('event_types', []),
            "opponents": search_params.get('opponents', []),
            "time_filter": search_params.get('time_filter', ''),
            "game_ids": search_params.get('game_ids', []),
            "limit": search_params.get('limit', 10)
        }
    
    def _generate_citations(self, clip_results: List[Dict[str, Any]]) -> List[str]:
        """Generate citations for clip results"""
        citations = []
        
        if clip_results:
            citations.append(f"[clip_database:{len(clip_results)}_clips]")
            
            # Add specific citations for unique sources
            unique_games = set()
            unique_players = set()
            
            for clip in clip_results:
                if clip.get('game_id'):
                    unique_games.add(clip['game_id'])
                if clip.get('player_name'):
                    unique_players.add(clip['player_name'])
            
            if unique_games:
                citations.append(f"[games:{','.join(list(unique_games)[:3])}]")
            
            if unique_players:
                citations.append(f"[players:{','.join(list(unique_players)[:3])}]")
        
        return citations
