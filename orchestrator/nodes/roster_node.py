"""
HeartBeat Engine - Roster Retrieval Node
Montreal Canadiens Advanced Analytics Assistant

Retrieves NHL team roster via NHLRosterClient and stores in state.
"""

from typing import Dict, Any
import logging

from orchestrator.utils.state import (
    AgentState,
    ToolResult,
    ToolType,
    update_state_step,
    add_tool_result,
    add_error
)
from orchestrator.tools.nhl_roster_client import NHLRosterClient

logger = logging.getLogger(__name__)


class RosterNode:
    """Node to fetch team roster information."""

    def __init__(self):
        self.client = NHLRosterClient()

    async def process(self, state: AgentState) -> AgentState:
        state = update_state_step(state, "roster_retrieval")

        try:
            query = state["original_query"]
            intent = state.get("intent_analysis", {})
            args: Dict[str, Any] = state.get("tool_arguments", {})

            team = args.get("team") or self._infer_team_from_intent(intent, query) or "MTL"
            season = args.get("season") or state.get("current_season")
            scope = args.get("scope") or "active"

            logger.info(f"Fetching roster: team={team}, season={season}, scope={scope}")

            result_data = await self.client.get_team_roster(team=team, season=season, scope=scope)

            tool_result = ToolResult(
                tool_type=ToolType.TEAM_ROSTER,
                success=True if result_data and result_data.get("players") is not None else False,
                data=result_data,
                execution_time_ms=0,
                citations=[f"[nhl_api:roster:{team}]"]
            )

            if "analytics_data" not in state:
                state["analytics_data"] = {}
            state["analytics_data"]["roster"] = result_data

            state = add_tool_result(state, tool_result)
            return state

        except Exception as e:
            logger.error(f"Roster retrieval failed: {e}")
            state = add_error(state, f"Roster retrieval failed: {str(e)}")
            tool_result = ToolResult(
                tool_type=ToolType.TEAM_ROSTER,
                success=False,
                error=str(e),
                execution_time_ms=0
            )
            state = add_tool_result(state, tool_result)
            return state

    def _infer_team_from_intent(self, intent: Dict[str, Any], query: str) -> str:
        # Simple extraction of team abbreviations (extend as needed)
        known = [
            "MTL","TOR","BOS","OTT","DET","TBL","FLA","BUF","NYR","NYI","NJD","PHI","PIT",
            "WSH","CAR","CBJ","VGK","SEA","VAN","EDM","CGY","WPG","MIN","COL","DAL","STL",
            "CHI","NSH","LAK","ANA","SJS","ARI","UTA"
        ]
        q = query.upper()
        for abbr in known:
            if abbr in q:
                return abbr
        # Try from intent if present
        team_from_intent = intent.get("team") or intent.get("opponent")
        if isinstance(team_from_intent, str) and len(team_from_intent) in (2,3):
            return team_from_intent.upper()
        return ""


