"""
HeartBeat Engine - Qwen3-Enhanced LangGraph Orchestrator
Montreal Canadiens Advanced Analytics Assistant

Enhanced orchestrator using Qwen3-Next-80B Thinking for reasoning and tool orchestration.
Maintains compatibility with existing node structure while adding Qwen3 capabilities.
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from orchestrator.utils.state import (
    AgentState, 
    create_initial_state, 
    UserContext,
    QueryType,
    ToolType
)
from orchestrator.config.settings import settings
from orchestrator.agents.qwen3_coordinator import qwen3_coordinator
from orchestrator.nodes.pinecone_retriever import PineconeRetrieverNode
from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode
from orchestrator.nodes.clip_retriever import ClipRetrieverNode

logger = logging.getLogger(__name__)


class HeartBeatQwen3Orchestrator:
    """
    Enhanced orchestrator using Qwen3-Next-80B Thinking.
    
    Coordinates between:
    - Qwen3-Next-80B Thinking (reasoning and tool planning)
    - Pinecone vector search (hockey context/rules)
    - Parquet analytics (real-time stats/metrics)
    - Qwen3-VL (vision analysis - future)
    """
    
    def __init__(self):
        self.graph = None
        self.coordinator = qwen3_coordinator
        self._build_workflow()
    
    def _build_workflow(self) -> None:
        """Build the Qwen3-enhanced LangGraph workflow"""
        
        # Initialize workflow
        workflow = StateGraph(AgentState)
        
        # Add nodes with Qwen3 integration
        workflow.add_node("qwen3_intent_analysis", self._qwen3_intent_analysis_node)
        workflow.add_node("qwen3_tool_execution", self._qwen3_tool_execution_node)
        workflow.add_node("qwen3_response_synthesis", self._qwen3_response_synthesis_node)
        
        # Define entry point
        workflow.set_entry_point("qwen3_intent_analysis")
        
        # Linear workflow: Intent → Tools → Synthesis
        # Qwen3 handles all routing internally via sequential tool calls
        workflow.add_edge("qwen3_intent_analysis", "qwen3_tool_execution")
        workflow.add_edge("qwen3_tool_execution", "qwen3_response_synthesis")
        workflow.add_edge("qwen3_response_synthesis", END)
        
        # Compile the graph
        self.graph = workflow.compile()
        
        logger.info("Qwen3-enhanced orchestrator workflow compiled successfully")
    
    async def process_query(
        self, 
        query: str, 
        user_context: UserContext,
        query_type: Optional[QueryType] = None
    ) -> Dict[str, Any]:
        """
        Process a user query using Qwen3 Thinking for orchestration.
        
        Args:
            query: User's hockey analytics query
            user_context: User identity and permissions
            query_type: Optional hint about query type
            
        Returns:
            Complete response with data, citations, and metadata
        """
        
        start_time = datetime.now()
        
        try:
            # Create initial state
            initial_state = create_initial_state(user_context, query, query_type)
            
            logger.info(f"Processing query with Qwen3 for {user_context.role.value}: {query[:100]}...")
            
            # Execute the workflow
            result = await self.graph.ainvoke(initial_state)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result["processing_time_ms"] = int(processing_time)
            
            # Format final response
            response = {
                "response": result["final_response"],
                "query_type": result["query_type"].value,
                "evidence_chain": result["evidence_chain"],
                "tool_results": [
                    {
                        "tool": r.tool_type.value,
                        "success": r.success,
                        "data": r.data,
                        "processing_time_ms": r.execution_time_ms,
                        "citations": r.citations,
                        "error": r.error
                    } for r in result["tool_results"]
                ],
                "processing_time_ms": result["processing_time_ms"],
                "iterations": result["iteration_count"],
                "model": "qwen3-next-80b-thinking",
                "user_role": user_context.role.value,
                "errors": result["error_messages"]
            }
            
            logger.info(f"Query processed successfully with Qwen3 in {processing_time:.0f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query with Qwen3: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again or rephrase your question.",
                "error": str(e),
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                "success": False
            }
    
    async def _qwen3_intent_analysis_node(self, state: AgentState) -> AgentState:
        """
        Analyze user intent using Qwen3 Thinking.
        
        Replaces traditional intent analysis with Qwen3's reasoning capabilities.
        """
        try:
            state = await self.coordinator.analyze_intent(state)
            logger.info(f"Intent analyzed: {state['query_type'].value}")
            return state
        except Exception as e:
            logger.error(f"Qwen3 intent analysis failed: {str(e)}")
            state["error_messages"].append(f"Intent analysis error: {str(e)}")
            # Fallback
            state["query_type"] = QueryType.GENERAL_HOCKEY
            state["required_tools"] = [ToolType.VECTOR_SEARCH]
            return state
    
    async def _qwen3_tool_execution_node(self, state: AgentState) -> AgentState:
        """
        Execute sequential tool calls coordinated by Qwen3.
        
        Handles multi-turn tool execution with Qwen3's single-tool limitation.
        """
        try:
            state = await self.coordinator.execute_tool_sequence(state, max_iterations=5)
            logger.info(f"Tool execution complete: {len(state['tool_results'])} tools executed")
            return state
        except Exception as e:
            logger.error(f"Qwen3 tool execution failed: {str(e)}")
            state["error_messages"].append(f"Tool execution error: {str(e)}")
            return state
    
    async def _qwen3_response_synthesis_node(self, state: AgentState) -> AgentState:
        """
        Synthesize final response using Qwen3 Thinking.
        
        Combines all tool results into comprehensive professional response.
        """
        try:
            state = await self.coordinator.synthesize_response(state)
            logger.info("Response synthesis complete")
            return state
        except Exception as e:
            logger.error(f"Qwen3 response synthesis failed: {str(e)}")
            state["error_messages"].append(f"Synthesis error: {str(e)}")
            state["final_response"] = "I apologize, but I encountered an error generating the response."
            return state


# Global Qwen3-enhanced orchestrator instance
qwen3_orchestrator = HeartBeatQwen3Orchestrator()

