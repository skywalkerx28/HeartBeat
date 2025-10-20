"""
Enhanced Clip Retriever Node for HeartBeat Orchestrator
Integrates shift mode and advanced filtering with frontend
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from orchestrator.utils.state import (
    AgentState,
    ToolResult,
    ToolType,
    update_state_step,
    add_tool_result,
    add_error
)
from orchestrator.tools.clip_query_enhanced import EnhancedClipQueryTool, ClipSearchParams
from orchestrator.tools.clip_cutter import FFmpegClipCutter, ClipCutRequest
from orchestrator.tools.roster_service import get_roster_service
from orchestrator.tools.schedule_service import get_schedule_service

logger = logging.getLogger(__name__)


class EnhancedClipRetrieverNode:
    """
    Enhanced clip retriever with shift mode and NL parsing
    
    Handles queries like:
    - "Show me all my shifts in period 2 from last game"
    - "Show me my zone exits when Ovechkin was on ice"
    - "Show me all my shifts with Suzuki and Caufield"
    """
    
    def __init__(self):
        workspace_root = Path(__file__).parent.parent.parent
        
        self.query_tool = EnhancedClipQueryTool(
            extracted_metrics_dir=str(workspace_root / "data/processed/extracted_metrics"),
            clips_dir=str(workspace_root / "data/clips")
        )
        
        self.cutter = FFmpegClipCutter(
            output_base_dir=str(workspace_root / "data/clips/generated"),
            max_workers=3,
            use_duckdb=True
        )
        
        self.roster_service = get_roster_service()
        self.schedule_service = get_schedule_service()
        
        logger.info("EnhancedClipRetrieverNode initialized")
    
    async def __call__(self, state: AgentState) -> AgentState:
        """Process clip retrieval request"""
        try:
            query = state.get("original_query", "")
            user_context = state.get("user_context")
            
            logger.info(f"Processing clip query: {query}")
            
            # Parse query to params
            params = self._parse_nl_query(query, user_context)
            
            if not params:
                return add_error(state, "Could not parse clip query")
            
            # Execute search
            segments = self.query_tool.query(params)
            
            if not segments:
                return self._add_no_clips_response(state, query)
            
            logger.info(f"Found {len(segments)} clip segments")
            
            # Cut clips
            clip_results = await self._cut_clips(segments, params)
            
            # Format for frontend
            clips_data = self._format_clips_for_frontend(clip_results, segments, params)
            
            # Add to state
            state = update_state_step(state, "clip_retrieval", {
                "found_clips": len(clip_results),
                "mode": params.mode,
                "query": query
            })
            
            # Add visual results
            if "visual" not in state:
                state["visual"] = {}
            
            state["visual"]["clips"] = clips_data
            
            # Add to analytics for chat response
            if "analytics" not in state:
                state["analytics"] = []
            
            state["analytics"].append({
                "type": "clips",
                "title": self._generate_title(params, len(clip_results)),
                "clips": clips_data
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Clip retrieval error: {e}", exc_info=True)
            return add_error(state, f"Clip retrieval failed: {str(e)}")
    
    def _parse_nl_query(self, query: str, user_context) -> Optional[ClipSearchParams]:
        """Parse natural language query to ClipSearchParams"""
        query_lower = query.lower()
        
        # Detect mode
        mode = "shift" if any(word in query_lower for word in ["shift", "shifts", "ice time"]) else "event"
        
        # Extract periods
        periods = []
        if "period 1" in query_lower or "first period" in query_lower:
            periods.append(1)
        if "period 2" in query_lower or "second period" in query_lower:
            periods.append(2)
        if "period 3" in query_lower or "third period" in query_lower:
            periods.append(3)
        if "all periods" in query_lower:
            periods = [1, 2, 3]
        
        # Extract event types
        event_types = []
        event_keywords = {
            "zone exit": "zone_exit",
            "zone entry": "zone_entry",
            "breakout": "breakout",
            "shot": "shot",
            "goal": "goal",
            "pass": "pass",
            "hit": "hit"
        }
        
        for keyword, event_type in event_keywords.items():
            if keyword in query_lower:
                event_types.append(event_type)
        
        # Extract player references
        players = []
        team_code = None
        
        # Check for "my" or "me" -> use user's player ID
        if "my" in query_lower or "me" in query_lower or "i " in query_lower:
            if hasattr(user_context, 'preferences') and 'player_id' in user_context.preferences:
                players.append(user_context.preferences['player_id'])
                if hasattr(user_context, 'team_access') and user_context.team_access:
                    team_code = user_context.team_access[0]
        
        # Extract timeframe
        timeframe = "last_game"
        if "last game" in query_lower:
            timeframe = "last_game"
        elif "last 3 games" in query_lower:
            timeframe = "last_3_games"
        elif "last 5 games" in query_lower:
            timeframe = "last_5_games"
        elif "this season" in query_lower:
            timeframe = "this_season"
        
        # Extract opponent filters (e.g., "when Ovechkin was on ice")
        opponents_on_ice = []
        if "when" in query_lower and "on ice" in query_lower:
            # Look for player names after "when"
            when_part = query_lower.split("when")[1].split("on ice")[0]
            # Try to find player by name
            potential_names = [n.strip() for n in when_part.split("or") if n.strip()]
            for name in potential_names:
                matches = self.roster_service.search_by_name(name)
                if matches:
                    opponents_on_ice.append(matches[0].id)
        
        return ClipSearchParams(
            players=players,
            event_types=event_types,
            mode=mode,
            periods=periods if periods else None,
            timeframe=timeframe,
            team=team_code,
            opponents_on_ice=opponents_on_ice,
            limit=10,
            season="20252026"
        )
    
    async def _cut_clips(self, segments, params: ClipSearchParams) -> List[Dict]:
        """Cut video clips from segments"""
        requests = []
        
        for seg in segments:
            if not seg.period_video_path:
                continue
            
            output_dir = Path(self.cutter.output_base_dir) / seg.game_id / f"p{seg.period}"
            output_dir.mkdir(parents=True, exist_ok=True)
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
                    'mode': seg.mode,
                    'period': seg.period,
                    'game_id': seg.game_id,
                    'season': seg.season,
                    'team_code': seg.team_code,
                    'opponent': seg.opponent,
                    'event_type': seg.event_type,
                    'strength': seg.strength,
                    'duration_s': seg.duration_s
                }
            )
            requests.append((request, seg))
        
        if not requests:
            return []
        
        # Cut clips
        results = self.cutter.cut_clips_parallel([r[0] for r in requests])
        
        # Combine with segments
        clip_data = []
        for result, (req, seg) in zip(results, requests):
            if result.success:
                clip_data.append({
                    'result': result,
                    'segment': seg,
                    'request': req
                })
        
        return clip_data
    
    def _format_clips_for_frontend(
        self,
        clip_results: List[Dict],
        segments,
        params: ClipSearchParams
    ) -> List[Dict]:
        """Format clips for frontend VideoClipCard component"""
        formatted = []
        
        for item in clip_results:
            result = item['result']
            seg = item['segment']
            
            # Generate title based on mode
            if seg.mode == "shift":
                title = f"{seg.player_name} - {seg.duration_s:.0f}s Shift"
            else:
                title = f"{seg.player_name} - {seg.event_type}"
            
            # Generate description
            if seg.mode == "shift":
                description = f"Period {seg.period} at {seg.period_time}"
                if seg.strength:
                    description += f" • {seg.strength}"
                if seg.opponents_on_ice:
                    description += f" • vs {len(seg.opponents_on_ice)} opponents"
            else:
                description = f"Period {seg.period} at {seg.period_time}"
                if seg.outcome:
                    description += f" • {seg.outcome}"
            
            formatted.append({
                'clip_id': seg.clip_id,
                'title': title,
                'player_name': seg.player_name or str(seg.player_id),
                'game_info': f"{seg.team_code} vs {seg.opponent} • {seg.game_date}",
                'event_type': seg.mode.upper() if seg.mode == "shift" else seg.event_type,
                'description': description,
                'file_url': f"/api/v1/clips/{seg.clip_id}/video",
                'thumbnail_url': f"/api/v1/clips/{seg.clip_id}/thumbnail",
                'duration': seg.duration_s,
                'relevance_score': 1.0,
                'metadata': {
                    'mode': seg.mode,
                    'period': seg.period,
                    'strength': seg.strength,
                    'team': seg.team_code,
                    'opponent': seg.opponent,
                    'season': seg.season,
                    'game_id': seg.game_id
                }
            })
        
        return formatted
    
    def _generate_title(self, params: ClipSearchParams, count: int) -> str:
        """Generate analytics panel title"""
        if params.mode == "shift":
            if params.periods:
                period_str = f"Period {params.periods[0]}" if len(params.periods) == 1 else "All Periods"
                return f"Shifts - {period_str} ({count} found)"
            return f"Shifts ({count} found)"
        else:
            event_str = params.event_types[0] if params.event_types else "Events"
            return f"{event_str.title()} Clips ({count} found)"
    
    def _add_no_clips_response(self, state: AgentState, query: str) -> AgentState:
        """Add response when no clips found"""
        if "analytics" not in state:
            state["analytics"] = []
        
        state["analytics"].append({
            "type": "clips",
            "title": "No Clips Found",
            "clips": []
        })
        
        return state

