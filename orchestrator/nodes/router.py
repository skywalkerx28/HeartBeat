"""
HeartBeat Engine - Router Node
Montreal Canadiens Advanced Analytics Assistant

Routes queries to appropriate tools and determines execution sequence.
"""

from typing import List, Dict, Any
import logging

from orchestrator.utils.state import AgentState, ToolType, update_state_step
from orchestrator.config.settings import settings

logger = logging.getLogger(__name__)

class RouterNode:
    """
    Routes queries to appropriate tools based on intent analysis.
    Determines optimal execution sequence and validates user permissions.
    """
    
    def __init__(self):
        # Tool execution priorities (lower = higher priority)
        self.tool_priorities = {
            ToolType.CLIP_RETRIEVAL: 1,     # Clips first (user-requested content)
            ToolType.VECTOR_SEARCH: 2,      # Context second
            ToolType.PARQUET_QUERY: 3,      # Then data
            ToolType.CALCULATE_METRICS: 4,  # Then calculations
            ToolType.MATCHUP_ANALYSIS: 5,   # Then comparisons
            ToolType.TEAM_ROSTER: 6,        # Roster before visualization
            ToolType.VISUALIZATION: 7       # Finally visualizations
        }
    
    def process(self, state: AgentState) -> AgentState:
        """Process routing decisions for the query"""
        
        state = update_state_step(state, "routing")
        
        user_context = state["user_context"]
        required_tools = state["required_tools"]
        intent_analysis = state["intent_analysis"]
        
        logger.info(f"Routing query with {len(required_tools)} required tools")
        
        # Validate user permissions for requested tools
        validated_tools = self._validate_tool_permissions(
            required_tools, user_context.role
        )
        
        # Create execution sequence
        tool_sequence = self._create_execution_sequence(
            validated_tools, intent_analysis
        )
        
        # Update state with routing decisions
        state["required_tools"] = validated_tools
        state["tool_sequence"] = tool_sequence
        
        # Add routing metadata to debug info
        state["debug_info"]["routing"] = {
            "original_tools": [t.value for t in required_tools],
            "validated_tools": [t.value for t in validated_tools],
            "execution_sequence": tool_sequence,
            "user_role": user_context.role.value,
            "processing_approach": intent_analysis.get("processing_approach", "standard")
        }
        
        logger.info(f"Routing complete: {len(validated_tools)} tools, sequence: {tool_sequence}")
        
        return state
    
    def _validate_tool_permissions(
        self, 
        requested_tools: List[ToolType], 
        user_role
    ) -> List[ToolType]:
        """Validate that user has permissions for requested tools"""
        
        user_permissions = settings.get_user_permissions(user_role)
        validated_tools = []
        
        for tool in requested_tools:
            if self._can_use_tool(tool, user_permissions):
                validated_tools.append(tool)
            else:
                logger.warning(f"Tool {tool.value} denied for role {user_role.value}")
        
        # Ensure we have at least vector search for basic functionality
        if not validated_tools and ToolType.VECTOR_SEARCH not in validated_tools:
            validated_tools.append(ToolType.VECTOR_SEARCH)
        
        return validated_tools
    
    def _can_use_tool(self, tool: ToolType, permissions: Dict[str, Any]) -> bool:
        """Check if user has permission to use a specific tool"""
        
        # Vector search is available to all users
        if tool == ToolType.VECTOR_SEARCH:
            return True
        
        # Basic parquet queries available to all
        if tool == ToolType.PARQUET_QUERY:
            return True
        
        # Advanced metrics require permission
        if tool == ToolType.CALCULATE_METRICS:
            return permissions.get("advanced_metrics", False)
        
        # Matchup analysis requires opponent data access
        if tool == ToolType.MATCHUP_ANALYSIS:
            return permissions.get("opponent_data", False)
        
        # Visualization available to all
        if tool == ToolType.VISUALIZATION:
            return True
        
        # Team roster available to all
        if tool == ToolType.TEAM_ROSTER:
            return True

        # Clip retrieval based on user permissions
        if tool == ToolType.CLIP_RETRIEVAL:
            return permissions.get("clips_access", True)  # Default to allowing clips
        
        # Default to allowing
        return True
    
    def _create_execution_sequence(
        self, 
        validated_tools: List[ToolType], 
        intent_analysis: Dict[str, Any]
    ) -> List[str]:
        """Create optimal execution sequence for tools"""
        
        if not validated_tools:
            return ["response_synthesis"]
        
        approach = intent_analysis.get("processing_approach", "standard")
        
        if approach == "single_tool":
            return self._single_tool_sequence(validated_tools)
        elif approach == "context_then_analysis":
            return self._context_first_sequence(validated_tools)
        elif approach == "multi_step_analysis":
            return self._multi_step_sequence(validated_tools)
        else:
            return self._parallel_sequence(validated_tools)
    
    def _single_tool_sequence(self, tools: List[ToolType]) -> List[str]:
        """Create sequence for single tool execution"""
        
        tool = tools[0]
        
        if tool == ToolType.CLIP_RETRIEVAL:
            return ["clip_retrieval", "response_synthesis"]
        elif tool == ToolType.VECTOR_SEARCH:
            return ["vector_retrieval", "response_synthesis"]
        elif tool in [ToolType.PARQUET_QUERY, ToolType.CALCULATE_METRICS]:
            return ["parquet_analysis", "response_synthesis"]
        elif tool == ToolType.TEAM_ROSTER:
            return ["roster_retrieval", "response_synthesis"]
        else:
            return ["parquet_analysis", "response_synthesis"]
    
    def _context_first_sequence(self, tools: List[ToolType]) -> List[str]:
        """Create sequence that prioritizes context retrieval first"""
        
        sequence = []
        
        # Start with clips if requested (high priority user content)
        if ToolType.CLIP_RETRIEVAL in tools:
            sequence.append("clip_retrieval")
        
        # Then context if available
        if ToolType.VECTOR_SEARCH in tools:
            sequence.append("vector_retrieval")
        
        # Then analytical tools
        if any(t in tools for t in [
            ToolType.PARQUET_QUERY, 
            ToolType.CALCULATE_METRICS, 
            ToolType.MATCHUP_ANALYSIS
        ]):
            sequence.append("parquet_analysis")

        # Team roster if needed
        if ToolType.TEAM_ROSTER in tools:
            sequence.insert(0, "roster_retrieval")
        
        # Finally synthesis
        sequence.append("response_synthesis")
        
        return sequence
    
    def _multi_step_sequence(self, tools: List[ToolType]) -> List[str]:
        """Create sequence for complex multi-step analysis"""
        
        sequence = []
        
        # Step 1: Get context
        if ToolType.VECTOR_SEARCH in tools:
            sequence.append("vector_retrieval")
        
        # Step 2: Get base data
        if ToolType.PARQUET_QUERY in tools:
            sequence.append("parquet_analysis")
        
        # Step 3: Advanced calculations (if needed)
        if ToolType.CALCULATE_METRICS in tools:
            # This would be handled within parquet_analysis
            pass
        
        # Step 4: Matchup analysis (if needed)
        if ToolType.MATCHUP_ANALYSIS in tools:
            # This would also be handled within parquet_analysis
            pass
        
        # Step 5: Synthesis
        sequence.append("response_synthesis")
        
        return sequence
    
    def _parallel_sequence(self, tools: List[ToolType]) -> List[str]:
        """Create sequence for parallel tool execution"""
        
        # For now, we'll use sequential execution
        # Future enhancement: implement true parallel execution
        
        sequence = []
        
        # Sort tools by priority
        sorted_tools = sorted(tools, key=lambda t: self.tool_priorities.get(t, 10))
        
        # Map tools to nodes
        for tool in sorted_tools:
            if tool == ToolType.CLIP_RETRIEVAL and "clip_retrieval" not in sequence:
                sequence.append("clip_retrieval")
            elif tool == ToolType.VECTOR_SEARCH and "vector_retrieval" not in sequence:
                sequence.append("vector_retrieval")
            elif tool in [
                ToolType.PARQUET_QUERY, 
                ToolType.CALCULATE_METRICS, 
                ToolType.MATCHUP_ANALYSIS
            ] and "parquet_analysis" not in sequence:
                sequence.append("parquet_analysis")
            elif tool == ToolType.TEAM_ROSTER and "roster_retrieval" not in sequence:
                sequence.append("roster_retrieval")
        
        # Always end with synthesis
        if "response_synthesis" not in sequence:
            sequence.append("response_synthesis")
        
        return sequence
