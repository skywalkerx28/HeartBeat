"""
HeartBeat Engine - Tool Registry
Typed tool specifications for LLM function calling

Implements the "Kinetic Layer" of the Palantir Ontology pattern:
- Tools are orchestrator functions exposed to the LLM
- Each has a typed JSON schema (inputs/outputs)
- Outputs include object_refs/URIs for ontology linkage
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Input/Output Models
# =============================================================================

class ObjectRef(BaseModel):
    """Reference to an ontology object."""
    object_type: str = Field(description="Type of object (Player, Team, Game, etc.)")
    object_id: str = Field(description="Primary key value")
    uri: Optional[str] = Field(None, description="GCS URI if available")


class ToolResult(BaseModel):
    """Standard tool result wrapper."""
    success: bool
    data: Any
    object_refs: List[ObjectRef] = Field(default_factory=list)
    error: Optional[str] = None
    execution_time_ms: float = 0.0


# =============================================================================
# Tool 1: retrieve_objects (Ontology Retrieval)
# =============================================================================

class RetrieveObjectsInput(BaseModel):
    """Input schema for retrieve_objects tool."""
    query: str = Field(description="Natural language query (e.g., 'Cole Caufield stats', 'Montreal Canadiens roster')")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters: {'object_type': 'Player'|'Team'|'Game', 'team': 'MTL', 'season': '2024-2025'}"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    expand_relationships: bool = Field(default=True, description="Fetch related objects (contracts, games, etc.)")


class RetrieveObjectsOutput(ToolResult):
    """Output schema for retrieve_objects tool."""
    data: Dict[str, Any] = Field(description="Context pack with primary_objects and related_objects")


# =============================================================================
# Tool 2: clip_retriever (Video Clips)
# =============================================================================

class ClipRetrieverInput(BaseModel):
    """Input schema for clip retrieval tool."""
    query: str = Field(description="Search query for clips (e.g., 'Ovechkin goal', 'Canadiens overtime winner')")
    game_id: Optional[int] = Field(None, description="Filter by specific game ID")
    team: Optional[str] = Field(None, description="Filter by team abbreviation")
    event_type: Optional[Literal["goal", "save", "hit", "fight", "highlight"]] = Field(
        None, description="Filter by event type"
    )
    limit: int = Field(default=5, ge=1, le=20)


class ClipRetrieverOutput(ToolResult):
    """Output schema for clip retrieval tool."""
    data: List[Dict[str, Any]] = Field(description="List of clip objects with video URLs and metadata")


# =============================================================================
# Tool 3: search_player_stats (Analytics)
# =============================================================================

class SearchPlayerStatsInput(BaseModel):
    """Input schema for player stats search."""
    player_name: str = Field(description="Player name (partial match supported)")
    season: str = Field(default="2024-2025", description="Season in YYYY-YYYY format")
    team: Optional[str] = Field(None, description="Filter by team abbreviation")
    stat_type: Literal["basic", "advanced", "all"] = Field(
        default="all",
        description="Type of stats to return"
    )


class SearchPlayerStatsOutput(ToolResult):
    """Output schema for player stats search."""
    data: Dict[str, Any] = Field(description="Player stats and season profile")


# =============================================================================
# Tool 4: analyze_matchup (Game Analysis)
# =============================================================================

class AnalyzeMatchupInput(BaseModel):
    """Input schema for matchup analysis."""
    team_a: str = Field(description="First team abbreviation")
    team_b: str = Field(description="Second team abbreviation")
    season: str = Field(default="2024-2025")
    include_history: bool = Field(default=True, description="Include historical matchup data")


class AnalyzeMatchupOutput(ToolResult):
    """Output schema for matchup analysis."""
    data: Dict[str, Any] = Field(description="Matchup statistics and predictions")


# =============================================================================
# Tool 5: market_data_query (Contracts & Cap)
# =============================================================================

class MarketDataQueryInput(BaseModel):
    """Input schema for market data queries."""
    query_type: Literal["player_contract", "team_cap", "expiring_contracts", "comparable_contracts"]
    player_name: Optional[str] = None
    team: Optional[str] = None
    season: str = Field(default="2024-2025")
    filters: Optional[Dict[str, Any]] = None


class MarketDataQueryOutput(ToolResult):
    """Output schema for market data queries."""
    data: Dict[str, Any] = Field(description="Contract and cap space information")


# =============================================================================
# Tool 6: search_transactions (Transaction History)
# =============================================================================

class SearchTransactionsInput(BaseModel):
    """Input schema for transaction search."""
    player_name: Optional[str] = None
    team: Optional[str] = None
    transaction_type: Optional[Literal["trade", "signing", "waiver", "loan", "recall", "release"]] = None
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    limit: int = Field(default=10, ge=1, le=50)


class SearchTransactionsOutput(ToolResult):
    """Output schema for transaction search."""
    data: List[Dict[str, Any]] = Field(description="List of transaction objects")


# =============================================================================
# Tool 7: lookup_cba_rule (CBA Rules)
# =============================================================================

class CBALookupInput(BaseModel):
    """Input for CBA rule lookup."""
    query: str = Field(description="Rule query, e.g., 'cap ceiling', 'waiver eligibility'")
    as_of_date: Optional[str] = Field(
        default=None, description="Point-in-time date YYYY-MM-DD. Defaults to today for current rules."
    )


class CBALookupOutput(ToolResult):
    """Output for CBA rule lookup."""
    data: Dict[str, Any] = Field(description="{rules: [...], category, as_of_date, sql}")


# =============================================================================
# Tool 8: simulate_roster_scenario (Dynamic Layer MVP)
# =============================================================================

class SimulateRosterScenarioInput(BaseModel):
    """Input for roster scenario simulation."""
    team: str = Field(description="Team abbreviation (e.g., 'MTL')")
    actions: List[Dict[str, Any]] = Field(
        description=(
            "List of actions. Each action has 'type' (add_player|remove_player|call_up|send_down|place_ir|place_ltir) "
            "and one of 'player_id' or 'player_name'."
        )
    )
    as_of_date: Optional[str] = Field(default=None, description="Point-in-time date YYYY-MM-DD for deadline checks")


class SimulateRosterScenarioOutput(ToolResult):
    """Output for roster scenario simulation."""
    data: Dict[str, Any] = Field(description="Before/after metrics, cap rules, and any violations")


# =============================================================================
# Tool 9: evaluate_acquisition (What-if acquisition helper)
# =============================================================================

class EvaluateAcquisitionInput(BaseModel):
    team: str = Field(description="Team abbreviation (e.g., 'MTL')")
    candidate_name: str = Field(description="Player name to acquire (partial supported)")
    as_of_date: Optional[str] = Field(default=None, description="Point-in-time date YYYY-MM-DD")


class EvaluateAcquisitionOutput(ToolResult):
    data: Dict[str, Any] = Field(description="Cap impact and recommended moves to stay compliant")


# =============================================================================
# Tool Registry
# =============================================================================

class ToolSpec(BaseModel):
    """Specification for a single tool."""
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    function_path: str  # Python import path to function
    examples: List[Dict[str, Any]] = Field(default_factory=list)


class HeartBeatToolRegistry:
    """
    Central registry of all tools available to the LLM.
    
    Tools are the "Kinetic Layer" - they execute actions and return
    ontology objects that the LLM can reason over.
    """
    
    def __init__(self):
        self.tools = self._register_tools()
        logger.info(f"Tool registry initialized with {len(self.tools)} tools")
    
    def _register_tools(self) -> Dict[str, ToolSpec]:
        """Register all available tools."""
        
        return {
            "retrieve_objects": ToolSpec(
                name="retrieve_objects",
                description=(
                    "Semantic search and retrieval of hockey objects (Players, Teams, Games, Contracts, etc.). "
                    "Returns typed objects with relationships expanded. Use this as your primary information "
                    "retrieval tool - it understands the hockey ontology and returns structured data."
                ),
                input_schema=RetrieveObjectsInput,
                output_schema=RetrieveObjectsOutput,
                function_path="orchestrator.tools.ontology_retriever.retrieve_hockey_context",
                examples=[
                    {
                        "input": {"query": "Cole Caufield stats", "top_k": 1},
                        "description": "Find player and season profile"
                    },
                    {
                        "input": {"query": "Montreal Canadiens roster", "filters": {"object_type": "Player", "team": "MTL"}},
                        "description": "Get current team roster"
                    },
                    {
                        "input": {"query": "recent games Maple Leafs", "filters": {"object_type": "Game"}, "top_k": 5},
                        "description": "Find recent games for a team"
                    }
                ]
            ),

            "lookup_cba_rule": ToolSpec(
                name="lookup_cba_rule",
                description=(
                    "Lookup NHL CBA structured rules (salary cap, waivers, roster limits, bonuses, etc.). "
                    "Supports point-in-time queries via as_of_date. Returns rules with temporal fields."
                ),
                input_schema=CBALookupInput,
                output_schema=CBALookupOutput,
                function_path="orchestrator.tools.cba_tool.lookup_cba_rule",
                examples=[
                    {"input": {"query": "cap ceiling"}, "description": "Get current salary cap ceiling"},
                    {"input": {"query": "waiver eligibility"}, "description": "Waiver eligibility thresholds"},
                    {"input": {"query": "cap ceiling", "as_of_date": "2022-01-15"}, "description": "Historical cap"}
                ]
            ),

            "simulate_roster_scenario": ToolSpec(
                name="simulate_roster_scenario",
                description=(
                    "Simulate roster/cap scenarios by applying actions (add/remove/call-up/send-down/IR). "
                    "Returns before/after metrics and CBA compliance flags."
                ),
                input_schema=SimulateRosterScenarioInput,
                output_schema=SimulateRosterScenarioOutput,
                function_path="orchestrator.tools.scenario_engine.simulate_roster_scenario",
                examples=[
                    {
                        "input": {
                            "team": "MTL",
                            "actions": [
                                {"type": "call_up", "player_name": "Joshua Roy"},
                                {"type": "place_ir", "player_name": "Sean Monahan"}
                            ]
                        },
                        "description": "What-if roster adjustment with call-up and IR move"
                    }
                ]
            ),

            "evaluate_acquisition": ToolSpec(
                name="evaluate_acquisition",
                description=(
                    "Evaluate acquiring a player: returns cap impact and suggested balancing moves "
                    "to stay compliant with CBA rules (ceiling/floor/roster size)."
                ),
                input_schema=EvaluateAcquisitionInput,
                output_schema=EvaluateAcquisitionOutput,
                function_path="orchestrator.tools.scenario_engine.evaluate_acquisition",
                examples=[
                    {
                        "input": {"team": "MTL", "candidate_name": "Patrik Laine"},
                        "description": "Can we acquire Laine and stay under the cap?"
                    }
                ]
            ),
            
            "clip_retriever": ToolSpec(
                name="clip_retriever",
                description=(
                    "Search and retrieve video clips of game highlights. Returns clip objects with "
                    "video URLs, thumbnails, and metadata."
                ),
                input_schema=ClipRetrieverInput,
                output_schema=ClipRetrieverOutput,
                function_path="orchestrator.nodes.clip_retriever.search_clips",
                examples=[
                    {
                        "input": {"query": "Ovechkin goal", "limit": 3},
                        "description": "Find recent Ovechkin goals"
                    }
                ]
            ),
            
            "search_player_stats": ToolSpec(
                name="search_player_stats",
                description=(
                    "Search for player statistics (basic and advanced). Returns season profiles with "
                    "goals, assists, xG, Corsi, and other metrics."
                ),
                input_schema=SearchPlayerStatsInput,
                output_schema=SearchPlayerStatsOutput,
                function_path="orchestrator.nodes.parquet_analyzer.get_player_stats",
                examples=[
                    {
                        "input": {"player_name": "Matthews", "season": "2024-2025"},
                        "description": "Get Matthews current season stats"
                    }
                ]
            ),
            
            "analyze_matchup": ToolSpec(
                name="analyze_matchup",
                description=(
                    "Analyze head-to-head matchup between two teams. Returns historical results, "
                    "current season matchups, and key statistics."
                ),
                input_schema=AnalyzeMatchupInput,
                output_schema=AnalyzeMatchupOutput,
                function_path="orchestrator.nodes.parquet_analyzer.analyze_matchup",
                examples=[
                    {
                        "input": {"team_a": "MTL", "team_b": "TOR", "season": "2024-2025"},
                        "description": "Analyze Canadiens vs Maple Leafs matchup"
                    }
                ]
            ),
            
            "market_data_query": ToolSpec(
                name="market_data_query",
                description=(
                    "Query contract and cap space information. Get player contracts, team cap situations, "
                    "expiring contracts, and comparable deals."
                ),
                input_schema=MarketDataQueryInput,
                output_schema=MarketDataQueryOutput,
                function_path="orchestrator.tools.market_data_client.query_market_data",
                examples=[
                    {
                        "input": {"query_type": "player_contract", "player_name": "Matthews"},
                        "description": "Get Matthews contract details"
                    },
                    {
                        "input": {"query_type": "team_cap", "team": "MTL", "season": "2024-2025"},
                        "description": "Get Canadiens cap space"
                    }
                ]
            ),
            
            "search_transactions": ToolSpec(
                name="search_transactions",
                description=(
                    "Search player movement transactions (trades, signings, waivers, etc.). "
                    "Returns transaction history with details."
                ),
                input_schema=SearchTransactionsInput,
                output_schema=SearchTransactionsOutput,
                function_path="orchestrator.tools.transaction_search.search_transactions",
                examples=[
                    {
                        "input": {"player_name": "Dubois", "limit": 5},
                        "description": "Get recent Dubois transactions"
                    },
                    {
                        "input": {"team": "MTL", "transaction_type": "trade", "limit": 10},
                        "description": "Get recent Canadiens trades"
                    }
                ]
            )
        }
    
    def get_tool(self, name: str) -> Optional[ToolSpec]:
        """Get tool specification by name."""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[ToolSpec]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_tool_schemas_for_llm(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas in OpenAI function calling format.
        
        Returns list of tool definitions suitable for LLM providers
        (OpenRouter, OpenAI, Anthropic, etc.)
        """
        
        schemas = []
        
        for tool_spec in self.tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool_spec.name,
                    "description": tool_spec.description,
                    "parameters": tool_spec.input_schema.model_json_schema()
                }
            }
            schemas.append(schema)
        
        return schemas
    
    def validate_tool_input(self, tool_name: str, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate tool input against schema."""
        
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"Unknown tool: {tool_name}"
        
        try:
            tool.input_schema(**input_data)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_tool_documentation(self) -> str:
        """Generate markdown documentation for all tools."""
        
        docs = ["# HeartBeat Engine - Available Tools\n"]
        docs.append("Tools available for LLM function calling (Kinetic Layer)\n")
        
        for tool_spec in self.tools.values():
            docs.append(f"\n## {tool_spec.name}\n")
            docs.append(f"{tool_spec.description}\n")
            
            docs.append("\n### Input Schema\n")
            docs.append(f"```json\n{tool_spec.input_schema.model_json_schema()}\n```\n")
            
            if tool_spec.examples:
                docs.append("\n### Examples\n")
                for ex in tool_spec.examples:
                    docs.append(f"- {ex['description']}\n")
                    docs.append(f"  ```json\n  {ex['input']}\n  ```\n")
        
        return "".join(docs)


# Global registry instance
tool_registry = HeartBeatToolRegistry()
