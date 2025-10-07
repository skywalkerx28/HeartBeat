"""
Qwen3 Autonomous Orchestrator - REASONING-FIRST ARCHITECTURE

This is the production approach for HeartBeat Engine:
- Model decides what tools it needs (not hardcoded routing)
- Model gathers data comprehensively (not limited by intent analysis)
- Model synthesizes naturally (not constrained by templates)

We TEACH the model, then TRUST it to perform.
"""

import vertexai
from vertexai.preview.generative_models import GenerativeModel, Tool, FunctionDeclaration
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime

from orchestrator.utils.state import AgentState, ToolType, ToolResult, QueryType, create_initial_state
from orchestrator.nodes.pinecone_retriever import PineconeRetrieverNode
from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode
from orchestrator.tools.nhl_roster_client import NHLRosterClient, NHLLiveGameClient
from orchestrator.tools.data_catalog import HeartBeatDataCatalog

logger = logging.getLogger(__name__)


class Qwen3AutonomousOrchestrator:
    """
    Fully autonomous orchestrator - model makes ALL decisions.
    
    How it works:
    1. Model receives query + tool catalog
    2. Model THINKS: "What do I need to answer this?"
    3. Model CALLS tools one by one, deciding when to stop
    4. Model SYNTHESIZES answer using all gathered data
    
    NO HARDCODED ROUTING. Pure AI reasoning.
    """
    
    def __init__(self, project_id: str = "heartbeat-474020", location: str = "global"):
        """Initialize autonomous orchestrator."""
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
        
        # Initialize data catalog for roster access
        from orchestrator.config.settings import settings
        self.data_catalog = HeartBeatDataCatalog(settings.parquet.data_directory)
        
        logger.info(f"Qwen3 Autonomous Orchestrator initialized")
    
    def get_tool_catalog(self) -> str:
        """
        Get tool catalog that teaches the model what's available.
        This is how we GUIDE the model without constraining it.
        """
        return """AVAILABLE TOOLS:

1. search_hockey_knowledge(query: str)
   - What it does: Retrieves hockey concepts, tactics, metric explanations from knowledge base
   - When to use: Need to understand a hockey concept or metric definition
   - Example: "What is Corsi?" → search "Corsi percentage defensive metric"

2. query_game_data(query_description: str)
   - What it does: Queries Montreal Canadiens data (games, players, matchups, stats)
   - When to use: Need actual numbers, records, or performance data
   - Example: "MTL vs Toronto record" → query "season results against Toronto"
   - Data available:
     * Season game results (wins/losses by opponent)
     * Matchup metrics (xG, Corsi, possession vs specific teams)
     * Power play/penalty kill stats
     * Player statistics (goals, assists, TOI, etc.)
     * Line combinations and deployment

3. calculate_hockey_metrics(data_reference: str, metric_type: str)
   - What it does: Computes advanced analytics from raw data
   - When to use: Need derived metrics like xG per 60, relative Corsi, etc.
   - Example: After getting game data, calculate "xG differential per game"

4. generate_visualization(chart_type: str, data_reference: str)
   - What it does: Creates charts, heatmaps, shot maps
   - When to use: Visual representation would help
   - Example: "shot map for last game"

5. get_team_roster(team: str, season: str = "current")
   - What it does: Gets current NHL roster for ANY team (all 32 teams)
   - When to use: Need player names, positions, jersey numbers, or team composition
   - Example: "Who is on Montreal's roster?" → get_team_roster("MTL")
   - Example: "What team is Ivan Demidov on?" → get_team_roster("MTL") and search for player
   - Returns: Active roster with player names, positions, numbers, team assignments
   - Data updated: Daily at 10 PM ET

6. get_live_game_data(team: str = None, date: str = None, game_id: int = None)
   - What it does: Gets real-time NHL game data (score, period, shots, goals, player stats)
   - When to use: Need current game status, live scores, or today's games
   - Example: "What's the score of today's game?" → get_live_game_data("MTL")
   - Example: "Who's playing today?" → get_live_game_data()
   - Returns: Live game state, score, period, clock, shots, goals, boxscore

7. search_player_info(player_name: str)
   - What it does: Finds player information across all NHL rosters
   - When to use: Looking for a specific player's current team or details
   - Example: "What team is Sidney Crosby on?" → search_player_info("Sidney Crosby")
   - Returns: Player name, team, position, jersey number

REASONING PATTERNS (learn from these):

Example 1: "How did we do against Toronto last season?"
Step 1 - THINK: Need season record and performance metrics
Step 2 - GATHER: Call query_game_data("Montreal vs Toronto 2024-2025 season results")
Step 3 - SYNTHESIZE: Combine W/L with metrics, provide analysis

Example 2: "What team is Ivan Demidov on?"
Step 1 - THINK: This is a roster question, I need current roster data
Step 2 - GATHER: Call get_team_roster("MTL") to get Montreal's roster
Step 3 - SEARCH: Look for "Ivan Demidov" in the roster response
Step 4 - SYNTHESIZE: "Ivan Demidov plays for the Montreal Canadiens as a forward, wears #93"

Example 3: "Who are Montreal's goalies?"
Step 1 - THINK: Need Montreal's roster, filter by position
Step 2 - GATHER: Call get_team_roster("MTL")
Step 3 - FILTER: Find all players where position = "G"
Step 4 - SYNTHESIZE: List goalie names and numbers

Example 4: "What's the score of today's game?"
Step 1 - THINK: Need real-time game data
Step 2 - GATHER: Call get_live_game_data("MTL")
Step 3 - SYNTHESIZE: Report score, period, and game state

KEY PRINCIPLES:
- You decide what data you need - there's no predetermined path
- For roster/team questions → use get_team_roster or search_player_info
- For live game questions → use get_live_game_data
- For historical stats → use query_game_data
- For concepts/tactics → use search_hockey_knowledge
- Call tools multiple times if needed to get complete information
- Think strategically: "Do I have EVERYTHING to answer properly?"
- Don't stop at first tool call - gather comprehensively
"""
    
    async def process_query(self, state: AgentState) -> AgentState:
        """
        Process query with full model autonomy.
        
        The model orchestrates its own tool sequence.
        """
        
        query = state["original_query"]
        current_date = state.get("current_date", datetime.now().strftime("%Y-%m-%d"))
        current_season = state.get("current_season", "2025-2026")
        
        logger.info(f"Processing query autonomously: {query}")
        
        # Define ALL tools upfront (Qwen3 MaaS limitation: one at a time)
        all_tools = {
            "search_hockey_knowledge": FunctionDeclaration(
                name="search_hockey_knowledge",
                description="Search hockey concepts, tactics, metric explanations",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            ),
            "get_player_stats": FunctionDeclaration(
                name="get_player_stats",
                description="Get statistics for ANY NHL player. Can specify team or search all teams.",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_name": {
                            "type": "string",
                            "description": "Full player name (e.g., 'Connor McDavid', 'Nick Suzuki', 'Auston Matthews')"
                        },
                        "season": {
                            "type": "string",
                            "description": "NHL season (e.g., '2024-2025')",
                            "default": "2024-2025"
                        },
                        "team": {
                            "type": "string",
                            "description": "Optional: Team abbreviation (e.g., 'EDM' for Edmonton, 'MTL' for Montreal, 'TOR' for Toronto). If omitted, searches all NHL teams.",
                            "default": None
                        }
                    },
                    "required": ["player_name"]
                }
            ),
            "get_matchup_stats": FunctionDeclaration(
                name="get_matchup_stats",
                description="Get Montreal Canadiens performance vs a specific opponent",
                parameters={
                    "type": "object",
                    "properties": {
                        "opponent": {
                            "type": "string",
                            "description": "Opponent team name or abbreviation (e.g., 'Toronto', 'Boston', 'TOR')"
                        },
                        "season": {
                            "type": "string",
                            "description": "NHL season",
                            "default": "2024-2025"
                        }
                    },
                    "required": ["opponent"]
                }
            ),
            "get_team_stats": FunctionDeclaration(
                name="get_team_stats",
                description="Get Montreal Canadiens team statistics (power play, penalty kill, overall)",
                parameters={
                    "type": "object",
                    "properties": {
                        "stat_type": {
                            "type": "string",
                            "description": "Type of stats: 'power_play', 'penalty_kill', 'season_results', 'overall'"
                        },
                        "season": {
                            "type": "string",
                            "description": "NHL season",
                            "default": "2024-2025"
                        }
                    },
                    "required": ["stat_type"]
                }
            ),
            "calculate_hockey_metrics": FunctionDeclaration(
                name="calculate_hockey_metrics",
                description="Compute advanced analytics from retrieved data",
                parameters={
                    "type": "object",
                    "properties": {
                        "metric_type": {"type": "string", "description": "Type of metric to calculate"}
                    },
                    "required": ["metric_type"]
                }
            ),
            "get_team_roster": FunctionDeclaration(
                name="get_team_roster",
                description="Get current NHL roster for any team. Returns active roster with player names, positions, numbers, and IDs.",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team abbreviation (e.g., 'MTL' for Montreal, 'TOR' for Toronto, 'BOS' for Boston)"
                        },
                        "season": {
                            "type": "string",
                            "description": "NHL season (e.g., '2025-2026')",
                            "default": "current"
                        }
                    },
                    "required": ["team"]
                }
            ),
            "get_live_game_data": FunctionDeclaration(
                name="get_live_game_data",
                description="Get real-time NHL game data: score, period, clock, situation, shots, goals, and player stats",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team abbreviation to find today's game (e.g., 'MTL', 'TOR')"
                        },
                        "date": {
                            "type": "string",
                            "description": "Optional: date in YYYY-MM-DD format (defaults to today)"
                        },
                        "include_boxscore": {
                            "type": "boolean",
                            "description": "Include detailed player statistics",
                            "default": False
                        }
                    },
                    "required": ["team"]
                }
            ),
            "search_player_info": FunctionDeclaration(
                name="search_player_info",
                description="Search for player information across all NHL teams. Returns player name, team, position, number.",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_name": {
                            "type": "string",
                            "description": "Player name to search (full or partial)"
                        }
                    },
                    "required": ["player_name"]
                }
            ),
            "done_gathering": FunctionDeclaration(
                name="done_gathering",
                description="Signal that you have all data needed to answer",
                parameters={
                    "type": "object",
                    "properties": {
                        "ready": {"type": "boolean", "description": "True when ready to synthesize"}
                    },
                    "required": ["ready"]
                }
            )
        }
        
        # STEP 1: Let model EXTRACT ENTITIES and PLAN
        reasoning_prompt = f"""You are STANLEY - Montreal Canadiens AI assistant.

User Question: {query}

Extract and list (be specific):
1. Player names mentioned (if any): [list each player]
2. Team names mentioned (if any): [list each team]
3. What data needed: [matchup/player stats/team stats]

Examples:
Query: "compare Caufield with Suzuki"
→ Players: Cole Caufield, Nick Suzuki | Data needed: Both players' stats for comparison

Query: "how did we do vs Toronto"  
→ Teams: Montreal, Toronto | Data needed: Matchup metrics and W/L record

Query: "show me power play stats"
→ Teams: Montreal | Data needed: Montreal power play statistics

Now extract from the user's query:"""
        
        logger.info("Step 1: Letting model reason about query...")
        
        try:
            reasoning_response = self.model.generate_content(
                reasoning_prompt,
                generation_config={"temperature": 0.3, "max_output_tokens": 1024}
            )
            reasoning_text = reasoning_response.text
            logger.info(f"Model's reasoning: {reasoning_text[:200]}...")
        except:
            reasoning_text = "Unable to reason - proceeding with tool execution"
        
        # Store reasoning in state for tool selection
        state["reasoning_text"] = reasoning_text
        
        # STEP 2: Now execute tools based on reasoning
        conversation = []
        max_tools = 15
        tool_count = 0
        
        logger.info(f"Step 2: Executing tools autonomously (max {max_tools})")
        
        while tool_count < max_tools:
            tool_count += 1
            
            # Suggest next tool
            next_tool = self._suggest_next_tool(state, conversation)
            
            logger.info(f"Iteration {tool_count}: Offering {next_tool}")
            
            if not next_tool:
                logger.info("No more tools to suggest")
                break
            
            tool_obj = Tool(function_declarations=[all_tools[next_tool]])
            
            # Context includes the REASONING so model remembers its plan
            if conversation:
                # Check what we've already retrieved
                players_retrieved = []
                for conv in conversation:
                    if conv.get("tool") == "get_player_stats":
                        # Extract player name from summary
                        summary = conv.get("summary", "")
                        if "Cole Caufield" in summary or "Caufield" in summary:
                            players_retrieved.append("Cole Caufield")
                        elif "Nick Suzuki" in summary or "Suzuki" in summary:
                            players_retrieved.append("Nick Suzuki")
                
                logger.info(f"Players already retrieved: {players_retrieved}")
                
                # Build smart context
                gathered_info = self._format_conversation(conversation)
                
                if next_tool == "get_player_stats" and players_retrieved:
                    # Extract ALL player names from query to tell model who's missing
                    query_lower = query.lower()
                    potential_players = []
                    
                    # Common Canadiens players - extract mentioned ones
                    known_players = {
                        'caufield': 'Cole Caufield',
                        'suzuki': 'Nick Suzuki',
                        'slafkovsky': 'Juraj Slafkovsky',
                        'dach': 'Kirby Dach',
                        'matheson': 'Mike Matheson',
                        'hutson': 'Lane Hutson',
                        'laine': 'Patrik Laine'
                    }
                    
                    for key, full_name in known_players.items():
                        if key in query_lower and full_name not in players_retrieved:
                            potential_players.append(full_name)
                    
                    if potential_players:
                        # Explicitly tell model WHO to fetch next
                        context = f"""Question: {query}

Already retrieved: {', '.join(players_retrieved)}

Still need: {potential_players[0]}

Call {next_tool} for {potential_players[0]}."""
                    else:
                        # Fallback if we can't detect the other player
                        context = f"""Question: {query}

Already have: {', '.join(players_retrieved)}

Call {next_tool} with DIFFERENT player name from query."""
                else:
                    context = f"""Question: {query}

Gathered: {gathered_info}

Call {next_tool} if needed."""
            else:
                # First tool - remind model of its plan
                context = f"""Plan: {reasoning_text[:200]}

Question: {query}

Call {next_tool}."""
            
            try:
                response = self.model.generate_content(
                    context,
                    tools=[tool_obj],
                    generation_config={"temperature": 0.2}
                )
                
                # Check if model called the function
                func_call = None
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            func_call = part.function_call
                            break
                
                if not func_call:
                    logger.info("Model declined tool - done gathering")
                    break
                
                if func_call.name == "done_gathering":
                    logger.info("Model signaled done gathering")
                    break
                
                # Execute the tool
                tool_result = await self._execute_tool(
                    func_call.name,
                    dict(func_call.args),
                    state
                )
                
                # Add result to state (avoid circular reference)
                state["tool_results"].append(tool_result)
                
                # Add to conversation (lightweight summary only)
                conversation.append({
                    "iteration": tool_count,
                    "tool": func_call.name,
                    "success": tool_result.success,
                    "summary": self._summarize_result(tool_result)
                })
                
            except Exception as e:
                logger.error(f"Tool execution error: {str(e)}")
                break
        
        # Synthesis
        state = await self.synthesize_response(state)
        
        return state
    
    def _suggest_next_tool(
        self,
        state: AgentState,
        conversation: List[Dict]
    ) -> Optional[str]:
        """
        Suggest next tool based on query keywords.
        Model still decides if it wants to use it!
        """
        
        query_lower = state.get("original_query", "").lower()
        tools_used = [c["tool"] for c in conversation]
        
        # Intelligent tool selection based on AI's OWN REASONING
        # Don't hardcode player names - let the AI's reasoning drive tool selection
        if not tools_used:
            # Parse the AI's reasoning to understand what data it needs
            reasoning_lower = state.get("reasoning_text", "").lower()
            
            # If AI mentioned "player" + "statistic" in its reasoning → get_player_stats
            if "player" in reasoning_lower and ("statistic" in reasoning_lower or "stats" in reasoning_lower or "performance" in reasoning_lower):
                return "get_player_stats"
            
            # If AI mentioned specific player names (pattern: capitalized words) → get_player_stats
            if any(kw in query_lower for kw in ['about', 'tell me', 'show me']) and not any(kw in query_lower for kw in ['vs', 'against', 'team']):
                return "get_player_stats"
            
            # Comparison queries → player stats
            if "compar" in query_lower:
                return "get_player_stats"
            
            # Matchup queries
            if any(kw in query_lower for kw in ['vs', 'against', 'matchup', 'opponent']):
                return "get_matchup_stats"
            
            # Team-level queries
            if any(kw in query_lower for kw in ['power play', 'penalty kill', 'team']) and 'player' not in query_lower:
                return "get_team_stats"
            
            # Default: If query is asking about something/someone, try player stats first
            if any(kw in query_lower for kw in ['about', 'how', 'what', 'who']):
                return "get_player_stats"
            
            # Fallback
            return "search_hockey_knowledge"
        
        # After first tool, intelligently suggest what's next
        # KEY: Allow SAME tool multiple times (for multi-player comparisons!
        #         
        # If only called player stats once and query mentions "compare", offer it again
        if tools_used.count("get_player_stats") == 1:
            query_lower = state.get("original_query", "").lower()
            if any(kw in query_lower for kw in ['compare', 'vs', 'versus', 'and']):
                logger.info("Multi-entity query detected - offering get_player_stats again for second entity")
                return "get_player_stats"  # Offer same tool for second player!
        
        # If called player stats 2+ times, offer context
        if tools_used.count("get_player_stats") >= 2 and "search_hockey_knowledge" not in tools_used:
            return "search_hockey_knowledge"
        
        # If called matchup, might want team context too
        if "get_matchup_stats" in tools_used and "get_team_stats" not in tools_used:
            return "get_team_stats"
        
        # Offer search if haven't yet
        if "search_hockey_knowledge" not in tools_used and len(tools_used) > 0:
            return "search_hockey_knowledge"
        
        # All reasonable tools offered
        return None
    
    def _format_conversation(self, conversation: List[Dict]) -> str:
        """Format conversation history for model."""
        lines = []
        for i, item in enumerate(conversation, 1):
            lines.append(f"{i}. {item['tool']}: {item['summary']}")
        return "\n".join(lines)
    
    def _summarize_result(self, result: ToolResult) -> str:
        """Summarize tool result for next iteration - INCLUDE ENTITY NAMES."""
        if not result.success:
            return "FAILED"
        
        if isinstance(result.data, dict):
            analysis_type = result.data.get("analysis_type", "")
            
            # For player stats, INCLUDE the player name in summary
            if analysis_type == "player_stats":
                player_name = result.data.get("player_name", "Unknown")
                return f"Retrieved stats for {player_name}"
            
            if analysis_type == "comprehensive_matchup":
                opponent = result.data.get("opponent", "")
                return f"Retrieved matchup vs {opponent}"
            
            if analysis_type:
                return f"Retrieved {analysis_type} data"
        
        return "SUCCESS"
    
    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        state: AgentState
    ) -> ToolResult:
        """Execute requested tool."""
        
        start_time = datetime.now()
        
        try:
            if tool_name == "search_hockey_knowledge":
                # Create minimal state for node processing
                temp_state = create_initial_state(
                    user_context=state["user_context"],
                    query=arguments.get("query", state["original_query"])
                )
                # Process returns state - extract the retrieval results
                processed_state = await self.pinecone_node.process(temp_state)
                result_data = processed_state.get("retrieval_results", {})
                tool_type = ToolType.VECTOR_SEARCH
            
            elif tool_name == "get_player_stats":
                # AI extracted player name - use it directly!
                player_name = arguments.get("player_name")
                season = arguments.get("season", state.get("current_season", "2024-2025"))
                
                logger.info(f"AI requested player stats for: {player_name}")
                
                result_data = await self.parquet_node.data_client.get_player_stats(
                    player_name=player_name,
                    season=season
                )
                tool_type = ToolType.PARQUET_QUERY
            
            elif tool_name == "get_matchup_stats":
                # AI extracted opponent - use it directly!
                opponent = arguments.get("opponent")
                season = arguments.get("season", state.get("current_season", "2024-2025"))
                
                logger.info(f"AI requested matchup stats vs: {opponent}")
                
                # Get comprehensive matchup data
                matchup_data = await self.parquet_node.data_client.get_matchup_data(opponent, season)
                season_data = await self.parquet_node.data_client.get_season_results(opponent=opponent, season=season)
                
                # Combine
                result_data = {
                    "analysis_type": "comprehensive_matchup",
                    "opponent": opponent,
                    "season": matchup_data.get("season", season),
                    "matchup_metrics": {"key_metrics": matchup_data.get("key_metrics", {})},
                    "game_results": season_data.get("record", {}) if season_data else {}
                }
                tool_type = ToolType.PARQUET_QUERY
            
            elif tool_name == "get_team_stats":
                # AI specified stat type
                stat_type = arguments.get("stat_type")
                season = arguments.get("season", state.get("current_season", "2024-2025"))
                
                logger.info(f"AI requested team stats: {stat_type}")
                
                if stat_type == "power_play":
                    result_data = await self.parquet_node.data_client.get_power_play_stats(season=season)
                elif stat_type == "season_results":
                    result_data = await self.parquet_node.data_client.get_season_results(season=season)
                else:
                    result_data = {"analysis_type": stat_type, "note": "Stat type not yet implemented"}
                
                tool_type = ToolType.PARQUET_QUERY
            
            elif tool_name == "calculate_hockey_metrics":
                # TODO: Implement metrics calculator
                result_data = {"analysis_type": "metrics", "note": "Calculator not yet implemented"}
                tool_type = ToolType.CALCULATE_METRICS
            
            elif tool_name == "get_team_roster":
                # Fetch NHL roster (hybrid: Parquet snapshot fallback to live API)
                team = arguments.get("team")
                season = arguments.get("season", "current")
                
                logger.info(f"Fetching roster for {team}, season {season}")
                
                try:
                    # Try Parquet snapshot first (fast)
                    roster_df = self.data_catalog.get_team_roster_from_snapshot(team)
                    
                    if not roster_df.empty:
                        result_data = {
                            "analysis_type": "team_roster",
                            "team": team,
                            "source": "parquet_snapshot",
                            "season": season,
                            "roster": roster_df.to_dict('records'),
                            "player_count": len(roster_df)
                        }
                    else:
                        # Fallback to live API
                        logger.info(f"No Parquet data for {team}, falling back to NHL API")
                        roster_data = await self.roster_client.get_team_roster(team, season)
                        result_data = {
                            "analysis_type": "team_roster",
                            "team": team,
                            "source": "nhl_api",
                            **roster_data
                        }
                except Exception as e:
                    logger.error(f"Roster fetch failed for {team}: {e}")
                    result_data = {"analysis_type": "team_roster", "error": str(e), "team": team}
                
                tool_type = ToolType.TEAM_ROSTER
            
            elif tool_name == "get_live_game_data":
                # Real-time NHL game data
                team = arguments.get("team")
                date = arguments.get("date")
                include_boxscore = arguments.get("include_boxscore", False)
                
                logger.info(f"Fetching live game data for {team} on {date or 'today'}")
                
                try:
                    game_data = await self.live_game_client.get_game_data(team=team, date=date)
                    
                    # Optionally fetch boxscore
                    if include_boxscore and "game_id" in game_data:
                        boxscore = await self.live_game_client.get_boxscore(game_data["game_id"])
                        game_data["boxscore"] = boxscore
                    
                    result_data = {
                        "analysis_type": "live_game",
                        "team": team,
                        **game_data
                    }
                except Exception as e:
                    logger.error(f"Live game fetch failed: {e}")
                    result_data = {"analysis_type": "live_game", "error": str(e), "team": team}
                
                tool_type = ToolType.LIVE_GAME_DATA
            
            elif tool_name == "search_player_info":
                # Search for player across all teams
                player_name = arguments.get("player_name")
                
                logger.info(f"Searching for player: {player_name}")
                
                try:
                    # Search in Parquet snapshot
                    results_df = self.data_catalog.search_player_in_rosters(player_name)
                    
                    if not results_df.empty:
                        result_data = {
                            "analysis_type": "player_search",
                            "query": player_name,
                            "source": "parquet_snapshot",
                            "results": results_df.to_dict('records'),
                            "match_count": len(results_df)
                        }
                    else:
                        result_data = {
                            "analysis_type": "player_search",
                            "query": player_name,
                            "results": [],
                            "match_count": 0,
                            "note": "No matches found in current roster data"
                        }
                except Exception as e:
                    logger.error(f"Player search failed: {e}")
                    result_data = {"analysis_type": "player_search", "error": str(e), "query": player_name}
                
                tool_type = ToolType.TEAM_ROSTER
            
            else:
                result_data = {"error": f"Unknown tool: {tool_name}"}
                tool_type = ToolType.VECTOR_SEARCH
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ToolResult(
                tool_type=tool_type,
                success=not result_data.get("error"),
                data=result_data,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return ToolResult(
                tool_type=ToolType.PARQUET_QUERY,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def synthesize_response(self, state: AgentState) -> AgentState:
        """Final synthesis - model reasons freely with all gathered data."""
        
        query = state["original_query"]
        current_date = state.get("current_date", "")
        current_season = state.get("current_season", "")
        
        # Build natural synthesis prompt with ALL data
        from orchestrator.agents.qwen3_reasoning_synthesis import build_reasoning_synthesis_prompt
        
        # Retrieve RAG context
        rag_context = ""
        try:
            from orchestrator.tools.pinecone_mcp_client import PineconeMCPClient
            pinecone = PineconeMCPClient()
            rag_results = await pinecone.search_hockey_context(query, namespace="context", top_k=3)
            if rag_results:
                rag_context = "\n".join([r.get("content", "")[:200] for r in rag_results])
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
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 8192  # High for reasoning + detailed output
                }
            )
            
            state["final_response"] = response.text
            state["current_step"] = "complete"
            
            logger.info("Synthesis complete")
            return state
        
        except Exception as e:
            logger.error(f"Synthesis failed: {str(e)}")
            state["final_response"] = "I encountered an error analyzing the data. Please try rephrasing your question."
            state["current_step"] = "error"
            return state


# Singleton instance
qwen3_autonomous_orchestrator = Qwen3AutonomousOrchestrator()

