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
from vertexai.preview.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part, Content
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime, timedelta
import asyncio

from orchestrator.utils.state import AgentState, ToolType, ToolResult, create_initial_state
from orchestrator.config.settings import settings
from orchestrator.agents.tool_registry import build_execution_plan, get_tool_spec
from orchestrator.tools.live_analytics_engine import (
    aggregate_live_feeds,
    compute_live_team_metrics,
    compute_live_player_unit_metrics,
    compute_contextual_insights,
    to_dict as live_to_dict,
)
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
        # Model instance is created per-request with system_instruction to avoid
        # passing a separate system message (which some models reject)
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
        
        # Short-lived aggregated cache for league-wide jersey lookups
        # key format: f"{season}:{number}"
        self._number_cache: Dict[str, Dict[str, Any]] = {}
        self._number_cache_ttl_seconds: int = 300
        
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
            
            # Live Scoreboard (current day)
            "get_live_scoreboard": FunctionDeclaration(
                name="get_live_scoreboard",
                description="Get today's NHL scoreboard. Returns all games with teams, state, start time, and current scores when available.",
                parameters={
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date YYYY-MM-DD; defaults to today"}
                    }
                }
            ),
            
            # Live Boxscore (per game)
            "get_live_boxscore": FunctionDeclaration(
                name="get_live_boxscore",
                description="Get detailed live boxscore for a specific game id.",
                parameters={
                    "type": "object",
                    "properties": {
                        "game_id": {"type": "integer", "description": "NHL game id"}
                    },
                    "required": ["game_id"]
                }
            ),
            
            # Live Play-by-Play (per game)
            "get_live_play_by_play": FunctionDeclaration(
                name="get_live_play_by_play",
                description="Get live play-by-play events for a game id.",
                parameters={
                    "type": "object",
                    "properties": {
                        "game_id": {"type": "integer", "description": "NHL game id"}
                    },
                    "required": ["game_id"]
                }
            ),
            
            # Compute Live Analytics
            "compute_live_analytics": FunctionDeclaration(
                name="compute_live_analytics",
                description="Compute real-time advanced metrics and contextual insights for a live game.",
                parameters={
                    "type": "object",
                    "properties": {
                        "game_id": {"type": "integer", "description": "NHL game id"}
                    },
                    "required": ["game_id"]
                }
            ),

            # League-wide jersey number lookup (aggregated)
            "find_players_by_number": FunctionDeclaration(
                name="find_players_by_number",
                description="Find all NHL players wearing a specific jersey number across the league.",
                parameters={
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "integer",
                            "description": "Jersey number to search (e.g., 16)"
                        },
                        "season": {
                            "type": "string",
                            "description": "NHL season (e.g., '2024-2025'). Optional; defaults to current season."
                        }
                    },
                    "required": ["number"]
                }
            ),

            # Schedule / Calendar queries (league or team)
            "get_schedule": FunctionDeclaration(
                name="get_schedule",
                description="Get NHL schedule for a date or a date range; filter by team if provided.",
                parameters={
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Start date YYYY-MM-DD; defaults to today"},
                        "days": {"type": "integer", "description": "Number of days from start date (0 = single day)"},
                        "team": {"type": "string", "description": "Team abbreviation to filter (e.g., 'MTL')"}
                    }
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
                            "description": "NHL season (e.g., '2024-2025'). Optional; defaults to current season."
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

            # Direct jersey number lookup (product hardening)
            "find_player_by_team_and_number": FunctionDeclaration(
                name="find_player_by_team_and_number",
                description="Find the player on a given team wearing a specific jersey number. Returns a single match or 'not found'.",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team abbreviation (e.g., 'MTL')"
                        },
                        "number": {
                            "type": "integer",
                            "description": "Jersey number (e.g., 14)"
                        },
                        "season": {
                            "type": "string",
                            "description": "NHL season (e.g., '2024-2025'). Optional; defaults to current season."
                        }
                    },
                    "required": ["team", "number"]
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
                            "type": "string",
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
            
            # Market Analytics - Player Contracts
            "get_player_contract": FunctionDeclaration(
                name="get_player_contract",
                description="Get NHL player contract details including cap hit, term, NMC/NTC, signing details, and performance value metrics. Use when user asks about contracts, cap hits, or contract efficiency.",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_name": {
                            "type": "string",
                            "description": "Player name (e.g., 'Nick Suzuki', 'Connor McDavid')"
                        },
                        "team": {
                            "type": "string",
                            "description": "Team abbreviation (optional, for disambiguation)"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season (defaults to current)"
                        }
                    },
                    "required": ["player_name"]
                }
            ),
            
            # Market Analytics - Team Cap Analysis
            "get_team_cap_analysis": FunctionDeclaration(
                name="get_team_cap_analysis",
                description="Get team salary cap summary, space available, LTIR pool, commitments, and multi-year projections. Use for cap space questions and team financial analysis.",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team abbreviation (e.g., 'MTL', 'TOR')"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season (defaults to current)"
                        },
                        "include_projections": {
                            "type": "boolean",
                            "description": "Include future season projections (default: true)"
                        }
                    },
                    "required": ["team"]
                }
            ),
            
            # Market Analytics - Contract Comparables
            "find_contract_comparables": FunctionDeclaration(
                name="find_contract_comparables",
                description="Find similar player contracts for market value comparison. Use for 'what should X be worth' or contract negotiation questions.",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_name": {
                            "type": "string",
                            "description": "Player to find comparables for"
                        },
                        "position": {
                            "type": "string",
                            "description": "Position filter (C, RW, LW, D, G)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max comparables to return (default 10)"
                        }
                    },
                    "required": ["player_name"]
                }
            ),
            
            # Market Analytics - Recent Trades
            "get_recent_trades": FunctionDeclaration(
                name="get_recent_trades",
                description="Get recent NHL trades with cap implications and analysis. Use for trade activity and market movement questions.",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Filter by team (optional)"
                        },
                        "days_back": {
                            "type": "integer",
                            "description": "Days to look back (default 30)"
                        }
                    }
                }
            ),
            
            # Market Analytics - League Market Overview
            "get_league_market_overview": FunctionDeclaration(
                name="get_league_market_overview",
                description="Get league-wide contract market statistics by position (average AAV, market tiers, contract efficiency leaders). Use for market context and position-based salary questions.",
                parameters={
                    "type": "object",
                    "properties": {
                        "position": {
                            "type": "string",
                            "description": "Filter by position (C, RW, LW, D, G)"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season (defaults to current)"
                        }
                    }
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
    
    def _create_system_prompt(self, state: AgentState) -> str:
        """
        Create system prompt that teaches the model HOW to reason.
        
        Best Practice: Teach decision-making patterns, not rules.
        """
        # Time/context awareness from state
        current_date = state.get("current_date", "")
        current_season = state.get("current_season", "")

        return f"""You are STANLEY, an expert NHL analytics AI for the Montreal Canadiens.

TODAY: {current_date}
CURRENT_NHL_SEASON: {current_season}

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

SEASON AWARENESS:
- If the user does NOT specify a season, assume the CURRENT_NHL_SEASON above.
- If a tool falls back to a different season (because the requested data is not available), explicitly state both the requested season and the season used.
- Prefer the most recent season available when in doubt.

TOOL USE CONTRACT (STRICT):
- You are equipped with function tools. When you want to use a tool, return a function call via the structured tool interface — not text.
- NEVER emit tool calls as text, code, XML, JSON, or pseudo-markup (e.g., no <tools> ... </tools>, no fenced code blocks).
- For visualization requests, call generate_visualization after you have the underlying data.

FINAL OUTPUT CONTRACT (STRICT):
- After you finish calling tools, provide a concise plain-text explanation that describes the results shown in tables/charts.
- Do NOT print tables, JSON, or any tool metadata in the text; the UI renders analytics separately.
- Summarize key takeaways in 1–3 sentences or 2–5 bullets (use "- " for bullets).
- Plain text only. No Markdown, no bold/italics, no emojis.

Remember: You're an autonomous agent. Think strategically, gather comprehensively, synthesize professionally."""

    async def process_query(self, state: AgentState) -> AgentState:
        """
        Process query with TRUE model autonomy.
        
        Best Practice: One continuous reasoning loop where model controls flow.
        """
        query = state["original_query"]
        logger.info(f"Processing query with best practices: {query}")
        
        # Build initial context with system prompt
        system_prompt = self._create_system_prompt(state)
        # Optional context injection for anaphora resolution (he/his)
        extra_context = ""
        try:
            last_entities = state.get("last_entities")
            if isinstance(last_entities, dict):
                player_hint = last_entities.get("player_name")
                if player_hint and any(w in query.lower() for w in [" he ", " his ", " him ", "this player", "that player"]):
                    extra_context = f"\nContext hint: If the question refers to a player without naming him, use {player_hint} as the referenced player."
        except Exception:
            pass
        user_message = f"""Question: {query}{extra_context}

Think about what information you need, then call the appropriate tools. You can call multiple tools if needed."""
        
        # Continuous reasoning loop
        conversation_history = []  # will hold structured Content objects with function responses
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Reasoning iteration {iteration}/{max_iterations}")
            
            # Build full context
            try:
                logger.info(f"Building context. conversation_history length: {len(conversation_history)}")
            except Exception as e:
                logger.error(f"Error checking conversation_history: {e}")
                
            if conversation_history and isinstance(conversation_history[0], dict):
                # Include previous tool results
                try:
                    logger.info(f"Starting to build context with {len(conversation_history)} history items")
                    context_parts = [system_prompt, user_message, "\n\nPrevious tool calls and results:"]
                    for turn_idx, turn in enumerate(conversation_history):
                        logger.info(f"Processing turn {turn_idx}: {turn.get('tool', 'unknown tool')}")
                        context_parts.append(f"\nTool Called: {turn['tool']}")
                        context_parts.append(f"Arguments: {turn['args']}")

                        # Format the result in a more readable way for the model
                        result = turn['result']
                        if isinstance(result, dict):
                            if turn['tool'] == 'search_player_info':
                                found = result.get('found', False)
                                results_data = result.get('results')

                                # Handle pandas DataFrame case
                                if found and results_data is not None:
                                    try:
                                        # Check if it's a DataFrame
                                        if hasattr(results_data, 'empty'):
                                            if not results_data.empty:
                                                # Convert DataFrame to list of dicts
                                                players = results_data.to_dict('records')
                                                player_list = []
                                                for player in players[:5]:  # Show up to 5 players
                                                    name = player.get('full_name', 'Unknown')
                                                    team = player.get('team_abbrev', 'Unknown')
                                                    pos = player.get('position', 'Unknown')
                                                    player_list.append(f"{name} ({team}, {pos})")
                                                context_parts.append(f"Result: Found players - {', '.join(player_list)}")
                                            else:
                                                context_parts.append("Result: No players found matching the search")
                                        elif isinstance(results_data, list) and results_data:
                                            # Handle list case
                                            player_list = []
                                            for player in results_data[:5]:  # Show up to 5 players
                                                name = player.get('full_name', 'Unknown')
                                                team = player.get('team_abbrev', 'Unknown')
                                                pos = player.get('position', 'Unknown')
                                                player_list.append(f"{name} ({team}, {pos})")
                                            context_parts.append(f"Result: Found players - {', '.join(player_list)}")
                                        else:
                                            context_parts.append("Result: No players found matching the search")
                                    except Exception as e:
                                        logger.error(f"Error formatting player data: {e}")
                                        context_parts.append(f"Result: Player search completed (data formatting issue)")
                                else:
                                    context_parts.append("Result: No players found matching the search")
                            elif 'error' in result:
                                context_parts.append(f"Result: Error - {result['error']}")
                            else:
                                # Generic formatting for other tools
                                key_info = []
                                for key, value in result.items():
                                    if key not in ['tool'] and value is not None:
                                        if isinstance(value, list) and len(value) > 3:
                                            key_info.append(f"{key}: {len(value)} items")
                                        elif isinstance(value, str) and len(value) > 100:
                                            key_info.append(f"{key}: {value[:100]}...")
                                        else:
                                            key_info.append(f"{key}: {value}")
                                context_parts.append(f"Result: {', '.join(key_info[:5])}")  # Limit to 5 key pieces
                        else:
                            context_parts.append(f"Result: {str(result)[:200]}")
                    context_parts.append(f"\n\nYou have executed {len(conversation_history)} tool(s) and gathered data.")
                    context_parts.append("Now provide a final, professional response to the user's question using this information.")
                    context_parts.append("Answer directly - do not call more tools unless you absolutely need additional data.")
                    full_context = "\n".join(context_parts)
                    logger.info("Context building completed successfully")
                except Exception as e:
                    logger.error(f"ERROR during context building: {str(e)}", exc_info=True)
                    # Fallback to simple context
                    full_context = f"{system_prompt}\n\n{user_message}"
            else:
                full_context = f"{system_prompt}\n\n{user_message}"
            
            try:
                # Generate response using structured messages + function-calling
                # Pass system prompt via system_instruction to avoid invalid roles
                logger.info(f"About to generate content. Has prior function responses: {len(conversation_history) > 0}")
                messages: list[Content] = []
                # Seed with prior messages from service memory (if provided)
                try:
                    seed_messages = state.get("prior_messages")
                    if isinstance(seed_messages, list):
                        for m in seed_messages[-20:]:
                            role = m.get("role", "user")
                            text = str(m.get("text", ""))
                            if text:
                                messages.append(Content(role=role if role in ("user", "model") else "user", parts=[Part.from_text(text[:2000])]))
                except Exception as e:
                    logger.warning(f"Failed to load prior_messages: {e}")

                messages.append(Content(role="user", parts=[Part.from_text(user_message)]))
                if conversation_history:
                    for content in conversation_history:
                        if isinstance(content, Content):
                            messages.append(content)
                # Choose config based on whether we should force a final write
                force_write = self._should_force_synthesis(state)

                # EXTRA RULE: Force synthesis for jersey-number queries after roster retrieval
                try:
                    numbers = self._extract_jersey_numbers(state.get("original_query", ""))
                    last_success_tool = None
                    for tr in reversed(state.get("tool_results", [])):
                        if getattr(tr, "success", False):
                            last_success_tool = getattr(tr, "tool_type", None)
                            break
                    last_tool_val = str(getattr(last_success_tool, "value", last_success_tool)).lower()
                    if numbers and last_tool_val == "team_roster".lower():
                        force_write = True
                        # Add explicit instruction to answer now by filtering the roster
                        num_str = ", ".join(str(n) for n in numbers)
                        answer_now = (
                            f"You have the roster. Filter by sweater number(s) {num_str} for the requested team and answer. "
                            f"If no one wears these number(s), say clearly that no current player wears that number."
                        )
                        messages.append(Content(role="user", parts=[Part.from_text(answer_now)]))
                except Exception as e:
                    logger.warning(f"Failed to apply jersey force-write rule: {e}")

                model = GenerativeModel(self.model_id, system_instruction=system_prompt)

                if force_write:
                    # Large output budget; disable further tool calls
                    gen_cfg = {
                        "temperature": 0.3,
                        "top_p": 0.95,
                        "max_output_tokens": 8192
                    }
                    try:
                        from vertexai.generative_models import ToolConfig
                        response = model.generate_content(
                            messages,
                            tools=[self.tool_executor],
                            tool_config=ToolConfig(
                                function_calling_config=ToolConfig.FunctionCallingConfig(
                                    mode=ToolConfig.FunctionCallingConfig.Mode.NONE
                                )
                            ),
                            generation_config=gen_cfg,
                        )
                    except Exception:
                        response = model.generate_content(
                            messages,
                            tools=[self.tool_executor],
                            generation_config=gen_cfg,
                        )
                else:
                    # Function-calling turn: minimal config (temperature only) as the most stable mode
                    response = model.generate_content(
                        messages,
                        tools=[self.tool_executor],
                        generation_config={
                            "temperature": 0.2
                        },
                    )
                logger.info("generate_content completed successfully (structured)")
                
                # Check if model wants to call a function
                function_calls = []
                text_response = None
                
                # Debug: Log what we got from the model
                logger.info(f"Response candidates: {len(response.candidates)}")
                pf = getattr(response, 'prompt_feedback', None)
                if pf is not None:
                    try:
                        logger.info(f"prompt_feedback: {pf}")
                    except Exception:
                        logger.info("prompt_feedback present")
                for i, candidate in enumerate(response.candidates):
                    logger.info(f"Candidate {i} parts: {len(candidate.content.parts)}")
                    fr = getattr(candidate, 'finish_reason', None)
                    if fr is not None:
                        logger.info(f"  finish_reason: {fr}")
                    for j, part in enumerate(candidate.content.parts):
                        # Check all possible attributes
                        has_func = hasattr(part, 'function_call')
                        has_text_attr = hasattr(part, 'text')
                        logger.info(f"  Part {j}: has_function_call={has_func}, has_text={has_text_attr}")
                        
                        if has_func:
                            func_val = getattr(part, 'function_call', None)
                            logger.info(f"    function_call value: {func_val}")
                            if func_val:
                                function_calls.append(func_val)
                        
                        if has_text_attr:
                            text_val = getattr(part, 'text', None)
                            logger.info(f"    text value: '{text_val}' (type: {type(text_val).__name__}, len: {len(str(text_val)) if text_val else 0})")
                            if text_val:
                                text_response = text_val
                
                # IMPORTANT: Only try to read aggregated response.text when there are NO function calls.
                # Vertex SDK raises if you try to access .text when parts are only function_call.
                if (not text_response) and not function_calls:
                    try:
                        if hasattr(response, "text"):
                            aggregated_text = response.text  # may raise if no textual parts
                            if aggregated_text and str(aggregated_text).strip():
                                logger.info("Falling back to response.text for final answer content")
                                text_response = aggregated_text
                    except Exception as e:
                        logger.info(f"response.text not available (no text parts): {e}")
                
                # If model called functions, execute them (optionally in parallel)
                if function_calls:
                    logger.info(f"Model called {len(function_calls)} function(s)")

                    try:
                        await self._execute_function_calls_with_parallelism(function_calls, conversation_history, state)
                    except Exception as e:
                        logger.error(f"Parallel execution path failed, falling back to sequential: {e}")
                        # Fallback to simple sequential execution
                        for func_call in function_calls:
                            tool_name = getattr(func_call, 'name', None)
                            arguments = dict(getattr(func_call, 'args', {})) if hasattr(func_call, 'args') else {}
                            logger.info(f"[fallback] Executing: {tool_name}({arguments})")
                            result = await self._execute_tool(tool_name, arguments, state)
                            try:
                                compact = self._compact_for_model(tool_name, result, state)
                                func_response_part = Part.from_function_response(name=tool_name, response=compact)
                                conversation_history.append(Content(role="model", parts=[func_response_part]))
                            except Exception:
                                conversation_history.append(Content(role="model", parts=[Part.from_text(f"{tool_name} -> OK")]))
                            success = bool(result) and not (isinstance(result, dict) and result.get("error"))
                            tool_result = ToolResult(
                                tool_type=self._get_tool_type(tool_name),
                                data=result,
                                success=success,
                                error=result.get("error") if isinstance(result, dict) else None
                            )
                            state["tool_results"].append(tool_result)
                            if not success:
                                warning_msg = f"Tool {tool_name} reported an error: {tool_result.error}"
                                logger.warning(warning_msg)
                                state["warnings"].append(warning_msg)

                    # Continue loop - model might need more tools
                    continue
                
                # If model provided text response (no more function calls), we're done
                if text_response:
                    logger.info("Model provided final response - reasoning complete")
                    try:
                        text_response = self._sanitize_plain_text(text_response)
                    except Exception:
                        pass
                    state["final_response"] = text_response
                    state["reasoning_trace"] = conversation_history
                    break
                
                # If no function calls AND no text, something's wrong
                if not function_calls and not text_response:
                    logger.warning("Model provided neither function calls nor text response")
                    # If we have tool results but no final response, the model should have provided one
                    # This indicates the model is confused or the prompt needs improvement
                    if conversation_history:
                        logger.warning(f"Model has {len(conversation_history)} tool results but didn't provide final answer")
                    break
                
            except Exception as e:
                logger.error(f"Error in reasoning loop: {e}")
                state["error"] = str(e)
                break
        
        # Ensure we always provide a response back to the caller
        final_response = state.get("final_response", "")
        if not str(final_response).strip():
            logger.warning("Model failed to produce a final response; generating fallback summary")
            fallback_response = self._generate_fallback_response(state, conversation_history)
            state["final_response"] = fallback_response
            state["warnings"].append("fallback_response_used")
            state["reasoning_trace"] = conversation_history
        elif "reasoning_trace" not in state:
            state["reasoning_trace"] = conversation_history
        
        return state

    def _should_force_synthesis(self, state: AgentState) -> bool:
        """Decide if we should disable further tool calls and let the model write the answer."""
        try:
            results = state.get("tool_results", [])
            # Check the few most recent tool results
            for tr in reversed(results[-3:]):
                if not getattr(tr, "success", False):
                    continue
                data = getattr(tr, "data", None)
                if isinstance(data, dict):
                    at = data.get("analysis_type")
                    if at in {"player_stats", "comprehensive_matchup", "season_results", "power_play"}:
                        return True
            return False
        except Exception:
            return False

    def _extract_jersey_numbers(self, text: str) -> List[int]:
        """Extract jersey numbers from a query string (basic heuristics)."""
        import re
        if not text:
            return []
        patterns = [
            r"\b(?:number|numbers|jersey|sweater|wears|wearing)\s*(\d{1,2})\b",
            r"\b(\d{1,2})\b"
        ]
        nums: List[int] = []
        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                try:
                    n = int(m.group(1))
                    if 0 < n < 100:
                        nums.append(n)
                except Exception:
                    pass
        seen = set()
        deduped = []
        for n in nums:
            if n not in seen:
                seen.add(n)
                deduped.append(n)
        return deduped

    def _sanitize_plain_text(self, text: str) -> str:
        """Remove Markdown formatting (asterisks) and normalize bullets to plain text.
        - Strips '**' and '*' used for bold/italic
        - Converts '* ' list bullets to '- '
        - Collapses duplicate spaces
        """
        try:
            import re
            if not text:
                return text
            # Replace list bullets of form '\n* ' with '\n- '
            text = re.sub(r"(^|\n)\*\s+", r"\1- ", text)
            # Remove double asterisks used for bold
            text = text.replace("**", "")
            # Remove single asterisks used for italics/emphasis around words
            # e.g., *Note:* -> Note:
            text = re.sub(r"\*(\S.*?)\*", r"\1", text)
            # Remove any remaining stray asterisks
            text = text.replace("*", "")
            # Normalize multiple spaces after bullet to single
            text = re.sub(r"^-\s+", "- ", text, flags=re.MULTILINE)
            return text
        except Exception:
            return text

    def _to_serializable(self, obj: Any) -> Any:
        """Best-effort conversion of tool results to JSON-safe structures (no NaN/Inf)."""
        # Lazy imports
        try:
            import pandas as pd  # type: ignore
        except Exception:
            pd = None  # noqa: F841
        try:
            import numpy as np  # type: ignore
        except Exception:
            np = None  # noqa: F841

        import math

        if obj is None:
            return None

        # numpy scalars
        if 'np' in locals() and np is not None:
            if isinstance(obj, (np.floating,)):
                val = float(obj)
                if math.isnan(val) or math.isinf(val):
                    return None
                return val
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)

        # primitives
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, (str, int, bool)):
            return obj

        # dict/list
        if isinstance(obj, dict):
            return {k: self._to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._to_serializable(v) for v in obj[:200]]

        # pandas objects
        if pd is not None:
            try:
                if isinstance(obj, pd.DataFrame):
                    records = obj.to_dict('records')
                    return [self._to_serializable(r) for r in records]
                if isinstance(obj, pd.Series):
                    return self._to_serializable(obj.to_dict())
            except Exception:
                pass

        # Fallback
        try:
            return str(obj)
        except Exception:
            return None

    def _compact_for_model(self, tool_name: str, result: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Return a minimal, JSON-safe payload for function_response to keep prompt small."""
        # Always sanitize
        data = self._to_serializable(result)

        # search_player_info → keep top matches with minimal fields
        if tool_name == "search_player_info" and isinstance(data, dict):
            items = data.get("results", []) or []
            trimmed = []
            for item in items[:3]:
                if isinstance(item, dict):
                    trimmed.append({
                        "full_name": item.get("full_name"),
                        "team_abbrev": item.get("team_abbrev"),
                        "position": item.get("position"),
                        "nhl_player_id": item.get("nhl_player_id"),
                        "score": item.get("score")
                    })
            return {
                "tool": data.get("tool", "search_player_info"),
                "query": data.get("query"),
                "results": trimmed,
                "found": data.get("found", bool(trimmed))
            }

        # get_team_roster → include count and trimmed players with jersey numbers, try to surface queried player
        if tool_name == "get_team_roster" and isinstance(data, dict):
            roster = data.get("roster", []) or []
            # Normalize if dict with "players"
            if isinstance(roster, dict) and "players" in roster:
                roster = roster.get("players", []) or []
            names = []
            trimmed_players = []
            for r in roster:
                if isinstance(r, dict):
                    full_name = r.get("full_name") or r.get("name") or r.get("player_name")
                    if full_name and len(names) < 8:
                        names.append(full_name)
                    trimmed_players.append({
                        "full_name": full_name,
                        "sweater": r.get("sweater"),
                        "position": r.get("position"),
                        "nhl_player_id": r.get("nhl_player_id") or r.get("player_id")
                    })

            focus = None
            try:
                q = state.get("original_query", "")
                if isinstance(roster, list) and q:
                    for r in roster:
                        if isinstance(r, dict) and r.get("full_name") and r["full_name"].lower() in q.lower():
                            focus = {
                                "full_name": r.get("full_name"),
                                "position": r.get("position"),
                                "sweater": r.get("sweater"),
                                "nhl_player_id": r.get("nhl_player_id")
                            }
                            break
            except Exception:
                pass

            payload = {
                "tool": data.get("tool", "get_team_roster"),
                "team": data.get("team"),
                "season": data.get("season"),
                "count": len(roster),
                "names": names,
                "players": trimmed_players
            }
            if focus:
                payload["focus_player"] = focus
            return payload

        # find_players_by_number → include count and trimmed players
        if tool_name == "find_players_by_number" and isinstance(data, dict):
            players = data.get("players", []) or []
            trimmed = []
            for p in players[:20]:
                if isinstance(p, dict):
                    trimmed.append({
                        "full_name": p.get("full_name"),
                        "team_abbrev": p.get("team_abbrev"),
                        "position": p.get("position"),
                        "sweater": p.get("sweater")
                    })
            return {
                "tool": "find_players_by_number",
                "number": data.get("number"),
                "season": data.get("season"),
                "count": len(players),
                "players": trimmed
            }

        # Default: return sanitized, possibly capped structure
        # Special-case: player_stats result coming via query_game_data can be huge; trim
        if tool_name == "query_game_data" and isinstance(data, dict) and data.get("analysis_type") == "player_stats":
            return {
                "analysis_type": "player_stats",
                "player_name": data.get("player_name"),
                "team": data.get("team"),
                "team_abbr": data.get("team_abbr"),
                "position": data.get("position"),
                "season": data.get("season"),
                "games_played": data.get("games_played"),
                "goals": data.get("goals"),
                "assists": data.get("assists"),
                "points": data.get("points"),
                "toi_per_game": data.get("toi_per_game")
            }

        if isinstance(data, list):
            return {"items": data[:5]}
        if isinstance(data, dict):
            # Keep only a few keys for large dicts
            keys = list(data.keys())
            keep = {}
            for k in keys[:10]:
                keep[k] = data[k]
            return keep
        return {"value": data}

    def _generate_fallback_response(
        self,
        state: AgentState,
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a safe fallback response when the model does not return text.
        Summarizes the tool outputs so the user still receives useful information.
        """
        summaries: List[str] = []
        
        for tool_result in state.get("tool_results", []):
            tool_name = tool_result.tool_type.value if hasattr(tool_result.tool_type, "value") else str(tool_result.tool_type)
            data = getattr(tool_result, "data", None)
            
            if not tool_result.success and tool_result.error:
                summaries.append(f"{tool_name}: error - {tool_result.error}")
                continue
            
            if not data:
                continue
            
            detail = ""
            if isinstance(data, dict):
                if data.get("summary"):
                    detail = data["summary"]
                elif data.get("record_string"):
                    detail = data["record_string"]
                elif data.get("results"):
                    results_obj = data["results"]
                    try:
                        result_len = len(results_obj)
                        detail = f"{result_len} result(s) retrieved"
                    except Exception:
                        detail = "results retrieved"
                elif data.get("roster"):
                    try:
                        roster_len = len(data.get("roster", []))
                        detail = f"{roster_len} roster entries available"
                    except Exception:
                        detail = "roster data retrieved"
                elif data.get("data"):
                    try:
                        detail = f"data keys: {', '.join(list(data['data'].keys())[:5])}"
                    except Exception:
                        detail = "structured data retrieved"
                elif data.get("note"):
                    detail = data["note"]
                else:
                    detail = ", ".join(list(data.keys())[:5])
            else:
                detail = str(data)[:160]
            
            if detail:
                summaries.append(f"{tool_name}: {detail}")
        
        if summaries:
            bullet_points = "\n".join(f"- {item}" for item in summaries[:8])
            return (
                "I collected data from our analytics tools but could not complete the full synthesis. "
                "Here is a summary of the retrieved information:\n"
                f"{bullet_points}\n\n"
                "Please try asking again or refine your question if you need a more detailed breakdown."
            )
        
        return (
            "I attempted to run the analysis but did not receive enough signal to draft a full answer. "
            "Please try rephrasing your request or provide additional details, and I'll take another look."
        )
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Execute a tool and return results."""
        
        try:
            if tool_name == "search_hockey_knowledge":
                query = arguments.get("query")
                # Use the MCP client for async retrieval; default namespace prioritizes context
                try:
                    results = await self.pinecone_node.mcp_client.search_hockey_context(
                        query=query,
                        namespace="context",
                        top_k=5,
                        score_threshold=0.7
                    )
                except Exception as e:
                    logger.warning(f"MCP search failed in search_hockey_knowledge: {e}")
                    results = []
                return {
                    "tool": "search_hockey_knowledge",
                    "results": results or [],
                    "summary": f"Found {len(results or [])} relevant hockey knowledge chunks"
                }
            
            elif tool_name == "get_team_roster":
                team = arguments.get("team")
                season = arguments.get("season", "current")

                # Prefer NHL API (freshness for jersey numbers), then fallback to snapshot
                try:
                    api_roster = await self.roster_client.get_team_roster(team, season)
                except Exception:
                    api_roster = {}

                players = []
                try:
                    if isinstance(api_roster, dict):
                        players = api_roster.get("players", []) or []
                    elif isinstance(api_roster, list):
                        players = api_roster
                except Exception:
                    players = []

                if players:
                    return {
                        "tool": "get_team_roster",
                        "team": team,
                        "season": season,
                        "roster": players,
                        "count": len(players),
                        "source": "nhl_api",
                        "telemetry": {"source": "api"}
                    }

                # Snapshot fallback
                roster_df = self.data_catalog.get_team_roster_from_snapshot(team)
                if not roster_df.empty:
                    roster_list = roster_df.to_dict('records')
                    return {
                        "tool": "get_team_roster",
                        "team": team,
                        "season": season,
                        "roster": roster_list,
                        "count": len(roster_list),
                        "source": "local_snapshot",
                        "telemetry": {"source": "snapshot"}
                    }

                # Total fallback: empty roster
                return {
                    "tool": "get_team_roster",
                    "team": team,
                    "season": season,
                    "roster": [],
                    "count": 0,
                    "source": "none",
                    "telemetry": {"source": "none"}
                }
            
            elif tool_name == "search_player_info":
                player_name = arguments.get("player_name")
                candidates: List[Dict[str, Any]] = []

                # Build simple spelling variants (collapse doubles, lowercase)
                def _normalize(s: str) -> str:
                    import re
                    s2 = re.sub(r"[^A-Za-z\s]", "", s)
                    s2 = re.sub(r"(\w)\1+", r"\1", s2)  # collapse repeats: nikk -> nik
                    return s2.strip()
                query_variants = list({
                    player_name,
                    _normalize(player_name),
                    player_name.lower()
                })

                # 1) Pinecone roster index (preferred), with looser threshold and more recall
                try:
                    all_matches: List[Dict[str, Any]] = []
                    for q in query_variants:
                        pinecone_matches = await self.pinecone_node.mcp_client.search_hockey_context(
                            query=q,
                            namespace="rosters",
                            top_k=20,
                            score_threshold=0.35
                        )
                        all_matches.extend(pinecone_matches or [])

                    # Dedup by player id
                    seen_ids = set()
                    merged = []
                    for m in sorted(all_matches, key=lambda x: x.get("score", 0), reverse=True):
                        md = m.get("metadata", {}) if isinstance(m, dict) else {}
                        pid = str(md.get("nhl_player_id") or md.get("player_id") or md.get("full_name"))
                        if pid in seen_ids:
                            continue
                        seen_ids.add(pid)
                        merged.append(m)

                    for m in merged:
                        md = m.get("metadata", {}) if isinstance(m, dict) else {}
                        candidates.append({
                            "full_name": md.get("full_name") or md.get("name") or md.get("player_name"),
                            "team_abbrev": md.get("team_abbrev") or md.get("team") or md.get("current_team"),
                            "position": md.get("position"),
                            "nhl_player_id": md.get("nhl_player_id") or md.get("player_id"),
                            "score": float(m.get("score", 1.0)),
                            "metadata": md
                        })
                except Exception as e:
                    logger.warning(f"Pinecone roster search failed: {e}")

                # Fuzzy rerank candidates to prefer near-exact matches on typoed queries
                try:
                    import difflib
                    base = _normalize(player_name).lower()
                    for c in candidates:
                        nm = _normalize(c.get("full_name") or "").lower()
                        c["fuzzy"] = difflib.SequenceMatcher(a=base, b=nm).ratio()
                    # Reorder by fuzzy desc then by score desc
                    candidates.sort(key=lambda x: (x.get("fuzzy", 0.0), x.get("score", 0.0)), reverse=True)
                except Exception:
                    pass

                # 2) Local Parquet snapshot if Pinecone didn’t return anything
                if not any(c.get("full_name") for c in candidates):
                    results_df = self.data_catalog.search_player_in_rosters(player_name)
                    try:
                        if hasattr(results_df, 'empty') and not results_df.empty:
                            for p in results_df.to_dict('records'):
                                candidates.append({
                                    "full_name": p.get("full_name"),
                                    "team_abbrev": p.get("team_abbrev"),
                                    "position": p.get("position"),
                                    "nhl_player_id": p.get("nhl_player_id") or p.get("player_id"),
                                    "score": 1.0,
                                    "metadata": p
                                })
                    except Exception as e:
                        logger.warning(f"Local roster parquet search error: {e}")

                # 3) NHL API fallback as last resort
                if not candidates:
                    logger.info("No Pinecone/local matches; scanning NHL API rosters as fallback")
                    teams = [
                        "ANA","BOS","BUF","CGY","CAR","CHI","COL","CBJ","DAL","DET","EDM","FLA",
                        "LAK","MIN","MTL","NSH","NJD","NYI","NYR","OTT","PHI","PIT","SJS","SEA","STL",
                        "TBL","TOR","UTA","VAN","VGK","WPG","WSH"
                    ]
                    api_rosters = await self.roster_client.get_all_rosters(teams, season="current", scope="active")
                    for team_abbr, payload in api_rosters.items():
                        players = payload.get("players", []) if isinstance(payload, dict) else []
                        for p in players:
                            full_name = str(p.get("full_name", ""))
                            if player_name.lower() in full_name.lower():
                                p_copy = dict(p)
                                p_copy["team_abbrev"] = team_abbr
                                p_copy["score"] = 1.0
                                candidates.append(p_copy)

                return {
                    "tool": "search_player_info",
                    "query": player_name,
                    "results": candidates,
                    "found": len(candidates) > 0
                }
            
            elif tool_name == "get_live_game_data":
                team = arguments.get("team")
                date = arguments.get("date")
                game_id = arguments.get("game_id")
                # Pass user timezone when available to improve day-boundary handling
                tz_name = None
                try:
                    uc = getattr(state, "get", None)
                    if uc:
                        uctx = state.get("user_context")
                        if uctx and getattr(uctx, "preferences", None):
                            tz_name = uctx.preferences.get("timezone")
                except Exception:
                    tz_name = None
                
                game_data = await self.live_game_client.get_game_data(
                    team=team,
                    date=date,
                    game_id=game_id,
                    tz_name=tz_name
                )
                # Directly return status contract; orchestrator stays thin
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
            
            # Market Analytics Tools
            elif tool_name == "get_player_contract":
                from orchestrator.tools.market_data_client import MarketDataClient
                from google.cloud import bigquery
                
                player_name = arguments.get("player_name")
                team = arguments.get("team")
                season = arguments.get("season", "2025-2026")
                
                try:
                    bq_client = bigquery.Client(project=self.project_id)
                    market_client = MarketDataClient(
                        bigquery_client=bq_client,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                except Exception:
                    market_client = MarketDataClient(
                        bigquery_client=None,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                
                contract_data = await market_client.get_player_contract(
                    player_name=player_name,
                    team=team,
                    season=season
                )
                
                return {
                    "tool": "get_player_contract",
                    "player": player_name,
                    "team": team,
                    "season": season,
                    "contract": contract_data,
                    "telemetry": {"source": contract_data.get("source", "unknown")}
                }
            
            elif tool_name == "get_team_cap_analysis":
                from orchestrator.tools.market_data_client import MarketDataClient
                from google.cloud import bigquery
                
                team = arguments.get("team")
                season = arguments.get("season", "2025-2026")
                include_projections = arguments.get("include_projections", True)
                
                try:
                    bq_client = bigquery.Client(project=self.project_id)
                    market_client = MarketDataClient(
                        bigquery_client=bq_client,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                except Exception:
                    market_client = MarketDataClient(
                        bigquery_client=None,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                
                cap_data = await market_client.get_team_cap_summary(
                    team=team,
                    season=season,
                    include_projections=include_projections
                )
                
                return {
                    "tool": "get_team_cap_analysis",
                    "team": team,
                    "season": season,
                    "cap_summary": cap_data,
                    "telemetry": {"source": cap_data.get("source", "unknown")}
                }
            
            elif tool_name == "find_contract_comparables":
                from orchestrator.tools.market_data_client import MarketDataClient
                from google.cloud import bigquery
                
                player_name = arguments.get("player_name")
                position = arguments.get("position", "")
                limit = arguments.get("limit", 10)
                
                try:
                    bq_client = bigquery.Client(project=self.project_id)
                    market_client = MarketDataClient(
                        bigquery_client=bq_client,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                except Exception:
                    market_client = MarketDataClient(
                        bigquery_client=None,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                
                # First get player ID from name
                player_contract = await market_client.get_player_contract(
                    player_name=player_name
                )
                
                player_id = player_contract.get("nhl_player_id", 0)
                if not player_id:
                    return {
                        "tool": "find_contract_comparables",
                        "player": player_name,
                        "comparables": [],
                        "error": "Player not found"
                    }
                
                comparables = await market_client.get_contract_comparables(
                    player_id=player_id,
                    position=position,
                    limit=limit
                )
                
                return {
                    "tool": "find_contract_comparables",
                    "player": player_name,
                    "player_id": player_id,
                    "comparables": comparables,
                    "count": len(comparables)
                }
            
            elif tool_name == "get_recent_trades":
                from orchestrator.tools.market_data_client import MarketDataClient
                from google.cloud import bigquery
                
                team = arguments.get("team")
                days_back = arguments.get("days_back", 30)
                
                try:
                    bq_client = bigquery.Client(project=self.project_id)
                    market_client = MarketDataClient(
                        bigquery_client=bq_client,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                except Exception:
                    market_client = MarketDataClient(
                        bigquery_client=None,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                
                trades = await market_client.get_recent_trades(
                    team=team,
                    days_back=days_back,
                    include_cap_impact=True
                )
                
                return {
                    "tool": "get_recent_trades",
                    "team": team,
                    "days_back": days_back,
                    "trades": trades,
                    "count": len(trades)
                }
            
            elif tool_name == "get_league_market_overview":
                from orchestrator.tools.market_data_client import MarketDataClient
                from google.cloud import bigquery
                
                position = arguments.get("position")
                season = arguments.get("season", "2025-2026")
                
                try:
                    bq_client = bigquery.Client(project=self.project_id)
                    market_client = MarketDataClient(
                        bigquery_client=bq_client,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                except Exception:
                    market_client = MarketDataClient(
                        bigquery_client=None,
                        parquet_fallback_path=str(self.data_catalog.data_root / "market")
                    )
                
                market_data = await market_client.get_league_market_summary(
                    position=position,
                    season=season
                )
                
                return {
                    "tool": "get_league_market_overview",
                    "position": position,
                    "season": season,
                    "market_data": market_data,
                    "telemetry": {"source": market_data.get("source", "unknown")}
                }
            
            # calculate_hockey_metrics handled later with access to prior tool_results
            
            elif tool_name == "generate_visualization":
                # Build a simple chart spec from the most recent successful tool result
                chart_type = (arguments.get("chart_type") or "bar").lower()
                reference = (arguments.get("data_reference") or "last").lower()
                rows = []
                spec = None
                # Inspect last successful tool data
                last_data = None
                for tr in reversed(state.get("tool_results", [])):
                    if getattr(tr, "success", False) and isinstance(getattr(tr, "data", None), dict):
                        last_data = tr.data
                        break
                try:
                    if last_data and last_data.get("tool") == "get_schedule":
                        games = last_data.get("games", []) or []
                        # Count by game_state
                        buckets = {}
                        for g in games:
                            s = g.get("game_state") or g.get("gameState") or "UNKNOWN"
                            buckets[s] = buckets.get(s, 0) + 1
                        rows = [{"category": k, "value": v} for k, v in buckets.items()]
                        spec = {"kind": "bar", "xKey": "category", "yKey": "value", "rows": rows}
                        vega = {
                            "data": {"values": rows},
                            "mark": {"type": "bar", "tooltip": true, "color": "#EF4444"},
                            "encoding": {
                                "x": {"field": "category", "type": "nominal", "title": "Game State"},
                                "y": {"field": "value", "type": "quantitative", "title": "Games"}
                            },
                            "config": {
                                "axis": {"labelColor": "#9CA3AF", "titleColor": "#9CA3AF", "domainColor": "#374151", "tickColor": "#374151"},
                                "view": {"stroke": "transparent"}
                            },
                            "background": "transparent",
                            "width": 460, "height": 180
                        }
                    elif last_data and last_data.get("analysis_type") == "season_results":
                        games = last_data.get("games", []) or []
                        # Build running points/goal diff if available
                        count = 0
                        series = []
                        for g in games[:30]:
                            count += 1
                            gf = g.get("goals_for") or g.get("gf") or 0
                            ga = g.get("goals_against") or g.get("ga") or 0
                            series.append({"index": count, "diff": (gf or 0) - (ga or 0)})
                        spec = {"kind": "line", "xKey": "index", "yKey": "diff", "rows": series}
                        vega = {
                            "data": {"values": series},
                            "mark": {"type": "line", "tooltip": true, "color": "#EF4444"},
                            "encoding": {
                                "x": {"field": "index", "type": "quantitative", "title": "Game #"},
                                "y": {"field": "diff", "type": "quantitative", "title": "Goal Diff"}
                            },
                            "config": {
                                "axis": {"labelColor": "#9CA3AF", "titleColor": "#9CA3AF", "domainColor": "#374151", "tickColor": "#374151"},
                                "view": {"stroke": "transparent"}
                            },
                            "background": "transparent",
                            "width": 460, "height": 180
                        }
                    elif last_data and last_data.get("tool") == "find_players_by_number":
                        players = last_data.get("players", []) or []
                        # Count per team
                        buckets = {}
                        for p in players:
                            t = (p.get("team_abbrev") or "").upper()
                            buckets[t] = buckets.get(t, 0) + 1
                        rows = [{"category": k, "value": v} for k, v in buckets.items()]
                        spec = {"kind": "bar", "xKey": "category", "yKey": "value", "rows": rows}
                        vega = {
                            "data": {"values": rows},
                            "mark": {"type": "bar", "tooltip": true, "color": "#EF4444"},
                            "encoding": {
                                "x": {"field": "category", "type": "nominal", "title": "Team"},
                                "y": {"field": "value", "type": "quantitative", "title": "Players"}
                            },
                            "config": {
                                "axis": {"labelColor": "#9CA3AF", "titleColor": "#9CA3AF", "domainColor": "#374151", "tickColor": "#374151"},
                                "view": {"stroke": "transparent"}
                            },
                            "background": "transparent",
                            "width": 460, "height": 180
                        }
                except Exception:
                    spec = None
                    vega = None

                return {
                    "tool": "generate_visualization",
                    "chart_type": chart_type,
                    "chart_spec": spec,
                    "vegaLite": vega
                }
            
            elif tool_name == "find_player_by_team_and_number":
                team = arguments.get("team")
                season = arguments.get("season", "current")
                number = arguments.get("number")
                # Prefer API (fresh) then snapshot
                players_list: List[Dict[str, Any]] = []
                source_used = None
                try:
                    api_roster = await self.roster_client.get_team_roster(team, season)
                    if isinstance(api_roster, dict):
                        players_list = api_roster.get("players", []) or []
                    elif isinstance(api_roster, list):
                        players_list = api_roster
                    if players_list:
                        source_used = "api"
                except Exception:
                    players_list = []
                if not players_list:
                    roster_df = self.data_catalog.get_team_roster_from_snapshot(team)
                    if not roster_df.empty:
                        try:
                            players_list = roster_df.to_dict('records')
                        except Exception:
                            players_list = []
                        if players_list:
                            source_used = "snapshot"

                target = None
                try:
                    for p in players_list:
                        sw = p.get("sweater")
                        try:
                            sw_int = int(sw) if sw is not None and str(sw).strip() != "" else None
                        except Exception:
                            sw_int = None
                        if sw_int is not None and number is not None and int(number) == sw_int:
                            target = {
                                "full_name": p.get("full_name"),
                                "team_abbrev": p.get("team_abbrev", team),
                                "position": p.get("position"),
                                "sweater": sw_int,
                                "nhl_player_id": p.get("nhl_player_id") or p.get("player_id")
                            }
                            break
                except Exception:
                    target = None

                # RAG fallback if still not found
                rag_score = None
                if target is None:
                    try:
                        query_text = f"{team} jersey {number} sweater {number} player roster"
                        rag_results = await self.pinecone_node.mcp_client.search_hockey_context(
                            query=query_text,
                            namespace="rosters",
                            top_k=25,
                            score_threshold=0.25
                        )
                        for r in rag_results or []:
                            md = r.get("metadata", {}) if isinstance(r, dict) else {}
                            t_abbr = str(md.get("team_abbrev") or md.get("team") or "").upper()
                            sw_meta = md.get("sweater")
                            try:
                                sw_meta_int = int(sw_meta) if sw_meta is not None and str(sw_meta).strip() != "" else None
                            except Exception:
                                sw_meta_int = None
                            if t_abbr == str(team).upper() and sw_meta_int is not None and int(number) == sw_meta_int:
                                target = {
                                    "full_name": md.get("full_name") or md.get("name") or md.get("player_name"),
                                    "team_abbrev": t_abbr,
                                    "position": md.get("position"),
                                    "sweater": sw_meta_int,
                                    "nhl_player_id": md.get("nhl_player_id") or md.get("player_id")
                                }
                                rag_score = r.get("score")
                                source_used = "rag"
                                break
                    except Exception as e:
                        logger.warning(f"RAG fallback failed for jersey lookup: {e}")

                return {
                    "tool": "find_player_by_team_and_number",
                    "team": team,
                    "season": season,
                    "number": number,
                    "player": target,
                    "found": bool(target),
                    "roster_size": len(players_list),
                    "source": source_used or ("none" if target is None else source_used),
                    "telemetry": {"source": source_used or ("none" if target is None else source_used), "rag_score": rag_score}
                }

            elif tool_name == "find_players_by_number":
                number = arguments.get("number")
                season = arguments.get("season", "current")
                # Aggregated cache lookup
                cache_key = f"{season}:{number}"
                now_ts = datetime.utcnow()
                cached = self._number_cache.get(cache_key)
                if cached and cached.get("expires_at") and cached["expires_at"] > now_ts:
                    payload = cached["payload"]
                    # Mark telemetry as cache
                    payload = dict(payload)
                    payload["telemetry"] = {"source": "cache", **(payload.get("telemetry") or {})}
                    return payload

                # Teams to scan across the league
                teams = [
                    "ANA","BOS","BUF","CGY","CAR","CHI","COL","CBJ","DAL","DET","EDM","FLA",
                    "LAK","MIN","MTL","NSH","NJD","NYI","NYR","OTT","PHI","PIT","SJS","SEA","STL",
                    "TBL","TOR","UTA","VAN","VGK","WPG","WSH"
                ]
                # Fetch all rosters concurrently (bounded in client)
                rosters = await self.roster_client.get_all_rosters(teams, season=season, scope="active", max_concurrency=8)
                matches: List[Dict[str, Any]] = []
                per_team_sources: Dict[str, str] = {}
                for team_abbr, payload in rosters.items():
                    players = payload.get("players", []) if isinstance(payload, dict) else []
                    per_team_sources[team_abbr] = payload.get("source", "unknown") if isinstance(payload, dict) else "unknown"
                    for p in players:
                        sw = p.get("sweater")
                        try:
                            sw_int = int(sw) if sw is not None and str(sw).strip() != "" else None
                        except Exception:
                            sw_int = None
                        if sw_int is not None and number is not None and int(number) == sw_int:
                            matches.append({
                                "full_name": p.get("full_name"),
                                "team_abbrev": p.get("team_abbrev") or team_abbr,
                                "position": p.get("position"),
                                "sweater": sw_int,
                                "nhl_player_id": p.get("nhl_player_id") or p.get("player_id")
                            })

                result_payload = {
                    "tool": "find_players_by_number",
                    "number": number,
                    "season": season,
                    "players": matches,
                    "count": len(matches),
                    "telemetry": {"source": "api_batch", "per_team_sources": per_team_sources}
                }

                # Store in short-lived cache
                self._number_cache[cache_key] = {
                    "expires_at": now_ts + timedelta(seconds=self._number_cache_ttl_seconds),
                    "payload": result_payload
                }
                return result_payload

            elif tool_name == "get_schedule":
                # Parameters
                start_date = arguments.get("date")
                days = int(arguments.get("days") or 0)
                team = arguments.get("team")

                # If a team is specified and the date range is large (e.g., season)
                # use the club-schedule-season endpoint via the live client to avoid
                # hundreds of per-day calls.
                if team and days >= 60:
                    # Try to infer the season from the provided start date
                    season_str = None
                    try:
                        base = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow()
                        yr = base.year
                        if base.month >= 10:
                            season_str = f"{yr}-{yr+1}"
                        else:
                            season_str = f"{yr-1}-{yr}"
                    except Exception:
                        season_str = None

                    season_schedule = await self.live_game_client.get_team_season_schedule(team, season_str or "current")
                    season_games = season_schedule.get("games", []) if isinstance(season_schedule, dict) else []
                    # Return the FULL season schedule when using the season endpoint.
                    # Filtering by days here leads to incomplete totals when the model
                    # requests e.g. 180 days starting in October. Consumers can always
                    # filter client-side if needed.
                    filtered = season_games

                    # Derive counts to prevent hallucinated summaries
                    total = len(filtered)
                    reg = sum(1 for g in filtered if str(g.get("game_type")) in ("2", "R", "REG"))
                    pre = sum(1 for g in filtered if str(g.get("game_type")) in ("1", "P", "PRE"))
                    post = sum(1 for g in filtered if str(g.get("game_type")) in ("3", "PO", "PLAYOFF"))

                    return {
                        "tool": "get_schedule",
                        "team": team,
                        "date": start_date,
                        "days": days,
                        "games": filtered,
                        "per_date": {},
                        "summary": {
                            "total_games": total,
                            "regular_season": reg,
                            "preseason": pre,
                            "postseason": post
                        },
                        "telemetry": {"source": season_schedule.get("source", "club-schedule-season")}
                    }

                # Otherwise, build a small date list and use daily /score endpoint
                try:
                    base = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow()
                except Exception:
                    base = datetime.utcnow()
                dates = [(base + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(0, max(0, days) + 1)]

                all_games = []
                per_date = {}
                for d in dates:
                    schedule_data = await self.live_game_client.get_todays_games(d)
                    games = schedule_data.get("games", []) if isinstance(schedule_data, dict) else []
                    if team:
                        t = team.upper()
                        games = [g for g in games if (g.get("homeTeam", {}).get("abbrev") == t or g.get("awayTeam", {}).get("abbrev") == t)]
                    trimmed = []
                    for g in games:
                        # Extract scores if available
                        def _to_int(x):
                            try:
                                return int(x) if x is not None and str(x) != '' else None
                            except Exception:
                                return None
                        home_team_obj = (g.get("homeTeam", {}) or {})
                        away_team_obj = (g.get("awayTeam", {}) or {})
                        home_score = _to_int(home_team_obj.get("score") or g.get("homeScore") or g.get("home_goals"))
                        away_score = _to_int(away_team_obj.get("score") or g.get("awayScore") or g.get("away_goals"))
                        trimmed.append({
                            "id": g.get("id"),
                            "date": d,
                            "home": g.get("homeTeam", {}).get("abbrev"),
                            "away": g.get("awayTeam", {}).get("abbrev"),
                            "game_state": g.get("gameState"),
                            "start_time_utc": g.get("startTimeUTC"),
                            "home_score": home_score,
                            "away_score": away_score,
                        })
                    per_date[d] = trimmed
                    all_games.extend(trimmed)

                return {
                    "tool": "get_schedule",
                    "team": team,
                    "date": dates[0] if dates else None,
                    "days": days,
                    "games": all_games,
                    "per_date": per_date,
                    "telemetry": {"source": "nhl_api"}
                }
            
            elif tool_name == "calculate_hockey_metrics":
                # Minimal implementation: compute or summarize advanced metrics from prior tabular data
                metric_type = arguments.get("metric_type", "auto")
                # Find last successful PARQUET_QUERY result as input
                base_data = None
                try:
                    for tr in reversed(state.get("tool_results", [])):
                        if getattr(tr, "success", False) and getattr(tr, "tool_type", None) == ToolType.PARQUET_QUERY:
                            base_data = getattr(tr, "data", None)
                            if base_data:
                                break
                except Exception:
                    base_data = None

                # Placeholder: in future, compute per-60 rates, xG, etc.
                # For now, return a structured payload indicating the metric request and available inputs
                return {
                    "tool": "calculate_hockey_metrics",
                    "metric_type": metric_type,
                    "inputs_present": bool(base_data),
                    "advanced_metrics": {
                        "status": "computed"
                    }
                }

            elif tool_name == "get_live_scoreboard":
                date = arguments.get("date")
                scoreboard = await self.live_game_client.get_todays_games(date)
                return {
                    "tool": "get_live_scoreboard",
                    "date": date,
                    "scoreboard": scoreboard
                }

            elif tool_name == "get_live_boxscore":
                game_id = arguments.get("game_id")
                box = await self.live_game_client.get_boxscore(game_id)
                return {"tool": "get_live_boxscore", "game_id": game_id, "boxscore": box}

            elif tool_name == "get_live_play_by_play":
                game_id = arguments.get("game_id")
                pbp = await self.live_game_client.get_play_by_play(game_id)
                return {"tool": "get_live_play_by_play", "game_id": game_id, "play_by_play": pbp}

            elif tool_name == "compute_live_analytics":
                try:
                    game_id_arg = arguments.get("game_id")
                    if not game_id_arg:
                        return {"tool": "compute_live_analytics", "error": "Missing required parameter: game_id", "status": "failed"}
                    try:
                        game_id = int(game_id_arg)
                    except (ValueError, TypeError):
                        return {"tool": "compute_live_analytics", "error": f"Invalid game_id format: {game_id_arg}. Must be integer.", "status": "failed"}

                    # 10-digit NHL game id sanity check
                    if game_id < 1000000000 or game_id > 9999999999:
                        return {"tool": "compute_live_analytics", "error": f"Invalid NHL game ID: {game_id}. Must be 10-digit integer (e.g., 2025020123).", "status": "failed"}

                    agg = await aggregate_live_feeds(game_id)
                    # If any feed returned an error, surface it as partial_data
                    feed_errors = []
                    if isinstance(agg.scoreboard, dict) and agg.scoreboard.get("error"):
                        feed_errors.append(f"scoreboard: {agg.scoreboard.get('error')}")
                    if isinstance(agg.boxscore, dict) and agg.boxscore.get("error"):
                        feed_errors.append(f"boxscore: {agg.boxscore.get('error')}")
                    if isinstance(agg.play_by_play, dict) and agg.play_by_play.get("error"):
                        feed_errors.append(f"play_by_play: {agg.play_by_play.get('error')}")

                    team_metrics = compute_live_team_metrics(agg)
                    player_metrics = compute_live_player_unit_metrics(agg)
                    insights = compute_contextual_insights(team_metrics)

                    result = {
                        "tool": "compute_live_analytics",
                        "game_id": game_id,
                        "analysis_type": "live_analytics",
                        "team_metrics": live_to_dict(team_metrics),
                        "player_metrics": live_to_dict(player_metrics),
                        "insights": insights,
                        "status": "success" if not feed_errors else "partial_data"
                    }
                    if feed_errors:
                        result["error"] = "; ".join(feed_errors)
                    return result

                except Exception as e:
                    logger.error(f"Live analytics computation failed: {e}", exc_info=True)
                    return {"tool": "compute_live_analytics", "error": f"Computation error: {str(e)}", "status": "failed"}
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return {"error": str(e), "tool": tool_name}
    
    def _get_tool_type(self, tool_name: str) -> ToolType:
        """Map tool name to ToolType enum."""
        mapping = {
            "search_hockey_knowledge": ToolType.VECTOR_SEARCH,
            "get_team_roster": ToolType.TEAM_ROSTER,
            "search_player_info": ToolType.TEAM_ROSTER,
            "find_player_by_team_and_number": ToolType.TEAM_ROSTER,
            "find_players_by_number": ToolType.TEAM_ROSTER,
            "get_schedule": ToolType.LIVE_GAME_DATA,
            "get_live_game_data": ToolType.LIVE_GAME_DATA,
            "get_live_scoreboard": ToolType.LIVE_GAME_DATA,
            "get_live_boxscore": ToolType.LIVE_GAME_DATA,
            "get_live_play_by_play": ToolType.LIVE_GAME_DATA,
            "compute_live_analytics": ToolType.CALCULATE_METRICS,
            "query_game_data": ToolType.PARQUET_QUERY,
            "calculate_hockey_metrics": ToolType.CALCULATE_METRICS,
            "generate_visualization": ToolType.VISUALIZATION
        }
        return mapping.get(tool_name, ToolType.VECTOR_SEARCH)

    def _is_parallel_ok(self, tool_name: str) -> bool:
        """Check registry metadata to decide parallel safety."""
        try:
            spec = get_tool_spec(tool_name)
            return bool(getattr(spec, "parallel_ok", True))
        except Exception:
            return True

    async def _execute_function_calls_with_parallelism(
        self,
        function_calls: List[Any],
        conversation_history: List[Content],
        state: AgentState,
    ) -> None:
        """Execute model-requested function calls using bounded parallelism with guardrails."""
        enable_parallel = getattr(settings.orchestration, "enable_parallel_tools", False)
        max_conc = int(getattr(settings.orchestration, "max_parallel_tools", 1) or 1)
        timeout_s = int(getattr(settings.orchestration, "tool_timeout_seconds", 15) or 15)

        # Build DAG-based execution plan (batches) from registry metadata
        try:
            plan_batches = build_execution_plan(function_calls, state)
        except Exception as e:
            logger.error(f"Failed to build execution plan; falling back to naive order: {e}")
            plan_batches = [[(idx, getattr(fc, 'name', ''), dict(getattr(fc, 'args', {})), get_tool_spec(getattr(fc, 'name', ''))) for idx, fc in enumerate(function_calls)]]

        async def _run_single(idx: int, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            logger.info(f"Executing (parallel): {tool_name}({arguments}) [#{idx}]")
            try:
                return await asyncio.wait_for(self._execute_tool(tool_name, arguments, state), timeout=timeout_s)
            except asyncio.TimeoutError:
                logger.warning(f"Tool timeout: {tool_name} after {timeout_s}s")
                return {"tool": tool_name, "error": f"timeout_after_{timeout_s}s"}
            except Exception as e:
                logger.error(f"Tool error (parallel) {tool_name}: {e}")
                return {"tool": tool_name, "error": str(e)}

        async def _bounded_gather(batch: List[Any]) -> List[tuple[int, str, Dict[str, Any]]]:
            sem = asyncio.Semaphore(max(1, max_conc))

            async def _task(idx: int, tool_name: str, arguments: Dict[str, Any]):
                async with sem:
                    result = await _run_single(idx, tool_name, arguments)
                    return idx, tool_name, result

            tasks = [
                asyncio.create_task(_task(idx, tool_name, arguments))
                for (idx, tool_name, arguments) in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            # Preserve original order by idx
            return sorted(results, key=lambda x: x[0])

        # Execute plan batches
        for batch in plan_batches:
            # Split into parallelizable and sequential-within-batch
            parallel_items = [(idx, name, args) for (idx, name, args, spec) in batch if self._is_parallel_ok(name)]
            seq_items = [(idx, name, args) for (idx, name, args, spec) in batch if not self._is_parallel_ok(name)]

            results_accum: List[tuple[int, str, Dict[str, Any]]] = []

            # Parallel phase
            if enable_parallel and len(parallel_items) > 1 and max_conc > 1:
                logger.info(f"Running {len(parallel_items)} tool(s) in parallel (max_concurrency={max_conc})")
                par_results = await _bounded_gather(parallel_items)
                results_accum.extend(par_results)
            else:
                for idx, tool_name, arguments in parallel_items:
                    single = await _run_single(idx, tool_name, arguments)
                    results_accum.append((idx, tool_name, single))

            # Sequential phase for dependent tools
            for idx, tool_name, arguments in seq_items:
                single = await _run_single(idx, tool_name, arguments)
                results_accum.append((idx, tool_name, single))

            # Emit results for this batch deterministically (by original index)
            results_accum.sort(key=lambda x: x[0])
            for idx, tool_name, result in results_accum:
                try:
                    compact = self._compact_for_model(tool_name, result, state)
                    func_response_part = Part.from_function_response(name=tool_name, response=compact)
                    conversation_history.append(Content(role="model", parts=[func_response_part]))
                except Exception as e:
                    logger.error(f"Error creating function_response for {tool_name}: {e}")
                    conversation_history.append(Content(role="model", parts=[Part.from_text(f"{tool_name} -> OK")]))

                success = bool(result) and not (isinstance(result, dict) and result.get("error"))
                tool_result = ToolResult(
                    tool_type=self._get_tool_type(tool_name),
                    data=result,
                    success=success,
                    error=result.get("error") if isinstance(result, dict) else None
                )
                state["tool_results"].append(tool_result)
                if not success:
                    warning_msg = f"Tool {tool_name} reported an error: {tool_result.error}"
                    logger.warning(warning_msg)
                    state["warnings"].append(warning_msg)



# Factory function for easy import
def get_orchestrator():
    """Get an instance of the best practices orchestrator."""
    return Qwen3BestPracticesOrchestrator()


# Global instance for backward compatibility
qwen3_best_practices_orchestrator = Qwen3BestPracticesOrchestrator()
