"""
Qwen3 Plan-Execute Orchestrator
TRUE AI REASONING: Model plans in natural language, we execute the plan

This solves the entity extraction problem:
1. Model reasons freely in text (no function calling pressure)
2. Model creates execution plan listing all entities  
3. We parse the plan and execute it
4. Model synthesizes with all gathered data
"""

import vertexai
from vertexai.preview.generative_models import GenerativeModel
from typing import Dict, List, Any
import json
import logging
import re
from datetime import datetime

from orchestrator.utils.state import AgentState, ToolType, ToolResult, create_initial_state
from orchestrator.nodes.pinecone_retriever import PineconeRetrieverNode
from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode

logger = logging.getLogger(__name__)


class Qwen3PlanExecutor:
    """
    Plan-Execute orchestrator - model reasons freely, we execute its plan.
    
    Flow:
    1. Model analyzes query and creates execution plan (pure reasoning)
    2. We parse plan to extract entities and tools needed
    3. We execute each step of the plan
    4. Model synthesizes with complete data
    """
    
    def __init__(self, project_id: str = "heartbeat-474020", location: str = "global"):
        """Initialize plan-executor."""
        self.project_id = project_id
        self.location = location
        
        vertexai.init(project=project_id, location=location)
        
        self.model_id = "publishers/qwen/models/qwen3-next-80b-a3b-thinking-maas"
        self.model = GenerativeModel(self.model_id)
        
        self.pinecone_node = PineconeRetrieverNode()
        self.parquet_node = ParquetAnalyzerNode()
        
        logger.info("Qwen3 Plan-Executor initialized")
    
    async def process_query(self, state: AgentState) -> AgentState:
        """Process query with plan-execute approach."""
        
        query = state["original_query"]
        current_date = state.get("current_date", "")
        current_season = state.get("current_season", "2025-2026")
        
        logger.info(f"Processing query with plan-execute: {query}")
        
        # STEP 1: Ultra-simple plan with TIME CONTEXT
        plan_prompt = f"""Today: {current_date}
Season: {current_season} (current NHL season)
Previous season: 2024-2025 (complete)

User asked: {query}

List player names and teams needed:"""
        
        try:
            plan_response = self.model.generate_content(
                plan_prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 1024}
            )
            execution_plan = plan_response.text
            logger.info(f"Model's execution plan created (length: {len(execution_plan)} chars)")
            logger.info(f"Plan text: {repr(execution_plan[:500])}")
        except Exception as e:
            logger.error(f"Planning failed: {str(e)}")
            execution_plan = "Unable to create plan - executing default"
        
        # STEP 2: Parse plan and execute
        tool_results_list = await self._execute_plan(execution_plan, query, state)
        state["tool_results"] = tool_results_list
        
        # STEP 3: Synthesize
        state = await self.synthesize_response(state)
        
        return state
    
    async def _execute_plan(
        self, 
        plan: str, 
        query: str,
        state: AgentState
    ) -> List[ToolResult]:
        """Execute the model's plan by parsing entities and calling tools."""
        
        results = []
        
        # Extract player names from plan
        player_pattern = r"(?:Players?|get_player_stats).*?(?:for|:)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
        player_matches = re.findall(player_pattern, plan)
        
        logger.info(f"Extracted {len(player_matches)} players from plan: {player_matches}")
        
        # Execute get_player_stats for each extracted player
        for player_name in player_matches:
            logger.info(f"Executing: get_player_stats(player_name='{player_name}')")
            
            try:
                player_data = await self.parquet_node.data_client.get_player_stats(
                    player_name=player_name,
                    season=state.get("current_season", "2024-2025")
                )
                
                results.append(ToolResult(
                    tool_type=ToolType.PARQUET_QUERY,
                    success=not player_data.get("error"),
                    data=player_data,
                    execution_time_ms=0
                ))
            except Exception as e:
                logger.error(f"Failed to get stats for {player_name}: {str(e)}")
        
        # Extract opponent names for matchup queries
        if any(kw in query.lower() for kw in ['vs', 'against', 'matchup']):
            opponent_pattern = r"(?:vs|against|matchup).*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
            opponent_matches = re.findall(opponent_pattern, plan + " " + query)
            
            for opponent in opponent_matches:
                if opponent.lower() not in ['montreal', 'canadiens']:
                    logger.info(f"Executing: get_matchup_stats(opponent='{opponent}')")
                    
                    try:
                        matchup_data = await self.parquet_node.data_client.get_matchup_data(
                            opponent=opponent,
                            season=state.get("current_season", "2024-2025")
                        )
                        
                        season_data = await self.parquet_node.data_client.get_season_results(
                            opponent=opponent,
                            season=state.get("current_season", "2024-2025")
                        )
                        
                        comprehensive = {
                            "analysis_type": "comprehensive_matchup",
                            "opponent": opponent,
                            "matchup_metrics": {"key_metrics": matchup_data.get("key_metrics", {})},
                            "game_results": season_data.get("record", {}) if season_data else {}
                        }
                        
                        results.append(ToolResult(
                            tool_type=ToolType.PARQUET_QUERY,
                            success=True,
                            data=comprehensive,
                            execution_time_ms=0
                        ))
                    except Exception as e:
                        logger.error(f"Failed to get matchup for {opponent}: {str(e)}")
        
        # Always get RAG context
        try:
            temp_state = create_initial_state(state["user_context"], query)
            rag_state = await self.pinecone_node.process(temp_state)
            results.append(ToolResult(
                tool_type=ToolType.VECTOR_SEARCH,
                success=True,
                data=rag_state.get("retrieval_results", {}),
                execution_time_ms=0
            ))
        except:
            pass
        
        logger.info(f"Plan execution complete: {len(results)} tools executed")
        return results
    
    async def synthesize_response(self, state: AgentState) -> AgentState:
        """Synthesize final response with all gathered data."""
        
        from orchestrator.agents.qwen3_reasoning_synthesis import build_reasoning_synthesis_prompt
        
        query = state["original_query"]
        
        # Get RAG context
        rag_context = ""
        try:
            from orchestrator.tools.pinecone_mcp_client import PineconeMCPClient
            pinecone = PineconeMCPClient()
            rag_results = await pinecone.search_hockey_context(query, namespace="context", top_k=3)
            if rag_results:
                rag_context = "\n".join([r.get("content", "")[:200] for r in rag_results[:3]])
        except:
            pass
        
        prompt = build_reasoning_synthesis_prompt(
            state,
            query,
            state["tool_results"],
            rag_context
        )
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": 0.3, "max_output_tokens": 8192}
            )
            
            state["final_response"] = response.text
            state["current_step"] = "complete"
            
            logger.info("Synthesis complete")
            return state
        
        except Exception as e:
            logger.error(f"Synthesis failed: {str(e)}")
            state["final_response"] = "Error synthesizing response"
            state["current_step"] = "error"
            return state


# Singleton
qwen3_plan_executor = Qwen3PlanExecutor()

