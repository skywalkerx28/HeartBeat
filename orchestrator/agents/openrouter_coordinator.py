"""
HeartBeat Engine - OpenRouter Coordinator (Planner-Executor)

Provider-agnostic planning loop that:
1) Asks the model to return STRICT JSON specifying the next tool and args
2) Executes the requested tool via existing nodes
3) Repeats until no more tools are requested or sufficient data gathered
4) Synthesizes final response using the selected model
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime

from orchestrator.utils.state import AgentState, ToolType, ToolResult, create_initial_state
from orchestrator.nodes.vector_retriever import VectorRetrieverNode
from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode
from orchestrator.nodes.clip_retriever_enhanced import EnhancedClipRetrieverNode
from orchestrator.tools.nhl_roster_client import NHLRosterClient, NHLLiveGameClient
from orchestrator.providers.openrouter_provider import OpenRouterProvider
from orchestrator.nodes.intent_analyzer import IntentAnalyzerNode
from orchestrator.tools.market_data_client import MarketDataClient
from orchestrator.config.settings import settings
import os
from orchestrator.config.prompts import SYNTHESIS_SYSTEM_PROMPT, planner_system_prompt, get_synthesis_system_prompt, build_neutral_synthesis_prompt

logger = logging.getLogger(__name__)


class OpenRouterCoordinator:
    """Planner-executor orchestration using OpenRouter-selected models."""

    def __init__(self, provider: OpenRouterProvider, model_slug: str, generation: Dict[str, Any]) -> None:
        self.provider = provider
        self.model_slug = model_slug
        self.gen = generation or {}
        self.temperature = float(self.gen.get("temperature", 0.2))
        self.max_tokens = int(self.gen.get("max_tokens", 2048))
        self.top_p = float(self.gen.get("top_p", 0.95))

        # Nodes
        self.rag_node = VectorRetrieverNode()
        self.parquet_node = ParquetAnalyzerNode()
        self.intent_node = IntentAnalyzerNode()
        self.clip_node = EnhancedClipRetrieverNode()
        self.roster_client = NHLRosterClient()
        self.live_client = NHLLiveGameClient()

    async def process_query(self, query: str, user_context, mode: Optional[str] = None, prior_messages: Optional[List[Dict[str, Any]]] = None) -> AgentState:
        """Run planning loop and synthesize the final response."""
        state = create_initial_state(user_context=user_context, query=query)
        if mode:
            # Persist chat mode for prompts/planning
            try:
                state["chat_mode"] = mode
            except Exception:
                pass
        if prior_messages:
            # Attach conversation history for context-aware planning/synthesis
            state["prior_messages"] = prior_messages
        # Initial intent analysis
        state = self.intent_node.process(state)

        # Tool loop (bounded). For report mode, run external research in parallel with internal tool loop.
        max_iters = 5
        iters = 0

        # Spawn external research task if report mode and model supports deep research
        research_task = None
        try:
            if (state.get("chat_mode") or "").lower() == "report" and "deep-research" in (self.model_slug or ""):
                import asyncio
                research_task = asyncio.create_task(self._run_external_research(query))
        except Exception:
            research_task = None

        while iters < max_iters:
            iters += 1
            plan = await self._plan_next_tool(state)
            if not plan:
                break
            tool = str(plan.get("next_tool") or "").lower()
            args = plan.get("args") or {}
            if tool in ("", "none", "null"):
                break
            result = await self._execute(tool, args, state)
            if isinstance(result, ToolResult):
                state["tool_results"].append(result)
            if self._has_sufficient_data(state):
                break

        # If external research is running, collect it with timeout
        try:
            if research_task is not None:
                import asyncio
                research = await asyncio.wait_for(research_task, timeout=25.0)
                if isinstance(research, dict):
                    # Attach as separate tool result for synthesis pooling
                    state["tool_results"].append(ToolResult(
                        tool_type=ToolType.VECTOR_SEARCH,
                        success=True,
                        data={"tool": "external_research", **research},
                        execution_time_ms=0,
                        citations=[src.get("url") for src in research.get("sources", []) if isinstance(src, dict) and src.get("url")]
                    ))
        except Exception:
            pass

        # Synthesis
        final_text = await self._synthesize(state)
        state["final_response"] = final_text
        return state

    async def _plan_next_tool(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """Ask model to reply with STRICT JSON {next_tool, args}."""
        tool_names = [
            "vector_search",
            "retrieve_objects",
            "parquet_query",
            "calculate_metrics",
            "get_team_roster",
            "find_players_by_number",
            "find_player_by_team_and_number",
            "get_schedule",
            "get_recent_games",
            "get_live_game_data",
            "get_live_scoreboard",
            "get_live_boxscore",
            "get_live_play_by_play",
            "retrieve_video_clips",
            "clip_retrieval",
            "generate_visualization",
            # Market analytics tools
            "get_player_contract",
            "get_team_cap_analysis",
            "find_contract_comparables",
            "get_recent_trades",
            "get_league_market_overview",
        ]
        data_brief = self._data_brief(state)
        system_prompt = planner_system_prompt(tool_names)
        user_prompt = (
            f"Question: {state['original_query']}\n\n"
            f"Data available: {data_brief}\n\n"
            "Return JSON like: {\"next_tool\": \"parquet_query\", \"args\": {\"sql\": \"...\"}} or {\"next_tool\": null, \"args\": {}}"
        )
        # For report mode, bias planner to gather internal data first.
        try:
            if (state.get("chat_mode") or "").lower() == "report":
                user_prompt += (
                    "\n\nMODE: report — Always gather INTERNAL data first: call vector_search and parquet_query to build a full picture. "
                    "Your model may use web search independently (deep-research); combine its findings with internal results during synthesis."
                )
        except Exception:
            pass
        try:
            resp = await self.provider.generate(
                model=self.model_slug,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=256,
                top_p=0.95,
            )
            text = (resp.get("text") or "").strip()
            plan = self._safe_json(text)
            if isinstance(plan, dict):
                return plan
            # One retry with even stricter instruction
            strict_system = system_prompt + " STRICT JSON ONLY."
            resp2 = await self.provider.generate(
                model=self.model_slug,
                system_prompt=strict_system,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=128,
                top_p=1.0,
            )
            text2 = (resp2.get("text") or "").strip()
            plan2 = self._safe_json(text2)
            if isinstance(plan2, dict):
                return plan2
        except Exception as e:
            logger.warning(f"Planning failed: {e}")
        return None

    async def _execute(self, tool: str, args: Dict[str, Any], state: AgentState) -> ToolResult:
        start = datetime.now()
        try:
            tool_l = tool.lower()
            if tool_l == "vector_search":
                updated = await self.rag_node.process(state)
                return updated["tool_results"][-1] if updated.get("tool_results") else ToolResult(
                    tool_type=ToolType.VECTOR_SEARCH, success=True, data={}, execution_time_ms=0
                )
            if tool_l in ("parquet_query", "calculate_metrics"):
                # ParquetAnalyzerNode encapsulates multiple analysis types
                updated = await self.parquet_node.process(state)
                return updated["tool_results"][-1] if updated.get("tool_results") else ToolResult(
                    tool_type=ToolType.PARQUET_QUERY, success=True, data={}, execution_time_ms=0
                )
            if tool_l in ("retrieve_video_clips", "clip_retrieval"):
                updated = await self.clip_node(state)
                # Extract clips block
                clips_block = None
                try:
                    for a in updated.get("analytics", []):
                        if isinstance(a, dict) and a.get("type") == "clips":
                            clips_block = a
                            break
                except Exception:
                    clips_block = None
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.CLIP_RETRIEVAL,
                    success=bool(clips_block and clips_block.get("clips")),
                    data={"tool": "clip_retrieval", **(clips_block or {"clips": []})},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "get_team_roster":
                team = args.get("team") or (state.get("user_context").team_access[0] if state.get("user_context") and getattr(state.get("user_context"), "team_access", None) else None)
                season = args.get("season") or "current"
                roster = await self.roster_client.get_team_roster(team=team, season=season)
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.TEAM_ROSTER,
                    success=True,
                    data={"tool": "get_team_roster", "team": team, "season": season, "players": roster.get("players", []), "source": roster.get("source")},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "find_players_by_number":
                number = args.get("number")
                season = args.get("season") or "current"
                teams = [
                    "ANA","BOS","BUF","CGY","CAR","CHI","COL","CBJ","DAL","DET","EDM","FLA",
                    "LAK","MIN","MTL","NSH","NJD","NYI","NYR","OTT","PHI","PIT","SJS","SEA","STL",
                    "TBL","TOR","UTA","VAN","VGK","WPG","WSH"
                ]
                rosters = await self.roster_client.get_all_rosters(teams, season=season, scope="active", max_concurrency=8)
                matches: List[Dict[str, Any]] = []
                for team_abbr, payload in rosters.items():
                    players = payload.get("players", []) if isinstance(payload, dict) else []
                    for p in players:
                        sw = p.get("sweater")
                        try:
                            if sw is not None and number is not None and int(sw) == int(number):
                                matches.append({
                                    "full_name": p.get("full_name"),
                                    "team_abbrev": p.get("team_abbrev") or team_abbr,
                                    "position": p.get("position"),
                                    "sweater": int(sw)
                                })
                        except Exception:
                            continue
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.TEAM_ROSTER,
                    success=True,
                    data={"tool": "find_players_by_number", "number": number, "season": season, "players": matches},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "get_schedule":
                date = args.get("date")
                days = int(args.get("days") or 0)
                team = args.get("team")
                schedule = await self.live_client.get_todays_games(date)
                games = schedule.get("games", []) if isinstance(schedule, dict) else []
                if team:
                    t = team.upper()
                    filtered = []
                    for g in games:
                        try:
                            home = (g.get("homeTeam", {}) or {}).get("abbrev")
                            away = (g.get("awayTeam", {}) or {}).get("abbrev")
                            if home == t or away == t:
                                filtered.append(g)
                        except Exception:
                            continue
                    games = filtered
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.LIVE_GAME_DATA,
                    success=True,
                    data={"tool": "get_schedule", "date": date, "days": days, "team": team, "games": games, "telemetry": {"source": "nhl_api"}},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "get_recent_games":
                team = args.get("team")
                limit = int(args.get("limit") or 5)
                max_days_back = int(args.get("max_days_back") or 30)
                result = await self.live_client.get_recent_games(team=team, limit=limit, max_days_back=max_days_back)
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.LIVE_GAME_DATA,
                    success=result.get("success", False),
                    data={"tool": "get_recent_games", **result},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "get_live_game_data":
                game_id = args.get("game_id")
                team = args.get("team")
                date = args.get("date")
                tz = None
                try:
                    uc = state.get("user_context")
                    if uc and getattr(uc, "preferences", None):
                        tz = uc.preferences.get("timezone")
                except Exception:
                    tz = None
                payload = await self.live_client.get_game_data(game_id=game_id, team=team, date=date, tz_name=tz)
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.LIVE_GAME_DATA,
                    success=True,
                    data={"tool": "get_live_game_data", **payload},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l in ("retrieve_objects", "ontology_retrieval"):
                q = args.get("query") or state.get("original_query")
                filters = args.get("filters") or {}
                top_k = int(args.get("top_k") or 5)
                expand = bool(args.get("expand_relationships", True))
                try:
                    from orchestrator.tools.ontology_retriever import OntologyRetriever
                    retriever = OntologyRetriever(
                        project_id=os.getenv("GCP_PROJECT", "heartbeat-474020"),
                        dataset="raw",
                    )
                    context_pack = await retriever.retrieve_objects(q, filters=filters, top_k=top_k, expand_relationships=expand)
                    execution_time = int((datetime.now() - start).total_seconds() * 1000)
                    return ToolResult(
                        tool_type=ToolType.VECTOR_SEARCH,
                        success=True,
                        data={"tool": "retrieve_objects", **context_pack.to_dict()},
                        execution_time_ms=execution_time,
                        citations=[],
                    )
                except Exception as e:
                    execution_time = int((datetime.now() - start).total_seconds() * 1000)
                    return ToolResult(
                        tool_type=ToolType.VECTOR_SEARCH,
                        success=False,
                        error=str(e),
                        execution_time_ms=execution_time,
                        citations=[],
                    )
            # ---------------- Market Analytics ----------------
            if tool_l in ("get_player_contract", "get_team_cap_analysis", "find_contract_comparables", "get_recent_trades", "get_league_market_overview"):
                # Initialize client (prefer parquet fallback; BigQuery optional)
                try:
                    from google.cloud import bigquery  # type: ignore
                    bq_client = bigquery.Client(project=os.getenv("GCP_PROJECT") or "")
                except Exception:
                    bq_client = None  # type: ignore
                market_client = MarketDataClient(
                    bigquery_client=bq_client,
                    parquet_fallback_path=str(getattr(settings, "parquet").data_directory)  # use processed root; client handles subpaths
                )
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                if tool_l == "get_player_contract":
                    data = await market_client.get_player_contract(
                        player_name=args.get("player_name"),
                        team=args.get("team"),
                        season=args.get("season") or "current",
                    )
                    return ToolResult(tool_type=ToolType.PARQUET_QUERY, success=True, data={"tool": tool_l, **(data or {})}, execution_time_ms=execution_time)
                if tool_l == "get_team_cap_analysis":
                    data = await market_client.get_team_cap_summary(
                        team=args.get("team"),
                        season=args.get("season") or "current",
                        include_projections=bool(args.get("include_projections", True)),
                    )
                    return ToolResult(tool_type=ToolType.PARQUET_QUERY, success=True, data={"tool": tool_l, **(data or {})}, execution_time_ms=execution_time)
                if tool_l == "find_contract_comparables":
                    # Optionally resolve player_id via contract endpoint first
                    player_name = args.get("player_name")
                    contract = await market_client.get_player_contract(player_name=player_name)
                    player_id = (contract or {}).get("nhl_player_id") or args.get("player_id")
                    data = await market_client.get_contract_comparables(
                        player_id=player_id,
                        position=args.get("position"),
                        limit=int(args.get("limit") or 10),
                    )
                    return ToolResult(tool_type=ToolType.PARQUET_QUERY, success=True, data={"tool": tool_l, "player": player_name, "player_id": player_id, "comparables": data or []}, execution_time_ms=execution_time)
                if tool_l == "get_recent_trades":
                    data = await market_client.get_recent_trades(
                        team=args.get("team"),
                        days_back=int(args.get("days_back") or 30),
                        include_cap_impact=True,
                    )
                    return ToolResult(tool_type=ToolType.PARQUET_QUERY, success=True, data={"tool": tool_l, "team": args.get("team"), "days_back": args.get("days_back"), "trades": data or []}, execution_time_ms=execution_time)
                if tool_l == "get_league_market_overview":
                    data = await market_client.get_league_market_summary(
                        position=args.get("position"),
                        season=args.get("season") or "current",
                    )
                    return ToolResult(tool_type=ToolType.PARQUET_QUERY, success=True, data={"tool": tool_l, **(data or {})}, execution_time_ms=execution_time)
            if tool_l == "get_live_scoreboard":
                date = args.get("date")
                scoreboard = await self.live_client.get_todays_games(date)
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.LIVE_GAME_DATA,
                    success=True,
                    data={"tool": "get_live_scoreboard", "date": date, "scoreboard": scoreboard},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "get_live_boxscore":
                game_id = args.get("game_id")
                box = await self.live_client.get_boxscore(int(game_id)) if game_id is not None else {"error": "missing game_id"}
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.LIVE_GAME_DATA,
                    success="error" not in box,
                    data={"tool": "get_live_boxscore", "game_id": game_id, "boxscore": box},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "get_live_play_by_play":
                game_id = args.get("game_id")
                pbp = await self.live_client.get_play_by_play(int(game_id)) if game_id is not None else {"error": "missing game_id"}
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.LIVE_GAME_DATA,
                    success="error" not in pbp,
                    data={"tool": "get_live_play_by_play", "game_id": game_id, "play_by_play": pbp},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "find_player_by_team_and_number":
                team = args.get("team")
                number = args.get("number")
                season = args.get("season") or "current"
                roster = await self.roster_client.get_team_roster(team=team, season=season)
                target = None
                try:
                    for p in roster.get("players", []) or []:
                        sw = p.get("sweater")
                        if sw is None:
                            continue
                        try:
                            if int(sw) == int(number):
                                target = {
                                    "full_name": p.get("full_name"),
                                    "team_abbrev": p.get("team_abbrev") or team,
                                    "position": p.get("position"),
                                    "sweater": int(sw),
                                    "nhl_player_id": p.get("nhl_player_id") or p.get("player_id")
                                }
                                break
                        except Exception:
                            continue
                except Exception:
                    target = None
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.TEAM_ROSTER,
                    success=target is not None,
                    data={"tool": "find_player_by_team_and_number", "team": team, "season": season, "number": number, "player": target},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            if tool_l == "generate_visualization":
                # Minimal placeholder: try to build a simple count chart from last tool
                last = None
                for tr in reversed(state.get("tool_results", [])):
                    if getattr(tr, "success", False) and isinstance(getattr(tr, "data", None), dict):
                        last = tr.data
                        break
                chart_spec = None
                try:
                    if last and last.get("tool") == "get_schedule":
                        games = last.get("games", []) or []
                        by_state = {}
                        for g in games:
                            s = (g.get("game_state") or g.get("gameState") or "UNKNOWN")
                            by_state[s] = by_state.get(s, 0) + 1
                        rows = [{"category": k, "value": v} for k, v in by_state.items()]
                        chart_spec = {"kind": "bar", "xKey": "category", "yKey": "value", "rows": rows}
                except Exception:
                    chart_spec = None
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                return ToolResult(
                    tool_type=ToolType.VISUALIZATION,
                    success=chart_spec is not None,
                    data={"tool": "generate_visualization", "chart_spec": chart_spec},
                    execution_time_ms=execution_time,
                    citations=[]
                )
            # Unknown tool: no-op result
            elapsed = int((datetime.now() - start).total_seconds() * 1000)
            return ToolResult(tool_type=ToolType.VECTOR_SEARCH, success=False, error=f"Unknown tool: {tool}", execution_time_ms=elapsed)
        except Exception as e:
            elapsed = int((datetime.now() - start).total_seconds() * 1000)
            return ToolResult(tool_type=ToolType.VECTOR_SEARCH, success=False, error=str(e), execution_time_ms=elapsed)

    async def _synthesize(self, state: AgentState) -> str:
        # Build team-agnostic synthesis prompt
        rag_context = ""
        try:
            for tr in state.get("tool_results", []):
                data = getattr(tr, "data", {})
                if isinstance(data, dict) and data.get("tool") == "external_research":
                    items = []
                    for s in (data.get("sources") or [])[:5]:
                        if isinstance(s, dict):
                            title = s.get("title") or "source"
                            url = s.get("url") or ""
                            take = s.get("takeaways") or []
                            items.append(f"- {title} ({url}) — " + "; ".join(take[:3]))
                    if items:
                        rag_context = "WEB RESEARCH SOURCES:\n" + "\n".join(items)
                    break
        except Exception:
            rag_context = ""

        # Format tool results with actual data for synthesis
        summaries: List[str] = []
        try:
            for tr in state.get("tool_results", []):
                if not getattr(tr, "success", False):
                    continue
                tname = tr.tool_type.value if hasattr(tr.tool_type, 'value') else str(tr.tool_type)
                data = getattr(tr, "data", {})
                if not isinstance(data, dict):
                    continue
                
                # Format based on tool type
                tool_id = data.get("tool", "").lower()
                
                # Schedule/scoreboard data
                if tool_id in ("get_schedule", "get_live_scoreboard"):
                    games = data.get("games", [])
                    if games:
                        summaries.append(f"\nTool: {tool_id}")
                        summaries.append(f"Date: {data.get('date', 'N/A')}")
                        summaries.append(f"Games found: {len(games)}")
                        for g in games[:10]:  # Limit to first 10 games
                            try:
                                home = (g.get("homeTeam", {}) or {}).get("abbrev") or g.get("home", "")
                                away = (g.get("awayTeam", {}) or {}).get("abbrev") or g.get("away", "")
                                game_state = g.get("gameState") or g.get("status") or "TBD"
                                start = g.get("startTimeUTC") or g.get("start_time_utc") or ""
                                summaries.append(f"  - {away} @ {home} ({game_state}) {start}")
                            except Exception:
                                continue
                    else:
                        summaries.append(f"\nTool: {tool_id} - No games found for {data.get('date', 'N/A')}")
                
                # Recent games data
                elif tool_id == "get_recent_games":
                    games = data.get("games", [])
                    team = data.get("team", "N/A")
                    summaries.append(f"\nTool: {tool_id}")
                    summaries.append(f"Team: {team}")
                    summaries.append(f"Games found: {len(games)}")
                    if games:
                        summaries.append("\nRecent Results:")
                        for g in games:
                            try:
                                date = g.get("date", "")
                                opp = g.get("opponent", "")
                                loc = g.get("location", "")
                                result = g.get("result", "")
                                team_score = g.get("team_score", 0)
                                opp_score = g.get("opp_score", 0)
                                summaries.append(f"  {date}: {team} {team_score} - {opp} {opp_score} ({result}, {loc})")
                            except Exception:
                                continue
                    else:
                        summaries.append("No recent completed games found")
                
                # Roster data
                elif tool_id == "get_team_roster":
                    players = data.get("players", [])
                    summaries.append(f"\nTool: {tool_id}")
                    summaries.append(f"Team: {data.get('team', 'N/A')}, Season: {data.get('season', 'N/A')}")
                    summaries.append(f"Total Players: {len(players)}")
                    if players:
                        summaries.append("\nRoster:")
                        # Group by position
                        forwards = [p for p in players if str(p.get("position", "")).upper() in ("C", "L", "R", "LW", "RW", "F")]
                        defensemen = [p for p in players if str(p.get("position", "")).upper() in ("D",)]
                        goalies = [p for p in players if str(p.get("position", "")).upper() in ("G",)]
                        
                        if forwards:
                            summaries.append(f"\nForwards ({len(forwards)}):")
                            for p in forwards[:15]:  # Limit to avoid huge prompts
                                name = p.get("full_name", "Unknown")
                                pos = p.get("position", "")
                                num = p.get("sweater", "")
                                summaries.append(f"  #{num} {name} ({pos})")
                        
                        if defensemen:
                            summaries.append(f"\nDefensemen ({len(defensemen)}):")
                            for p in defensemen[:10]:
                                name = p.get("full_name", "Unknown")
                                pos = p.get("position", "")
                                num = p.get("sweater", "")
                                summaries.append(f"  #{num} {name} ({pos})")
                        
                        if goalies:
                            summaries.append(f"\nGoalies ({len(goalies)}):")
                            for p in goalies:
                                name = p.get("full_name", "Unknown")
                                pos = p.get("position", "")
                                num = p.get("sweater", "")
                                summaries.append(f"  #{num} {name} ({pos})")
                
                # Player lookup
                elif tool_id == "find_player_by_team_and_number":
                    player = data.get("player")
                    if player:
                        summaries.append(f"\nTool: {tool_id}")
                        summaries.append(f"Found: {player.get('full_name')} #{player.get('sweater')} ({player.get('team_abbrev')})")
                
                # Generic fallback
                else:
                    at = data.get("analysis_type") or tool_id or tname
                    summaries.append(f"\nTool: {at}")
            
            tool_summaries = "\n".join(summaries) if summaries else "No data retrieved"
        except Exception as e:
            logger.warning(f"Failed to format tool summaries: {e}")
            tool_summaries = "Data retrieved but formatting failed"

        # Build conversation history summary for context
        conversation_history = ""
        try:
            prior_msgs = state.get("prior_messages", [])
            if prior_msgs:
                recent = prior_msgs[-4:]  # Last 2 turns
                lines = []
                for m in recent:
                    role = m.get("role", "user")
                    text = str(m.get("text", ""))[:200]  # Truncate long messages
                    lines.append(f"{role}: {text}")
                conversation_history = "\n".join(lines)
        except Exception:
            conversation_history = ""

        try:
            prompt = build_neutral_synthesis_prompt(
                query=state["original_query"],
                current_date=state.get("current_date", ""),
                current_season=state.get("current_season", ""),
                tool_summaries=tool_summaries,
                rag_context=rag_context,
                conversation_history=conversation_history,
            )
        except Exception:
            prompt = state["original_query"]

        # Build role/mode-aware synthesis system prompt
        try:
            uc = state.get("user_context")
            mode = state.get("intent_analysis", {}).get("processing_approach")  # proxy for now
            system_prompt = get_synthesis_system_prompt(mode=mode, role=getattr(uc, "role", None))
        except Exception:
            system_prompt = SYNTHESIS_SYSTEM_PROMPT
        try:
            resp = await self.provider.generate(
                model=self.model_slug,
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
            )
            return resp.get("text", "") or "Analysis complete."
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return "I encountered an error synthesizing the response."

    async def _run_external_research(self, query: str) -> Dict[str, Any]:
        """Ask the deep-research model to produce a compact JSON research brief."""
        try:
            research_prompt = (
                "You are performing web research to support a hockey pre-scout report. "
                "Return STRICT JSON with keys: sources (array of {title,url,takeaways[]}), summary (string). "
                "Limit to 5 reputable sources. Keep takeaways concise. Query: " + query[:400]
            )
            resp = await self.provider.generate(
                model=self.model_slug,
                system_prompt="Research: return strict JSON only.",
                user_prompt=research_prompt,
                temperature=0.2,
                max_tokens=768,
                top_p=0.9,
            )
            txt = (resp.get("text") or "").strip()
            data = self._safe_json(txt)
            if isinstance(data, dict):
                # Normalize shape
                srcs = data.get("sources") if isinstance(data.get("sources"), list) else []
                norm = []
                for s in srcs[:5]:
                    if not isinstance(s, dict):
                        continue
                    norm.append({
                        "title": s.get("title"),
                        "url": s.get("url"),
                        "takeaways": s.get("takeaways") if isinstance(s.get("takeaways"), list) else []
                    })
                return {"sources": norm, "summary": data.get("summary", "")}
        except Exception:
            pass
        return {"sources": [], "summary": ""}

    def _has_sufficient_data(self, state: AgentState) -> bool:
        # If we have at least one successful tool result with data, proceed
        for tr in state.get("tool_results", []):
            if getattr(tr, "success", False) and getattr(tr, "data", None):
                return True
        return False

    def _safe_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            # Strip code fences if present
            t = text.strip()
            if t.startswith("```"):
                t = t.strip("`\n ")
                # Remove potential language tag
                if "\n" in t:
                    t = t.split("\n", 1)[1]
            return json.loads(t)
        except Exception:
            return None

    def _data_brief(self, state: AgentState) -> str:
        # Short summary to help planning without leaking large content
        try:
            parts: List[str] = []
            if state.get("retrieved_context"):
                parts.append("context:yes")
            if state.get("analytics_data"):
                at = state.get("analytics_data", {}).get("analysis_type", "?")
                parts.append(f"analytics:{at}")
            parts.append(f"tools:{len(state.get('tool_results', []))}")
            return ",".join(parts)
        except Exception:
            return ""
