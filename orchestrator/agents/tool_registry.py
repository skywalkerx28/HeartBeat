"""
Tool Registry: Declarative per-tool dependency metadata and planning utilities.

Defines a compact, extensible specification for each tool the model can call,
including what data it consumes/produces and whether it is safe to run in
parallel. The orchestrator uses this registry to derive an execution plan
and schedule tools deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, List, Tuple, Any, Optional


@dataclass(frozen=True)
class ToolSpec:
    name: str
    consumes: Set[str] = field(default_factory=set)
    produces: Set[str] = field(default_factory=set)
    parallel_ok: bool = True
    resource_group: str = "default"
    timeout_s: Optional[int] = None
    side_effects: bool = False


# Canonical data tags
# - Use broad tags that capture data categories. Tools may consume multiple.
# - Keep minimal to avoid over-constraining the scheduler.
TAG_CONTEXT = "context"
TAG_TABULAR = "tabular_data"
TAG_ADV_METRICS = "advanced_metrics"
TAG_VISUAL = "visualization"
TAG_ROSTER = "roster"
TAG_PLAYER_CANDIDATES = "player_candidates"
TAG_PLAYER_BY_NUMBER = "player_by_number"
TAG_PLAYERS_BY_NUMBER = "players_by_number"
TAG_SCHEDULE = "schedule"
TAG_LIVE = "live_data"
TAG_LIVE_SCOREBOARD = "live_scoreboard"
TAG_LIVE_BOXSCORE = "live_boxscore"
TAG_LIVE_PBP = "live_play_by_play"
TAG_LIVE_AGG = "live_aggregate"
TAG_LIVE_ANALYTICS = "live_analytics"
TAG_CONTRACT_DATA = "contract_data"
TAG_CAP_DATA = "cap_data"
TAG_MARKET_DATA = "market_data"
TAG_TRADE_DATA = "trade_data"
TAG_CLIPS = "clips"


# Registry of available tools with dependency metadata
REGISTRY: Dict[str, ToolSpec] = {
    # Knowledge search (independent)
    "search_hockey_knowledge": ToolSpec(
        name="search_hockey_knowledge",
        consumes=set(),
        produces={TAG_CONTEXT},
        parallel_ok=True,
        resource_group="vertex",
        timeout_s=10,
    ),
    # Video clip retrieval (local metrics + media)
    "retrieve_video_clips": ToolSpec(
        name="retrieve_video_clips",
        consumes=set(),
        produces={TAG_CLIPS},
        parallel_ok=False,  # performs cutting and indexing; serialize per turn
        resource_group="media",
        timeout_s=60,
        side_effects=True,
    ),

    # Historical data query (independent)
    "query_game_data": ToolSpec(
        name="query_game_data",
        consumes=set(),
        produces={TAG_TABULAR},
        parallel_ok=True,
        resource_group="parquet",
        timeout_s=15,
    ),

    # Advanced calculations (depends on tabular data)
    "calculate_hockey_metrics": ToolSpec(
        name="calculate_hockey_metrics",
        consumes={TAG_TABULAR},
        produces={TAG_ADV_METRICS},
        parallel_ok=False,
        resource_group="cpu",
        timeout_s=15,
    ),

    # Visualization (depends on advanced metrics or tabular data)
    "generate_visualization": ToolSpec(
        name="generate_visualization",
        consumes={TAG_ADV_METRICS, TAG_TABULAR},
        produces={TAG_VISUAL},
        parallel_ok=False,
        resource_group="viz",
        timeout_s=20,
    ),

    # Rosters and players
    "get_team_roster": ToolSpec(
        name="get_team_roster",
        consumes=set(),
        produces={TAG_ROSTER},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=15,
    ),
    "search_player_info": ToolSpec(
        name="search_player_info",
        consumes=set(),
        produces={TAG_PLAYER_CANDIDATES},
        parallel_ok=True,
        resource_group="vertex",
        timeout_s=15,
    ),
    # Direct jersey-by-team lookup does not require prior roster fetch; it can call API itself
    "find_player_by_team_and_number": ToolSpec(
        name="find_player_by_team_and_number",
        consumes=set(),
        produces={TAG_PLAYER_BY_NUMBER},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=15,
    ),
    "find_players_by_number": ToolSpec(
        name="find_players_by_number",
        consumes=set(),
        produces={TAG_PLAYERS_BY_NUMBER},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=20,
    ),

    # Schedule / Live
    "get_schedule": ToolSpec(
        name="get_schedule",
        consumes=set(),
        produces={TAG_SCHEDULE},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=15,
    ),
    "get_live_game_data": ToolSpec(
        name="get_live_game_data",
        consumes=set(),
        produces={TAG_LIVE},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=10,
    ),
    # New live tools
    "get_live_scoreboard": ToolSpec(
        name="get_live_scoreboard",
        consumes=set(),
        produces={TAG_LIVE_SCOREBOARD},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=10,
    ),
    "get_live_boxscore": ToolSpec(
        name="get_live_boxscore",
        consumes=set(),
        produces={TAG_LIVE_BOXSCORE},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=15,
    ),
    "get_live_play_by_play": ToolSpec(
        name="get_live_play_by_play",
        consumes=set(),
        produces={TAG_LIVE_PBP},
        parallel_ok=True,
        resource_group="nhl_api",
        timeout_s=15,
    ),
    # Compute live analytics after we have live inputs
    "compute_live_analytics": ToolSpec(
        name="compute_live_analytics",
        consumes={TAG_LIVE_BOXSCORE, TAG_LIVE_PBP},
        produces={TAG_ADV_METRICS, TAG_LIVE_ANALYTICS},
        parallel_ok=False,
        resource_group="cpu",
        timeout_s=20,
    ),
    
    # Market Analytics Tools
    "get_player_contract": ToolSpec(
        name="get_player_contract",
        consumes=set(),
        produces={TAG_CONTRACT_DATA},
        parallel_ok=True,
        resource_group="market_data",
        timeout_s=15,
    ),
    "get_team_cap_analysis": ToolSpec(
        name="get_team_cap_analysis",
        consumes=set(),
        produces={TAG_CAP_DATA, TAG_CONTRACT_DATA},
        parallel_ok=True,
        resource_group="market_data",
        timeout_s=15,
    ),
    "find_contract_comparables": ToolSpec(
        name="find_contract_comparables",
        consumes={TAG_CONTRACT_DATA},
        produces={TAG_MARKET_DATA},
        parallel_ok=False,
        resource_group="market_data",
        timeout_s=20,
    ),
    "get_recent_trades": ToolSpec(
        name="get_recent_trades",
        consumes=set(),
        produces={TAG_TRADE_DATA},
        parallel_ok=True,
        resource_group="market_data",
        timeout_s=15,
    ),
    "get_league_market_overview": ToolSpec(
        name="get_league_market_overview",
        consumes=set(),
        produces={TAG_MARKET_DATA},
        parallel_ok=True,
        resource_group="market_data",
        timeout_s=15,
    ),
}


def get_tool_spec(name: str) -> ToolSpec:
    """Return the ToolSpec for a given tool name, with a permissive default."""
    if name in REGISTRY:
        return REGISTRY[name]
    # Default: independent, parallel-ok, no specific data contracts
    return ToolSpec(name=name)


def _topo_sort_with_levels(
    nodes: List[int],
    edges_out: Dict[int, Set[int]],
    edges_in: Dict[int, Set[int]],
) -> Optional[List[List[int]]]:
    """Kahn's algorithm variant returning execution levels (batches).

    Returns None if a cycle is detected.
    """
    in_deg = {n: len(edges_in.get(n, set())) for n in nodes}
    level: List[int] = [n for n in nodes if in_deg[n] == 0]
    batches: List[List[int]] = []

    remaining = set(nodes)
    while level:
        batches.append(list(level))
        next_level: List[int] = []
        for n in level:
            remaining.discard(n)
            for m in edges_out.get(n, set()):
                in_deg[m] -= 1
                if in_deg[m] == 0:
                    next_level.append(m)
        level = next_level

    if remaining:
        return None  # cycle detected
    return batches


def build_execution_plan(
    function_calls: List[Any],
    state: Any,
) -> List[List[Tuple[int, str, Dict[str, Any], ToolSpec]]]:
    """Build a DAG-based execution plan as batches of (idx, name, args, spec).

    Dependency rule:
    - If a tool consumes a tag that is produced by another tool in this same
      turn, add an edge producer -> consumer.
    - If a tool consumes a tag already available from prior state results,
      do NOT add an edge (dependency satisfied).
    - Unknown tools are treated as independent and parallel-safe by default.
    """
    if not function_calls:
        return []

    # Determine which data tags are already satisfied by prior state results
    satisfied: Set[str] = set()
    try:
        for tr in state.get("tool_results", []) or []:
            data = getattr(tr, "data", None)
            if not data:
                continue
            # Rough mapping: infer tags from known keys to seed satisfied set
            if isinstance(data, dict):
                keys = set(data.keys())
                if any(k in keys for k in ("games", "analytics_data", "results", "opponent", "season")):
                    satisfied.add(TAG_TABULAR)
                if any(k in keys for k in ("advanced", "advanced_metrics")):
                    satisfied.add(TAG_ADV_METRICS)
                if any(k in keys for k in ("chart_spec", "vegaLite")):
                    satisfied.add(TAG_VISUAL)
                if any(k in keys for k in ("roster",)):
                    satisfied.add(TAG_ROSTER)
                if any(k in keys for k in ("results", "found")):
                    satisfied.add(TAG_PLAYER_CANDIDATES)
                if any(k in keys for k in ("schedule", "games", "per_date")):
                    satisfied.add(TAG_SCHEDULE)
    except Exception:
        pass

    # Build nodes and dependency edges amongst this turn's calls
    nodes: List[int] = list(range(len(function_calls)))
    specs: Dict[int, ToolSpec] = {}
    names: Dict[int, str] = {}
    args_map: Dict[int, Dict[str, Any]] = {}
    produces_by_idx: Dict[int, Set[str]] = {}

    for i, fc in enumerate(function_calls):
        name = getattr(fc, 'name', '')
        args = dict(getattr(fc, 'args', {})) if hasattr(fc, 'args') else {}
        spec = get_tool_spec(name)
        specs[i] = spec
        names[i] = name
        args_map[i] = args
        produces_by_idx[i] = set(spec.produces)

    edges_in: Dict[int, Set[int]] = {i: set() for i in nodes}
    edges_out: Dict[int, Set[int]] = {i: set() for i in nodes}

    # For each consumer, if it consumes a tag produced by another tool in this turn, add dependency edge
    for i in nodes:
        cons = specs[i].consumes
        if not cons:
            continue
        # If any consume tag is already satisfied from prior state, skip those tags
        needed = cons - satisfied
        if not needed:
            continue
        for j in nodes:
            if j == i:
                continue
            prod = produces_by_idx.get(j, set())
            if prod & needed:
                edges_in[i].add(j)
                edges_out[j].add(i)

    batches_idx = _topo_sort_with_levels(nodes, edges_out, edges_in)
    if batches_idx is None:
        # Cycle or error: fallback to sequential in original order
        return [[(i, names[i], args_map[i], specs[i])] for i in nodes]

    # Convert index batches to detailed batches
    plan: List[List[Tuple[int, str, Dict[str, Any], ToolSpec]]] = []
    for b in batches_idx:
        plan.append([(i, names[i], args_map[i], specs[i]) for i in b])
    return plan


# ---------------- Affordance Scoring (Step 1) ----------------
def score_affordances(query: str, state: Any | None = None) -> List[Tuple[str, float, Dict[str, Any]]]:
    """Heuristic tool affordance scoring for soft routing and hints.

    Returns list of (tool_name, score [0-1], suggested_args) sorted desc.
    """
    q = (query or "").lower()
    scores: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def bump(name: str, val: float, **kwargs):
        cur = scores.get(name, (0.0, {}))
        s = min(1.0, cur[0] + val)
        args = {**cur[1], **kwargs}
        scores[name] = (s, args)

    # Video intent
    if any(t in q for t in ["clip", "clips", "video", "shift", "shifts", "highlight", "ozone", "o-zone", "offensive zone"]):
        bump("retrieve_video_clips", 0.9)
        # Ozone defaults to zone entries as a useful first pass
        if any(t in q for t in ["ozone", "o-zone", "offensive zone"]):
            bump("retrieve_video_clips", 0.05, event_types=["zone_entry"])  # nudge

    # Live intent
    if any(t in q for t in ["today", "now", "live", "currently", "right now"]):
        bump("get_live_game_data", 0.7)
        bump("get_live_scoreboard", 0.5)

    # Roster / player identity
    if any(t in q for t in ["roster", "lineup", "who", "which team", "what team", "jersey", "number"]):
        bump("search_player_info", 0.6)
        bump("get_team_roster", 0.4)

    # Market analytics
    if any(t in q for t in ["contract", "cap", "salary", "cap space", "comparable", "ntc", "nmc"]):
        bump("get_player_contract", 0.6)
        bump("get_team_cap_analysis", 0.5)

    # Generic fallback
    if not scores:
        bump("search_hockey_knowledge", 0.4)

    # Return top 5
    ordered = sorted(scores.items(), key=lambda kv: kv[1][0], reverse=True)[:5]
    return [(name, sc, args) for name, (sc, args) in ordered]
