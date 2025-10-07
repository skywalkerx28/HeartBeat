"""
Qwen3-Next-80B Thinking Coordinator for HeartBeat Engine

Sequential tool orchestration coordinator that works with Qwen3's single-tool limitation.
Integrates seamlessly with existing LangGraph orchestrator.
"""

import vertexai
from vertexai.preview.generative_models import GenerativeModel, Tool, FunctionDeclaration
from typing import Dict, List, Any, Optional, Tuple
import json
import logging
from datetime import datetime

from orchestrator.utils.state import AgentState, ToolType, ToolResult, QueryType
from orchestrator.config.settings import settings
from orchestrator.tools.hockey_context_loader import get_hockey_context_loader
from orchestrator.tools.pinecone_mcp_client import PineconeMCPClient

logger = logging.getLogger(__name__)


class Qwen3ToolCoordinator:
    """
    Coordinates sequential tool calling with Qwen3-Next-80B Thinking.
    
    Handles the limitation that Qwen3 MaaS only supports one function
    declaration at a time by orchestrating multi-turn conversations.
    """
    
    def __init__(self, project_id: str = "heartbeat-474020", location: str = "global"):
        """Initialize Qwen3 coordinator."""
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Model ID for Qwen3 MaaS
        self.model_id = "publishers/qwen/models/qwen3-next-80b-a3b-thinking-maas"
        self.model = GenerativeModel(self.model_id)
        
        # Initialize Pinecone RAG client for dynamic expert hockey context
        self.pinecone_client = PineconeMCPClient()
        
        logger.info(f"Qwen3 Coordinator initialized (location: {location})")
        logger.info(f"RAG enabled: Pinecone context retrieval for expert analysis")
    
    async def retrieve_expert_context(
        self,
        query: str,
        tool_results: List[ToolResult],
        top_k: int = 5
    ) -> str:
        """
        Retrieve expert hockey context from Pinecone RAG based on query and data.
        
        Args:
            query: User's original query
            tool_results: Results from tool execution
            top_k: Number of context chunks to retrieve
            
        Returns:
            Expert context string for synthesis
        """
        try:
            # Build search query from user query + analysis types
            search_terms = [query]
            
            for result in tool_results:
                if result.success and result.data and isinstance(result.data, dict):
                    analysis_type = result.data.get("analysis_type", "")
                    if analysis_type:
                        search_terms.append(analysis_type)
            
            search_query = " ".join(search_terms)
            
            # Retrieve relevant context from Pinecone
            rag_results = await self.pinecone_client.search_hockey_context(
                query=search_query,
                namespace="context",
                top_k=top_k,
                score_threshold=0.7
            )
            
            if not rag_results:
                logger.warning("No RAG context retrieved, using fallback")
                return "SAMPLE SIZE: Minimum 50 minutes TOI for reliable PP stats. XGF% of 1.000 with low TOI = small sample."
            
            # Format retrieved contexts
            context_parts = []
            for i, rag_item in enumerate(rag_results, 1):
                content = rag_item.get("content", "")
                score = rag_item.get("score", 0)
                context_parts.append(f"[Context {i}] {content[:300]}")
            
            expert_context = "\n\n".join(context_parts)
            logger.info(f"Retrieved {len(rag_results)} expert contexts from Pinecone RAG")
            
            return expert_context
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {str(e)}")
            # Fallback to basic rules
            return "SAMPLE SIZE: Minimum 50 minutes TOI for reliable PP stats. XGF% of 1.000 with low TOI = small sample."
    
    def get_system_prompt(self, state: Optional[AgentState] = None) -> str:
        """
        Get HeartBeat core system prompt with time awareness.
        
        Args:
            state: AgentState with current_date and current_season for time context
        """
        # Extract time context from state, or calculate dynamically if missing
        if state and "current_date" in state:
            current_date = state["current_date"]
            current_season = state["current_season"]
        else:
            # Fallback: calculate current date/season dynamically (NEVER hardcode)
            from datetime import datetime
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            
            # NHL season calculation
            current_year = now.year
            current_month = now.month
            if current_month >= 10:  # Oct-Dec: current year to next year
                current_season = f"{current_year}-{current_year + 1}"
            else:  # Jan-Sep: previous year to current year
                current_season = f"{current_year - 1}-{current_year}"
        
        return f"""You are STANLEY - the official AI analytics assistant for the Montreal Canadiens.

CRITICAL TIME CONTEXT (MEMORIZE):
- Today's Date: {current_date}
- Current NHL Season: {current_season}
- Your Team: Montreal Canadiens (MTL)

YOU ARE: HeartBeat Engine orchestrator - Montreal Canadiens' professional hockey analytics system.

YOUR PRIMARY ROLE: Execute data tools to retrieve information, then synthesize insights.

PROFESSIONAL COMMUNICATION STANDARDS (MANDATORY):
- NEVER use emojis in any response (🚫 ❌ ✅ 🏒 etc.)
- Use professional, technical hockey terminology
- Maintain serious, analytical tone at all times
- This is professional sports analytics, not casual conversation

TOOL ORCHESTRATION RULES (CRITICAL):
1. When a tool/function is available → CALL IT with appropriate parameters
2. DO NOT ask for clarification → Function descriptions provide all context
3. DO NOT explain what you'll do → EXECUTE the function immediately
4. Tool calls may return partial data → This is normal (incremental development)
5. Your job: Orchestrate tools, NOT have conversations about calling tools

AVAILABLE TOOLS:
- search_hockey_knowledge: Retrieve hockey concepts, tactics, rules, patterns
- query_game_data: Execute SQL on Montreal Canadiens statistics/play-by-play
- calculate_hockey_metrics: Compute Corsi, xG, zone entries/exits, possession
- generate_visualization: Create shot maps, heatmaps, charts

WHEN ANALYZING QUERIES:
- Identify query type and required tools
- Determine execution sequence
- Plan multi-step data gathering

WHEN TOOLS ARE AVAILABLE:
- IMMEDIATELY call the function with proper arguments
- Use function parameters to specify what data you need
- Trust that tools will return relevant information

WHEN SYNTHESIZING RESPONSES:
- Use retrieved data to generate insights
- Cite specific statistics
- Provide actionable recommendations
- Use authentic Montreal Canadiens coaching terminology

FOCUS: Montreal Canadiens performance, matchups, strategic intelligence, player development.

IMPORTANT: You can only request ONE tool per response. Plan your analysis to use tools sequentially."""
    
    async def analyze_intent(self, state: AgentState) -> AgentState:
        """
        Analyze query intent and determine required tools (replaces IntentAnalyzerNode).
        
        This is the entry point for Qwen3-based orchestration.
        """
        query = state["original_query"]
        user_context = state["user_context"]
        
        logger.info(f"Analyzing intent for: {query[:100]}...")
        
        # Create analysis prompt with time context
        prompt = f"""{self.get_system_prompt(state)}

User Role: {user_context.role.value}
Team Access: {', '.join(user_context.team_access)}

User Query: {query}

Analyze this query and identify:
1. Query type (player analysis, team performance, game analysis, matchup comparison, tactical analysis, statistical query, or general hockey)
2. Required information (what data/context is needed)
3. Which tool to request FIRST

Available tools (request ONE):
- search_hockey_knowledge: Retrieve hockey context, rules, tactics, historical patterns
- query_game_data: Execute SQL queries on game statistics and play-by-play data
- calculate_hockey_metrics: Compute advanced metrics (Corsi, xG, zone analysis, possession)
- generate_visualization: Create shot maps, heatmaps, performance charts

Respond in this format:
QUERY_TYPE: [type]
NEEDS: [what information is required]
FIRST_TOOL: [tool name]
REASONING: [why this tool first]"""
        
        try:
            # Intent analysis doesn't use function calling, but keep config consistent
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 1024,
                    "top_p": 0.9
                    # top_k removed for consistency with function calling config
                }
            )
            
            analysis_text = response.text
            
            # Parse response
            intent_analysis = self._parse_intent_analysis(analysis_text, query)
            
            # Update state
            state["intent_analysis"] = intent_analysis
            state["query_type"] = intent_analysis["query_type"]
            state["required_tools"] = intent_analysis["required_tools"]
            state["current_step"] = "intent_analyzed"
            
            logger.info(f"Intent analysis complete: {intent_analysis['query_type'].value}")
            
            return state
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            state["error_messages"].append(f"Intent analysis error: {str(e)}")
            # Fallback to simple routing
            state["query_type"] = QueryType.GENERAL_HOCKEY
            state["required_tools"] = [ToolType.VECTOR_SEARCH]
            return state
    
    async def execute_tool_sequence(
        self,
        state: AgentState,
        max_iterations: int = 15  # Allow model to gather comprehensive data
    ) -> AgentState:
        """
        Execute sequential tool calls with Qwen3 Thinking.
        
        This handles the multi-turn conversation to gather all needed data.
        """
        query = state["original_query"]
        conversation_history = []
        iteration = 0
        
        logger.info("Starting tool sequence execution...")
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Tool iteration {iteration}/{max_iterations}")
            
            # Build conversation context
            context = self._build_conversation_context(
                state, 
                conversation_history,
                query
            )
            
            # Determine next tool needed
            logger.info(f"Requesting next tool (iteration {iteration})...")
            tool_info = await self._request_next_tool(context, state)
            
            if not tool_info:
                # No more tools needed
                logger.info("Tool sequence complete - no more tools requested")
                break
            
            logger.info(f"Tool requested: {tool_info['tool_name']} with args: {tool_info['arguments']}")
            
            # Execute the requested tool
            tool_result = await self._execute_single_tool(
                tool_info["tool_name"],
                tool_info["arguments"],
                state
            )
            
            # Add to state and conversation
            state["tool_results"].append(tool_result)
            
            # Build rich result summary for next iteration
            result_summary = "FAILED" if not tool_result.success else "SUCCESS"
            if tool_result.success and tool_result.data and isinstance(tool_result.data, dict):
                analysis_type = tool_result.data.get("analysis_type", "")
                if analysis_type == "matchup":
                    result_summary = f"Retrieved {tool_result.data.get('total_matchup_rows', 0)} matchup metrics vs {tool_result.data.get('opponent')}"
                elif analysis_type == "season_results":
                    result_summary = f"Retrieved {tool_result.data.get('total_games', 0)} game results"
                elif analysis_type == "power_play":
                    result_summary = f"Retrieved {tool_result.data.get('total_pp_units', 0)} PP units"
                else:
                    result_summary = f"Retrieved {analysis_type} data"
            
            conversation_history.append({
                "iteration": iteration,
                "tool": tool_info["tool_name"],
                "args": tool_info["arguments"],
                "result": tool_result.data,
                "result_summary": result_summary,
                "success": tool_result.success
            })
            
            # Check if we have enough information
            if self._has_sufficient_data(state, conversation_history):
                logger.info("Sufficient data gathered")
                break
        
        state["current_step"] = "tools_executed"
        state["iteration_count"] = iteration
        
        return state
    
    async def synthesize_response(self, state: AgentState) -> AgentState:
        """
        Synthesize final response using all gathered data.
        
        Replaces ResponseSynthesizerNode with Qwen3-based synthesis.
        """
        query = state["original_query"]
        tool_results = state["tool_results"]
        
        logger.info("Synthesizing final response...")
        
        # Build SIMPLE synthesis prompt that lets model reason freely
        from orchestrator.agents.qwen3_reasoning_synthesis import build_reasoning_synthesis_prompt
        
        # Retrieve RAG context (but keep it optional/minimal)
        rag_context = ""
        try:
            rag_context = await self.retrieve_expert_context(query, tool_results, top_k=3)
        except:
            pass  # Continue without RAG if it fails
        
        # Let model reason with full data access
        prompt = build_reasoning_synthesis_prompt(state, query, tool_results, rag_context)
        
        try:
            # Qwen3 Thinking needs VERY HIGH token limit for reasoning + detailed analysis
            # Reasoning tokens are HIDDEN but count toward max_output_tokens
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 8192  # High limit for Thinking model reasoning + output
                }
            )
            
            final_response = response.text
            
            # Update state
            state["final_response"] = final_response
            state["current_step"] = "complete"
            
            # Build evidence chain
            evidence = []
            for result in tool_results:
                if result.success and result.citations:
                    evidence.extend(result.citations)
            state["evidence_chain"] = evidence
            
            logger.info("Response synthesis complete")
            
            return state
            
        except Exception as e:
            logger.error(f"Response synthesis failed: {str(e)}")
            state["error_messages"].append(f"Synthesis error: {str(e)}")
            state["final_response"] = "I apologize, but I encountered an error synthesizing the response. Please try again."
            return state
    
    async def _request_next_tool(
        self,
        context: str,
        state: AgentState
    ) -> Optional[Dict[str, Any]]:
        """Request the next tool from Qwen3."""
        
        # Create tool declaration for current need
        tool_decl = self._create_next_tool_declaration(state)
        
        if not tool_decl:
            return None
        
        tool = Tool(function_declarations=[tool_decl])
        
        # CRITICAL: Qwen3 Thinking + function calling requires MINIMAL prompts
        # Complex prompts trigger safety filters (finish_reason: 2)
        # Use generic action - function declaration provides all context needed
        tool_name = tool_decl.name if hasattr(tool_decl, 'name') else "query_game_data"
        
        # EXPLICIT: Tell model to execute the function that's available
        # Include the original query for context in function parameters
        original_query = state.get("original_query", "")
        
        if "search" in tool_name or "knowledge" in tool_name:
            tool_prompt = f"Execute the search function. Query: {original_query[:80]}"
        elif "query" in tool_name or "data" in tool_name:
            tool_prompt = f"Execute the query function. Query: {original_query[:80]}"
        elif "calculate" in tool_name or "metric" in tool_name:
            tool_prompt = f"Execute the calculate function. Query: {original_query[:80]}"
        elif "visual" in tool_name:
            tool_prompt = f"Execute the visualization function. Query: {original_query[:80]}"
        else:
            tool_prompt = f"Execute the function. Query: {original_query[:80]}"
        
        logger.info(f"Tool prompt (first 200 chars): {tool_prompt[:200]}...")
        
        try:
            # CRITICAL QWEN3 FUNCTION CALLING CONSTRAINTS:
            # 1. top_k + max_output_tokens = 0 parts  
            # 2. max_output_tokens < 1024 = safety filter (finish_reason: 2)
            # Solution: Only use temperature for function calling
            response = self.model.generate_content(
                tool_prompt,
                tools=[tool],
                generation_config={
                    "temperature": 0.2
                    # max_output_tokens removed - causes safety filters < 1024
                    # top_p removed - not needed for function calling
                    # top_k removed - breaks function calling entirely
                }
            )
            
            logger.info(f"Got response with {len(response.candidates)} candidates")
            
            # Try to get response text safely
            try:
                resp_text = response.text if response.text else "empty"
                logger.info(f"Response text: '{resp_text[:100]}'")
            except:
                logger.info("Response has no accessible text")
            
            # Check if response is empty
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning("Response has 0 parts - model didn't generate function call or text")
                logger.warning(f"This may be due to safety settings or prompt issues")
                return None
            
            # Extract function call
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        logger.info(f"✓ Function call detected: {part.function_call.name}")
                        return {
                            "tool_name": part.function_call.name,
                            "arguments": dict(part.function_call.args)
                        }
            
            # No tool requested
            logger.warning("No function call found in response parts")
            return None
            
        except Exception as e:
            logger.error(f"Tool request failed: {str(e)}", exc_info=True)
            return None
    
    def _create_next_tool_declaration(self, state: AgentState) -> Optional[FunctionDeclaration]:
        """
        Create function declaration for next tool.
        
        REASONING-FIRST APPROACH: Offer the model the MOST LIKELY next tool,
        but let it decide autonomously. Don't restrict to predetermined list.
        """
        
        completed_tools = [r.tool_type for r in state["tool_results"] if r.success]
        
        logger.info(f"Tools used so far: {[t.value for t in completed_tools]}")
        
        # Intelligent tool suggestion based on query and what's been gathered
        query_lower = state.get("original_query", "").lower()
        
        # Priority 1: If asking about "vs/against" opponent and no matchup data yet
        if any(kw in query_lower for kw in ['vs', 'against', 'matchup']) and ToolType.PARQUET_QUERY not in completed_tools:
            logger.info("Suggesting: query_game_data (for matchup/game data)")
            return self._get_tool_declaration(ToolType.PARQUET_QUERY)
        
        # Priority 2: If we have matchup metrics but no game results for that opponent
        if ToolType.PARQUET_QUERY in completed_tools:
            # Check if we got matchup data but maybe need season results too
            has_matchup = any(r.data.get("analysis_type") == "matchup" for r in state["tool_results"] if r.success and isinstance(r.data, dict))
            has_season = any(r.data.get("analysis_type") == "season_results" for r in state["tool_results"] if r.success and isinstance(r.data, dict))
            
            if has_matchup and not has_season:
                logger.info("Suggesting: query_game_data (for season results to complement matchup data)")
                return self._get_tool_declaration(ToolType.PARQUET_QUERY)
        
        # Priority 3: If no RAG context yet, offer search
        if ToolType.VECTOR_SEARCH not in completed_tools:
            logger.info("Suggesting: search_hockey_knowledge (for expert context)")
            return self._get_tool_declaration(ToolType.VECTOR_SEARCH)
        
        # Priority 4: Calculate metrics if we have raw data
        if completed_tools and ToolType.CALCULATE_METRICS not in completed_tools:
            logger.info("Suggesting: calculate_hockey_metrics")
            return self._get_tool_declaration(ToolType.CALCULATE_METRICS)
        
        # All major tools used or model has enough
        logger.info("All major tools offered - model can stop if satisfied")
        return None
    
    def _get_tool_declaration(self, tool_type: ToolType) -> FunctionDeclaration:
        """Get function declaration for a specific tool type."""
        
        if tool_type == ToolType.VECTOR_SEARCH:
            return FunctionDeclaration(
                name="search_hockey_knowledge",
                description="Search hockey context, rules, tactics, and historical patterns from knowledge base",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for hockey context"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results (default: 5)"
                        }
                    },
                    "required": ["query"]
                }
            )
        
        elif tool_type == ToolType.PARQUET_QUERY:
            return FunctionDeclaration(
                name="query_game_data",
                description="Execute SQL query on Montreal Canadiens game statistics and play-by-play data",
                parameters={
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "SQL query to execute"
                        },
                        "filters": {
                            "type": "object",
                            "description": "Additional filters (date range, opponent, etc.)"
                        }
                    },
                    "required": ["sql_query"]
                }
            )
        
        elif tool_type == ToolType.CALCULATE_METRICS:
            return FunctionDeclaration(
                name="calculate_hockey_metrics",
                description="Calculate advanced hockey metrics like Corsi, xG, zone analysis, possession",
                parameters={
                    "type": "object",
                    "properties": {
                        "metric_type": {
                            "type": "string",
                            "description": "Type of metric",
                            "enum": ["corsi", "xg", "zone_entries", "zone_exits", "possession", "shot_quality"]
                        },
                        "context": {
                            "type": "object",
                            "description": "Context filters"
                        }
                    },
                    "required": ["metric_type"]
                }
            )
        
        elif tool_type == ToolType.VISUALIZATION:
            return FunctionDeclaration(
                name="generate_visualization",
                description="Generate hockey visualizations like shot maps, heatmaps, charts",
                parameters={
                    "type": "object",
                    "properties": {
                        "viz_type": {
                            "type": "string",
                            "description": "Type of visualization",
                            "enum": ["shot_map", "heatmap", "performance_chart", "zone_analysis"]
                        },
                        "data_source": {
                            "type": "string",
                            "description": "Data to visualize"
                        }
                    },
                    "required": ["viz_type", "data_source"]
                }
            )
        
        # Default fallback
        return FunctionDeclaration(
            name="search_hockey_knowledge",
            description="Search hockey knowledge",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        )
    
    async def _execute_single_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        state: AgentState
    ) -> ToolResult:
        """Execute a single tool and return result."""
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            
            # Add tool arguments to state for node processing
            state["tool_arguments"] = arguments
            
            # Map tool name to execution via existing nodes
            if tool_name == "search_hockey_knowledge":
                from orchestrator.nodes.pinecone_retriever import PineconeRetrieverNode
                node = PineconeRetrieverNode()
                # Call node's process method with state
                updated_state = await node.process(state)
                tool_type = ToolType.VECTOR_SEARCH
                
                # Extract result from updated state
                if updated_state["tool_results"]:
                    latest_result = updated_state["tool_results"][-1]
                    return latest_result
                else:
                    # Successful but no explicit result
                    result_data = {
                        "context": updated_state.get("retrieved_context", []),
                        "success": True
                    }
                
            elif tool_name == "query_game_data":
                from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode
                node = ParquetAnalyzerNode()
                updated_state = await node.process(state)
                tool_type = ToolType.PARQUET_QUERY
                
                if updated_state["tool_results"]:
                    latest_result = updated_state["tool_results"][-1]
                    return latest_result
                else:
                    result_data = {
                        "analytics": updated_state.get("analytics_data", {}),
                        "success": True
                    }
                
            elif tool_name == "calculate_hockey_metrics":
                from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode
                node = ParquetAnalyzerNode()
                updated_state = await node.process(state)
                tool_type = ToolType.CALCULATE_METRICS
                
                if updated_state["tool_results"]:
                    latest_result = updated_state["tool_results"][-1]
                    return latest_result
                else:
                    result_data = {
                        "metrics": updated_state.get("analytics_data", {}),
                        "success": True
                    }
                
            elif tool_name == "generate_visualization":
                # Placeholder - will implement when visualization node is ready
                result_data = {
                    "visualization_spec": arguments,
                    "status": "pending_implementation"
                }
                tool_type = ToolType.VISUALIZATION
            
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ToolResult(
                tool_type=tool_type,
                success=True,
                data=result_data,
                execution_time_ms=execution_time,
                citations=result_data.get("citations", []) if isinstance(result_data, dict) else []
            )
            
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            logger.exception("Full traceback:")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ToolResult(
                tool_type=ToolType.VECTOR_SEARCH,  # Fallback
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    def _build_conversation_context(
        self,
        state: AgentState,
        conversation_history: List[Dict],
        query: str
    ) -> str:
        """
        Build conversation context that encourages comprehensive analysis.
        Model should think: "Do I have EVERYTHING I need to answer this properly?"
        """
        
        # Start with the user's question
        context = f"""Montreal Canadiens Analytics Query: {query}

"""
        
        if conversation_history:
            context += "Data retrieved so far:\n"
            for item in conversation_history:
                context += f"{item['iteration']}. {item['tool']}: {item.get('result_summary', 'Retrieved')}\n"
            
            # Encourage model to think about completeness
            context += f"""
You've gathered {len(conversation_history)} data source(s).

Think: To FULLY answer "{query}", do you need:
- Game results (wins/losses)?
- Player statistics?
- Matchup metrics (xG, Corsi)?
- Historical context or tactics?

If you have everything, stop. If not, call the next tool you need.
"""
        else:
            # First call - encourage strategic thinking
            context += """Think about what data you need to answer this comprehensively.

For example, if they ask "how did we do against Team X":
- You likely need: matchup metrics AND game results (W/L record)
- Maybe also: player performance in those games

Start by calling the most important tool first.
"""
        
        return context
    
    async def _build_synthesis_prompt_simple(
        self,
        state: AgentState,
        query: str,
        tool_results: List[ToolResult]
    ) -> str:
        """
        Build SIMPLE prompt for synthesis to avoid safety filters.
        
        CRITICAL: Complex prompts trigger Vertex AI safety filters.
        Keep this minimal and direct, but include time context.
        """
        
        # Extract time context
        current_date = state.get("current_date", "")
        current_season = state.get("current_season", "")
        
        # Retrieve expert hockey context from Pinecone RAG (dynamic, not hardcoded!)
        expert_guidance = await self.retrieve_expert_context(
            query=query,
            tool_results=tool_results,
            top_k=5
        )
        
        # Build data summary with actual hockey information
        data_summary = []
        
        for result in tool_results:
            if result.success and result.data and isinstance(result.data, dict):
                # Extract key information based on analysis type
                analysis_type = result.data.get("analysis_type", "")
                
                if analysis_type == "power_play":
                    # Include actual PP unit players with TOI for sample size awareness
                    pp_info = f"Power Play Data ({result.data.get('season')}): {result.data.get('total_pp_units')} units. "
                    if result.data.get('top_unit'):
                        top = result.data['top_unit']
                        toi_min = top.get('TOI(min)', '')
                        pp_info += f"Top unit: {top.get('Players', '')[:150]} | TOI: {toi_min} | XGF%: {top.get('XGF%', 0):.3f}"
                    data_summary.append(pp_info)
                
                elif analysis_type == "matchup":
                    # Include matchup metrics WITH ACTUAL NUMBERS (single line to avoid filters)
                    matchup_info = f"MTL vs {result.data.get('opponent')} ({result.data.get('season')}): "
                    if result.data.get('key_metrics'):
                        # Format top 8 metrics in compact format
                        metrics = []
                        for metric_name, values in list(result.data['key_metrics'].items())[:8]:
                            mtl = values.get('mtl', 0)
                            opp = values.get('opponent', 0)
                            metrics.append(f"{metric_name}={mtl:.2f}v{opp:.2f}")
                        matchup_info += " | ".join(metrics)
                    data_summary.append(matchup_info)
                
                elif analysis_type == "player_stats" or analysis_type == "player_performance":
                    # Include player stats with key metrics
                    player_info = f"Player: {result.data.get('player_name', 'Unknown')} - "
                    if result.data.get('stats'):
                        stats = result.data['stats']
                        player_info += f"GP={stats.get('GP', 0)} G={stats.get('G', 0)} A={stats.get('A', 0)} PTS={stats.get('PTS', 0)} "
                        player_info += f"ES_TOI={stats.get('Player ES TOI (Minutes)', 0):.1f}min"
                    data_summary.append(player_info)
                
                elif analysis_type == "season_results":
                    # Include game results
                    result_info = f"Season {result.data.get('season')}: {result.data.get('total_games')} games. "
                    if result.data.get('record'):
                        result_info += f"Record: {result.data['record'].get('record_string')}"
                    data_summary.append(result_info)
                
                else:
                    # Generic fallback - show key fields only
                    generic_info = f"{analysis_type}: "
                    if isinstance(result.data, dict):
                        key_fields = {k: v for k, v in result.data.items() if isinstance(v, (int, float, str)) and not k.startswith('_')}
                        generic_info += str(key_fields)[:300]
                    else:
                        generic_info += str(result.data)[:200]
                    data_summary.append(generic_info)
        
        # SIMPLE prompt - include time context, data, AND RAG-retrieved expert hockey knowledge
        prompt = f"""STANLEY - Montreal Canadiens AI Assistant

Date: {current_date} | Season: {current_season}

EXPERT HOCKEY CONTEXT (USE THIS):
{expert_guidance}

Question: {query}

Data Available: {' | '.join(data_summary[:3])}

Analyze professionally with NO EMOJIS:"""
        
        return prompt
    
    def _parse_intent_analysis(self, analysis_text: str, query: str) -> Dict[str, Any]:
        """Parse Qwen3's intent analysis response."""
        
        # Default values
        query_type = QueryType.GENERAL_HOCKEY
        required_tools = [ToolType.VECTOR_SEARCH]
        
        # Parse response
        lines = analysis_text.strip().split('\n')
        intent_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                intent_data[key.strip().lower()] = value.strip()
        
        # Map query type
        query_type_str = intent_data.get('query_type', '').lower()
        if 'player' in query_type_str:
            query_type = QueryType.PLAYER_ANALYSIS
        elif 'team' in query_type_str or 'performance' in query_type_str:
            query_type = QueryType.TEAM_PERFORMANCE
        elif 'game' in query_type_str:
            query_type = QueryType.GAME_ANALYSIS
        elif 'matchup' in query_type_str or 'comparison' in query_type_str:
            query_type = QueryType.MATCHUP_COMPARISON
        elif 'tactical' in query_type_str:
            query_type = QueryType.TACTICAL_ANALYSIS
        elif 'stat' in query_type_str:
            query_type = QueryType.STATISTICAL_QUERY
        
        # Determine required tools from first tool and query needs
        first_tool = intent_data.get('first_tool', '').lower()
        needs = intent_data.get('needs', '').lower()
        
        # Start with first tool
        required_tools = []
        if 'knowledge' in first_tool or 'search' in first_tool:
            required_tools.append(ToolType.VECTOR_SEARCH)
        elif 'query' in first_tool or 'data' in first_tool:
            required_tools.append(ToolType.PARQUET_QUERY)
        elif 'calculate' in first_tool or 'metric' in first_tool:
            required_tools.append(ToolType.CALCULATE_METRICS)
        elif 'visual' in first_tool:
            required_tools.append(ToolType.VISUALIZATION)
        
        # Add additional tools based on query complexity
        # For matchup/performance queries, typically need data query
        if query_type in [QueryType.MATCHUP_COMPARISON, QueryType.TEAM_PERFORMANCE, QueryType.PLAYER_ANALYSIS]:
            if ToolType.PARQUET_QUERY not in required_tools:
                required_tools.append(ToolType.PARQUET_QUERY)
        
        # If analysis/tactics mentioned, add knowledge search first if not present
        if query_type == QueryType.TACTICAL_ANALYSIS and ToolType.VECTOR_SEARCH not in required_tools:
            required_tools.insert(0, ToolType.VECTOR_SEARCH)
        
        # Fallback if nothing matched
        if not required_tools:
            required_tools = [ToolType.PARQUET_QUERY]
        
        return {
            "query_type": query_type,
            "required_tools": required_tools,
            "reasoning": intent_data.get('reasoning', ''),
            "needs": intent_data.get('needs', ''),
            "raw_analysis": analysis_text
        }
    
    def _has_sufficient_data(self, state: AgentState, conversation_history: List[Dict]) -> bool:
        """Determine if we have sufficient data to answer the query."""
        
        # Check if we have successful results
        successful_tools = sum(1 for r in state["tool_results"] if r.success)
        
        # If we have at least one successful tool result, we can proceed
        if successful_tools >= 1:
            return True
        
        # If we've tried multiple times without success, stop
        if len(conversation_history) >= 3:
            return True
        
        return False


# Global coordinator instance
qwen3_coordinator = Qwen3ToolCoordinator()

