"""
Qwen3 Orchestrator Service for HeartBeat Engine

Wraps the Qwen3-Next-80B Thinking orchestrator for use in the FastAPI backend.
Provides a clean interface between the HTTP API and the Vertex AI-powered orchestrator.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from orchestrator.agents.qwen3_autonomous_orchestrator import qwen3_autonomous_orchestrator
from orchestrator.utils.state import AgentState, create_initial_state, UserContext, ToolType
from orchestrator.config.settings import UserRole

logger = logging.getLogger(__name__)


class Qwen3OrchestratorService:
    """
    Service wrapper for Qwen3 orchestrator integration.
    
    Handles:
    - State management
    - User context mapping
    - Result transformation for API responses
    - Error handling and logging
    """
    
    def __init__(self):
        """Initialize Qwen3 service with autonomous orchestrator."""
        self.orchestrator = qwen3_autonomous_orchestrator
        logger.info("Qwen3 Autonomous Orchestrator Service initialized")
    
    async def process_query(
        self,
        query: str,
        user_context: UserContext
    ) -> Dict[str, Any]:
        """
        Process a hockey analytics query through Qwen3 orchestrator.
        
        Args:
            query: User's natural language query
            user_context: User role and context information
            
        Returns:
            Dict with structured response data for API
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing query via Qwen3: {query[:100]}...")
            
            # Create initial state
            state = create_initial_state(
                query=query,
                user_context=user_context
            )
            
            # Process through Qwen3 autonomous orchestrator
            # Model decides everything: what tools, when, how many
            result_state = await self.orchestrator.process_query(state)
            
            # Calculate processing time
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Transform to API response format
            api_response = self._transform_to_api_format(
                result_state,
                processing_time_ms
            )
            
            logger.info(f"Query processed successfully in {processing_time_ms}ms")
            return api_response
            
        except Exception as e:
            logger.error(f"Error processing query via Qwen3: {str(e)}", exc_info=True)
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return {
                "success": False,
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "query_type": "unknown",
                "tool_results": [],
                "processing_time_ms": processing_time_ms,
                "evidence_chain": [],
                "analytics": [],
                "errors": [str(e)],
                "warnings": []
            }
    
    def _transform_to_api_format(
        self,
        state: AgentState,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Transform orchestrator state to API response format.
        
        Args:
            state: Final AgentState from orchestrator
            processing_time_ms: Total processing time
            
        Returns:
            Dict formatted for API response
        """
        # Extract tool results
        tool_results = []
        for tool_result in state.get("tool_results", []):
            tool_results.append({
                "tool": tool_result.tool_type.value if hasattr(tool_result.tool_type, 'value') else str(tool_result.tool_type),
                "success": tool_result.success,
                "data": tool_result.data,
                "processing_time_ms": tool_result.execution_time_ms if hasattr(tool_result, 'execution_time_ms') else 0,
                "citations": tool_result.citations if hasattr(tool_result, 'citations') else [],
                "error": tool_result.error
            })
        
        # Build analytics data for frontend visualization
        analytics = self._build_analytics_from_results(state)
        
        # Build evidence chain
        evidence_chain = self._build_evidence_chain(state)
        
        return {
            "success": True,
            "response": state.get("final_response", "Analysis complete."),
            "query_type": state.get("query_type", {}).get("primary") if isinstance(state.get("query_type"), dict) else state.get("query_type"),
            "tool_results": tool_results,
            "processing_time_ms": processing_time_ms,
            "evidence_chain": evidence_chain,
            "analytics": analytics,
            "errors": state.get("errors", []),
            "warnings": state.get("warnings", [])
        }
    
    def _build_analytics_from_results(self, state: AgentState) -> List[Dict[str, Any]]:
        """
        Build analytics data from tool results for frontend visualization.
        
        Args:
            state: AgentState with tool results
            
        Returns:
            List of analytics data objects
        """
        analytics = []
        
        for tool_result in state.get("tool_results", []):
            if not tool_result.success or not tool_result.data:
                continue
            
            data = tool_result.data
            
            # Ensure data is a dict before calling .get()
            if not isinstance(data, dict):
                continue
            
            # Power play analytics
            if "power_play" in str(tool_result.tool_type).lower() or data.get("analysis_type") == "power_play":
                analytics.append({
                    "type": "stat",
                    "title": "Power Play Analysis",
                    "data": {
                        "pp_units": data.get("total_pp_units", 0),
                        "opponent": data.get("opponent", "All"),
                        "metrics": data.get("pp_units", [])[:5]  # Top 5 units
                    },
                    "metadata": {
                        "source": data.get("data_source", "parquet"),
                        "columns": data.get("columns_available", [])
                    }
                })
            
            # Matchup analytics
            elif "matchup" in str(tool_result.tool_type).lower() or data.get("analysis_type") == "matchup":
                analytics.append({
                    "type": "stat",
                    "title": f"Matchup Analysis - {data.get('opponent', 'Opponent')}",
                    "data": {
                        "total_matchups": data.get("total_matchups", 0),
                        "xgf": data.get("xgf", 0),
                        "metrics": data.get("summary_stats", {})
                    },
                    "metadata": {
                        "source": data.get("data_source", "parquet")
                    }
                })
            
            # Game data analytics
            elif "game" in str(tool_result.tool_type).lower() or data.get("analysis_type") == "season_results":
                analytics.append({
                    "type": "table",
                    "title": "Season Results",
                    "data": {
                        "total_games": data.get("total_games", 0),
                        "games": data.get("games", [])[:10]  # Recent 10 games
                    },
                    "metadata": {
                        "source": data.get("data_source", "parquet")
                    }
                })
        
        return analytics
    
    def _build_evidence_chain(self, state: AgentState) -> List[str]:
        """
        Build evidence chain showing reasoning steps.
        
        Args:
            state: AgentState with processing history
            
        Returns:
            List of evidence strings
        """
        evidence = []
        
        # Add query type detection
        if state.get("query_type"):
            qt = state.get("query_type")
            if isinstance(qt, dict):
                evidence.append(f"Identified query type: {qt.get('primary', 'unknown')}")
            else:
                evidence.append(f"Identified query type: {qt}")
        
        # Add tools used
        tools_used = [tr.tool_type for tr in state.get("tool_results", []) if tr.success]
        if tools_used:
            tool_names = [t.value if hasattr(t, 'value') else str(t) for t in tools_used]
            evidence.append(f"Executed {len(tools_used)} analysis tools: {', '.join(tool_names)}")
        
        # Add data sources
        data_sources = set()
        for tr in state.get("tool_results", []):
            if tr.success and tr.data and isinstance(tr.data, dict):
                source = tr.data.get("data_source")
                if source:
                    data_sources.add(source)
        
        if data_sources:
            evidence.append(f"Queried data sources: {', '.join(data_sources)}")
        
        return evidence
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of Qwen3 orchestrator.
        
        Returns:
            Health status dict
        """
        try:
            # Test that coordinator is initialized
            status = {
                "coordinator_initialized": self.orchestrator is not None,
                "vertex_ai_configured": True,  # Already validated at startup
                "status": "healthy"
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "coordinator_initialized": False,
                "vertex_ai_configured": False,
                "status": "unhealthy",
                "error": str(e)
            }


# Global service instance
_qwen3_service: Optional[Qwen3OrchestratorService] = None


def get_qwen3_service() -> Qwen3OrchestratorService:
    """
    Get or create the global Qwen3 service instance.
    
    Returns:
        Qwen3OrchestratorService instance
    """
    global _qwen3_service
    
    if _qwen3_service is None:
        _qwen3_service = Qwen3OrchestratorService()
    
    return _qwen3_service

