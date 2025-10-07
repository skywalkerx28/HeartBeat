"""
Qwen3 Best Practices Orchestrator - PROPER AI REASONING ARCHITECTURE

This follows elite AI company practices (OpenAI, Anthropic, Google):
1. Give model ALL tools upfront
2. Let model decide what to call and when
3. Trust the reasoning - don't intercept
4. Continuous reasoning loop until model says "done"

Key Differences from Current Implementation:
- NO _suggest_next_tool() logic (trust the model)
- NO sequential tool offering (give all tools at once)
- NO separation of reasoning and execution (integrated flow)
- YES to model autonomy (model controls its own workflow)
"""

import vertexai
from vertexai.preview.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime

from orchestrator.utils.state import AgentState, ToolType, ToolResult, create_initial_state
from orchestrator.nodes.pinecone_retriever import PineconeRetrieverNode
from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode
from orchestrator.tools.nhl_roster_client import NHLRosterClient, NHLLiveGameClient
from orchestrator.tools.data_catalog import HeartBeatDataCatalog

logger = logging.getLogger(__name__)


class Qwen3BestPracticesOrchestrator:
    """
    Elite AI Orchestrator - Following OpenAI/Anthropic/Google Best Practices
    
    Philosophy:
    - Model SEES all tools at once
    - Model DECIDES what to call
    - Model THINKS and ACTS in one flow
    - We OBSERVE, not CONTROL
    
    The model is the autonomous agent. We're just the executor.
    """
    
    def __init__(self, project_id: str = "heartbeat-474020", location: str = "global"):
        """Initialize with full tool transparency."""
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Qwen3 Thinking model
        self.model_id = "publishers/qwen/models/qwen3-next-80b-a3b-thinking-maas"
        self.model = GenerativeModel(self.model_id)
        
        # Initialize data nodes
        self.pinecone_node = PineconeRetrieverNode()
        self.parquet_node = ParquetAnalyzerNode()
        
        # Initialize NHL clients
        self.roster_client = NHLRosterClient()
        self.live_game_client = NHLLiveGameClient()
        
        # Initialize data catalog
        from orchestrator.config.settings import settings
        self.data_catalog = HeartBeatDataCatalog(settings.parquet.data_directory)
        
        # Define ALL tools once - model gets full visibility
        self.all_tools = self._define_all_tools()
        self.tool_executor = Tool(function_declarations=list(self.all_tools.values()))
        
        logger.info(f"Qwen3 Best Practices Orchestrator initialized with {len(self.all_tools)} tools")
    
    def _define_all_tools(self) -> Dict[str, FunctionDeclaration]:
        """
        Define ALL available tools upfront.
        
        Best Practice: Model needs to see the FULL toolkit to make informed decisions.
        """
        return {
            # Hockey Knowledge Search
            "search_hockey_knowledge": FunctionDeclaration(
                name="search_hockey_knowledge",
                description="Search hockey concepts, tactics, strategies, metric explanations from knowledge base. Use for understanding terms, strategies, or context.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for hockey knowledge (e.g., 'Corsi percentage', 'power play strategies', 'zone exit tactics')"
                        }
                    },
                    "required": ["query"]
                }
            ),
            
            # NHL Roster Data (ALL TEAMS)
            "get_team_roster": FunctionDeclaration(
                name="get_team_roster",
                description="Get current NHL roster for ANY team (all 32 teams). Returns player names, positions, jersey numbers, team assignments. Data updated daily at 10 PM ET.",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team abbreviation (e.g., 'MTL' for Montreal, 'TOR' for Toronto, 'BOS' for Boston, 'EDM' for Edmonton, 'PIT' for Pittsburgh, etc.)"
                        },
                        "season": {
                            "type": "string",
                            "description": "NHL season (e.g., '2024-2025'). Defaults to current season.",
                            "default": "current"
                        }
                    },
                    "required": ["team"]
                }
            ),
            
            # Player Search (CROSS-LEAGUE)
            "search_player_info": FunctionDeclaration(
                name="search_player_info",
                description="Find player information across ALL NHL rosters. Use when you need to find which team a player is on or get player details without knowing their team.",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_name": {
                            "type": "string",
                            "description": "Player name to search for (e.g., 'Sidney Crosby', 'Connor McDavid', 'Ivan Demidov')"
                        }
                    },
                    "required": ["player_name"]
                }
            ),
            
            # Live Game Data
            "get_live_game_data": FunctionDeclaration(
                name="get_live_game_data",
                description="Get real-time NHL game data including score, period, clock, shots, goals, player stats. Use for current game status or today's schedule.",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team abbreviation (e.g., 'MTL'). Optional - if omitted, returns all games for the date."
                        },
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format. Defaults to today."
                        },
                        "game_id": {
                            "type": "integer",
                            "description": "Specific NHL game ID. Optional."
                        }
                    }
                }
            ),
            
            # Montreal Historical Data
            "query_game_data": FunctionDeclaration(
                name="query_game_data",
                description="Query Montreal Canadiens historical data: season results, performance metrics, matchup stats, player statistics. Use for past games and historical analysis.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query_description": {
                            "type": "string",
                            "description": "Description of what data to retrieve (e.g., 'Montreal vs Toronto 2024-2025 season results', 'Suzuki goals and assists', 'power play stats')"
                        }
                    },
                    "required": ["query_description"]
                }
            ),
            
            # Advanced Calculations
            "calculate_hockey_metrics": FunctionDeclaration(
                name="calculate_hockey_metrics",
                description="Compute advanced hockey analytics from retrieved data (Corsi, xG differential, per-60 rates, etc.)",
                parameters={
                    "type": "object",
                    "properties": {
                        "metric_type": {
                            "type": "string",
                            "description": "Type of metric to calculate"
                        }
                    },
                    "required": ["metric_type"]
                }
            ),
            
            # Visualization
            "generate_visualization": FunctionDeclaration(
                name="generate_visualization",
                description="Create charts, heatmaps, shot maps from data",
                parameters={
                    "type": "object",
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "description": "Type of visualization"
                        },
                        "data_reference": {
                            "type": "string",
                            "description": "Reference to data to visualize"
                        }
                    },
                    "required": ["chart_type"]
                }
            ),
        }
    
    def _create_system_prompt(self) -> str:
        """
        Create system prompt that teaches the model HOW to reason.
        
        Best Practice: Teach decision-making patterns, not rules.
        """
        return """You are STANLEY, an expert NHL analytics AI for the Montreal Canadiens.

YOUR CAPABILITIES:
You have access to powerful tools for NHL data and analysis. You can see ALL available tools and decide which ones to use, when to use them, and in what order.

REASONING APPROACH (How Elite AI Thinks):

1. UNDERSTAND THE QUESTION
   - What is the user really asking?
   - What type of information do I need?
   - Is this about: rosters, live games, historical stats, concepts, or analysis?

2. IDENTIFY REQUIRED DATA
   - Do I need current roster info? → use get_team_roster or search_player_info
   - Do I need live game data? → use get_live_game_data
   - Do I need historical stats? → use query_game_data
   - Do I need to understand a concept? → use search_hockey_knowledge

3. EXECUTE STRATEGICALLY
   - Call the tools you identified
   - You can call MULTIPLE tools if needed (don't stop at one!)
   - Review the results - do you have everything to answer?
   - If not, call MORE tools to fill gaps

4. SYNTHESIZE ANSWER
   - Combine all gathered information
   - Provide complete, accurate response
   - Cite specific data points

CRITICAL DECISION PATTERNS:

Question Type: "What team is [player] on?"
→ THINK: This is a roster question about a specific player
→ ACTION: search_player_info(player_name) OR get_team_roster(likely_team)
→ DECIDE: If I don't know the team, use search_player_info first

Question Type: "Who are [team]'s [position]?"
→ THINK: This is a roster question about a team
→ ACTION: get_team_roster(team) then filter by position
→ DECIDE: I need the full roster, then I can filter

Question Type: "What's the score of today's game?"
→ THINK: This is about LIVE, CURRENT game data
→ ACTION: get_live_game_data(team or no params for all games)
→ DECIDE: Real-time data, not historical

Question Type: "How did Montreal perform vs [team] last season?"
→ THINK: This is HISTORICAL performance data
→ ACTION: query_game_data("Montreal vs [team] 2024-2025 season results")
→ DECIDE: Past games, need historical query tool

AUTONOMY PRINCIPLES:
- YOU decide which tools to use (I don't control you)
- YOU decide when you have enough information (stop when ready)
- YOU decide the order of operations (plan your approach)
- THINK before acting (reason about what you need)
- DON'T GUESS - if you need data, call a tool to get it

Remember: You're an autonomous agent. Think strategically, gather comprehensively, synthesize professionally."""

    async def process_query(self, state: AgentState) -> AgentState:
        """
        Process query with TRUE model autonomy.
        
        Best Practice: One continuous reasoning loop where model controls flow.
        """
        query = state["original_query"]
        logger.info(f"Processing query with best practices: {query}")
        
        # Build initial context with system prompt
        system_prompt = self._create_system_prompt()
        user_message = f"""Question: {query}

Think about what information you need, then call the appropriate tools. You can call multiple tools if needed."""
        
        # Continuous reasoning loop
        conversation_history = []
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Reasoning iteration {iteration}/{max_iterations}")
            
            # Build full context
            if conversation_history:
                # Include previous tool results
                context_parts = [system_prompt, user_message, "\n\nPrevious tool calls and results:"]
                for turn in conversation_history:
                    context_parts.append(f"\nTool: {turn['tool']}")
                    context_parts.append(f"Arguments: {turn['args']}")
                    context_parts.append(f"Result: {turn['result']}")
                context_parts.append("\n\nBased on the above results, do you need more data? Or can you answer now?")
                full_context = "\n".join(context_parts)
            else:
                full_context = f"{system_prompt}\n\n{user_message}"
            
            try:
                # Generate with ALL tools available
                response = self.model.generate_content(
                    full_context,
                    tools=[self.tool_executor],
                    generation_config={
                        "temperature": 0.3,  # Slight creativity for reasoning
                        "top_p": 0.95,
                        "max_output_tokens": 2048
                    }
                )
                
                # Check if model wants to call a function
                function_calls = []
                text_response = None
                
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)
                        elif part.text:
                            text_response = part.text
                
                # If model called functions, execute them
                if function_calls:
                    logger.info(f"Model called {len(function_calls)} function(s)")
                    
                    for func_call in function_calls:
                        tool_name = func_call.name
                        arguments = dict(func_call.args)
                        
                        logger.info(f"Executing: {tool_name}({arguments})")
                        
                        # Execute the tool
                        result = await self._execute_tool(tool_name, arguments, state)
                        
                        # Store in conversation history
                        conversation_history.append({
                            "tool": tool_name,
                            "args": arguments,
                            "result": result
                        })
                        
                        # Update state
                        tool_result = ToolResult(
                            tool_type=self._get_tool_type(tool_name),
                            data=result,
                            success=True,
                            metadata={"tool_name": tool_name}
                        )
                        state["tool_results"].append(tool_result)
                    
                    # Continue loop - model might need more tools
                    continue
                
                # If model provided text response (no more function calls), we're done
                if text_response:
                    logger.info("Model provided final response - reasoning complete")
                    state["final_response"] = text_response
                    state["reasoning_trace"] = conversation_history
                    break
                
                # If no function calls AND no text, something's wrong
                logger.warning("Model provided neither function calls nor text response")
                break
                
            except Exception as e:
                logger.error(f"Error in reasoning loop: {e}")
                state["error"] = str(e)
                break
        
        return state
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Execute a tool and return results."""
        
        try:
            if tool_name == "search_hockey_knowledge":
                query = arguments.get("query")
                results = self.pinecone_node.retrieve(query, top_k=5)
                return {
                    "tool": "search_hockey_knowledge",
                    "results": results,
                    "summary": f"Found {len(results)} relevant hockey knowledge chunks"
                }
            
            elif tool_name == "get_team_roster":
                team = arguments.get("team")
                season = arguments.get("season", "current")
                
                # Try Parquet snapshot first
                roster_df = self.data_catalog.get_team_roster_from_snapshot(team)
                
                if not roster_df.empty:
                    roster_list = roster_df.to_dict('records')
                    return {
                        "tool": "get_team_roster",
                        "team": team,
                        "season": season,
                        "roster": roster_list,
                        "count": len(roster_list),
                        "source": "local_snapshot"
                    }
                else:
                    # Fallback to NHL API
                    roster_data = await self.roster_client.get_team_roster(team, season)
                    return {
                        "tool": "get_team_roster",
                        "team": team,
                        "season": season,
                        "roster": roster_data,
                        "count": len(roster_data),
                        "source": "nhl_api"
                    }
            
            elif tool_name == "search_player_info":
                player_name = arguments.get("player_name")
                results = self.data_catalog.search_player_in_rosters(player_name)
                
                return {
                    "tool": "search_player_info",
                    "query": player_name,
                    "results": results,
                    "found": len(results) > 0
                }
            
            elif tool_name == "get_live_game_data":
                team = arguments.get("team")
                date = arguments.get("date")
                game_id = arguments.get("game_id")
                
                game_data = await self.live_game_client.get_game_data(
                    team=team,
                    date=date,
                    game_id=game_id
                )
                
                return {
                    "tool": "get_live_game_data",
                    "data": game_data
                }
            
            elif tool_name == "query_game_data":
                query_desc = arguments.get("query_description")
                results = await self.parquet_node.analyze(query_desc)
                
                return {
                    "tool": "query_game_data",
                    "query": query_desc,
                    "results": results
                }
            
            elif tool_name == "calculate_hockey_metrics":
                metric_type = arguments.get("metric_type")
                return {
                    "tool": "calculate_hockey_metrics",
                    "metric_type": metric_type,
                    "note": "Calculation not yet implemented"
                }
            
            elif tool_name == "generate_visualization":
                chart_type = arguments.get("chart_type")
                return {
                    "tool": "generate_visualization",
                    "chart_type": chart_type,
                    "note": "Visualization not yet implemented"
                }
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return {"error": str(e), "tool": tool_name}
    
    def _get_tool_type(self, tool_name: str) -> ToolType:
        """Map tool name to ToolType enum."""
        mapping = {
            "search_hockey_knowledge": ToolType.RAG_SEARCH,
            "get_team_roster": ToolType.TEAM_ROSTER,
            "search_player_info": ToolType.TEAM_ROSTER,
            "get_live_game_data": ToolType.LIVE_GAME_DATA,
            "query_game_data": ToolType.PARQUET_QUERY,
            "calculate_hockey_metrics": ToolType.CALCULATE_METRICS,
            "generate_visualization": ToolType.VISUALIZATION
        }
        return mapping.get(tool_name, ToolType.RAG_SEARCH)


# Factory function for easy import
def get_orchestrator():
    """Get an instance of the best practices orchestrator."""
    return Qwen3BestPracticesOrchestrator()

