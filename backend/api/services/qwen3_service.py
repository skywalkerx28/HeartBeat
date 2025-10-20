"""
Qwen3 Best Practices Orchestrator Service for HeartBeat Engine

Wraps the Qwen3-Next-80B Thinking best practices orchestrator for use in the FastAPI backend.
Provides a clean interface between the HTTP API and the Vertex AI-powered orchestrator.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4

from orchestrator.agents.qwen3_best_practices_orchestrator import qwen3_best_practices_orchestrator
from orchestrator.utils.state import AgentState, create_initial_state, UserContext, ToolType
from orchestrator.config.settings import UserRole

logger = logging.getLogger(__name__)


class Qwen3OrchestratorService:
    """
    Service wrapper for Qwen3 Best Practices orchestrator integration.

    Handles:
    - State management
    - User context mapping
    - Result transformation for API responses
    - Error handling and logging
    """
    
    def __init__(self):
        """Initialize Qwen3 service with best practices orchestrator."""
        import inspect
        self.orchestrator = qwen3_best_practices_orchestrator
        src_file = inspect.getsourcefile(self.orchestrator.__class__) or "unknown"
        logger.info(f"Qwen3 Best Practices Orchestrator Service initialized (source: {src_file})")
        # In-memory conversation store: { thread_key: { 'messages': [...], 'last_entities': {...}, 'updated_at': iso } }
        # thread_key = f"{user_id}:{conversation_id or 'default'}"
        self._conversations: Dict[str, Dict[str, Any]] = {}
        # Limits for summarization
        self._max_turns: int = 20
        self._summary_compact_to: int = 8
    
    async def process_query(
        self,
        query: str,
        user_context: UserContext,
        conversation_id: str | None = None
    ) -> Dict[str, Any]:
        """
        Process a hockey analytics query through Qwen3 orchestrator.
        
        Args:
            query: User's natural language query
            user_context: User role and context information
            
        Returns:
            Dict with structured response data for API
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing query via Qwen3: {query[:100]}...")
            
            # Create initial state
            state = create_initial_state(
                query=query,
                user_context=user_context
            )
            # Attach prior conversation messages (if any)
            thread_key = self._thread_key(user_context, conversation_id)
            prior_messages = self._get_prior_messages(thread_key)
            if prior_messages:
                state["prior_messages"] = prior_messages
            # Attach short-memory last entities
            last_entities = self._conversations.get(thread_key, {}).get("last_entities")
            if last_entities:
                state["last_entities"] = last_entities
            
            # Process through Qwen3 best practices orchestrator
            # Model has all tools upfront and controls its own workflow
            result_state = await self.orchestrator.process_query(state)
            
            # Calculate processing time
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Transform to API response format
            api_response = self._transform_to_api_format(
                result_state,
                processing_time_ms
            )

            # Persist this turn in the conversation store
            self._append_to_thread(thread_key, role="user", text=query)
            final_text = api_response.get("response") if isinstance(api_response, dict) else api_response.response
            self._append_to_thread(thread_key, role="model", text=str(final_text))
            # Update short-memory entities from tool results
            try:
                self._update_last_entities(thread_key, result_state)
            except Exception as e:
                logger.debug(f"Entity extraction failed: {e}")
            # Summarize if the thread is too long
            await self._maybe_summarize_thread(thread_key)
            
            logger.info(f"Query processed successfully in {processing_time_ms}ms")
            return api_response
            
        except Exception as e:
            logger.error(f"Error processing query via Qwen3: {str(e)}", exc_info=True)
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return {
                "success": False,
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "query_type": "unknown",
                "tool_results": [],
                "processing_time_ms": processing_time_ms,
                "evidence_chain": [],
                "analytics": [],
                "errors": [str(e)],
                "warnings": []
            }
    
    def _transform_to_api_format(
        self,
        state: AgentState,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Transform orchestrator state to API response format.
        
        Args:
            state: Final AgentState from orchestrator
            processing_time_ms: Total processing time
            
        Returns:
            Dict formatted for API response
        """
        # Extract tool results
        tool_results = []
        for tool_result in state.get("tool_results", []):
            # Serialize data - convert DataFrames and other non-serializable types
            serialized_data = self._serialize_tool_data(tool_result.data)
            
            tool_results.append({
                "tool": tool_result.tool_type.value if hasattr(tool_result.tool_type, 'value') else str(tool_result.tool_type),
                "success": tool_result.success,
                "data": serialized_data,
                "processing_time_ms": tool_result.execution_time_ms if hasattr(tool_result, 'execution_time_ms') else 0,
                "citations": tool_result.citations if hasattr(tool_result, 'citations') else [],
                "error": tool_result.error
            })
        
        # Build analytics data for frontend visualization
        analytics = self._build_analytics_from_results(state)
        # Merge any analytics blocks the orchestrator attached directly (e.g., clips panels)
        try:
            prebuilt = state.get("analytics", []) if isinstance(state, dict) else []
            for a in prebuilt:
                if isinstance(a, dict) and a.get("type") in {"clips", "stat", "chart", "table"}:
                    if a.get("type") == "clips" and not a.get("clips"):
                        continue
                    analytics.append(a)
        except Exception:
            pass
        
        # Dedupe analytics blocks (common duplicate case: tool_results + prebuilt analytics)
        try:
            unique = []
            seen_keys = set()
            for a in analytics:
                if not isinstance(a, dict):
                    continue
                a_type = a.get("type")
                a_title = a.get("title")
                key = (a_type, a_title)
                # For clips, include a stable clip-id set in the key when available
                if a_type == "clips" and isinstance(a.get("clips"), list):
                    try:
                        clip_ids = tuple(sorted(str(c.get("clip_id")) for c in a.get("clips") if isinstance(c, dict)))
                        key = (a_type, a_title, clip_ids)
                    except Exception:
                        pass
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                unique.append(a)
            analytics = unique
        except Exception:
            pass

        # Build evidence chain
        evidence_chain = self._build_evidence_chain(state)
        
        return {
            "success": True,
            "response": state.get("final_response", "Analysis complete."),
            "query_type": state.get("query_type", {}).get("primary") if isinstance(state.get("query_type"), dict) else state.get("query_type"),
            "tool_results": tool_results,
            "processing_time_ms": processing_time_ms,
            "evidence": evidence_chain,  
            "citations": [],  # Frontend expects citations field
            "analytics": analytics,
            "errors": state.get("errors", []),
            "warnings": state.get("warnings", [])
        }

    # --------------- Conversation Memory ---------------
    def _thread_key(self, user: UserContext, conversation_id: str | None) -> str:
        return f"{user.user_id}:{conversation_id or 'default'}"

    def _get_prior_messages(self, thread_key: str) -> List[Dict[str, Any]]:
        thread = self._conversations.get(thread_key)
        if not thread:
            return []
        return thread.get("messages", [])

    def _append_to_thread(self, thread_key: str, role: str, text: str) -> None:
        if not text:
            return
        thread = self._conversations.setdefault(thread_key, {"messages": [], "last_entities": {}, "updated_at": datetime.now().isoformat()})
        thread["messages"].append({"role": role, "text": text})
        # Trim to a hard cap to avoid unbounded growth even before summarize
        if len(thread["messages"]) > (self._max_turns * 2):
            thread["messages"] = thread["messages"][-self._max_turns*2:]
        thread["updated_at"] = datetime.now().isoformat()

    async def _maybe_summarize_thread(self, thread_key: str) -> None:
        thread = self._conversations.get(thread_key)
        if not thread:
            return
        msgs = thread.get("messages", [])
        if len(msgs) <= self._max_turns:
            return
        # Summarize the earliest chunk and keep the tail
        head = msgs[: len(msgs) - self._summary_compact_to]
        tail = msgs[len(msgs) - self._summary_compact_to :]
        try:
            summary_text = await self._summarize_messages(head)
        except Exception:
            # Fallback: naive compression
            summary_text = self._naive_summarize(head)
        thread["messages"] = [{"role": "model", "text": f"Conversation summary: {summary_text}"}] + tail
        thread["updated_at"] = datetime.now().isoformat()

    async def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        # Use the same Qwen3 model to produce a compact memory
        try:
            import vertexai
            from vertexai.preview.generative_models import GenerativeModel, Content, Part
            vertexai.init()  # assume orchestrator already configured project/location
            model = GenerativeModel("publishers/qwen/models/qwen3-next-80b-a3b-thinking-maas")
            parts = []
            for m in messages[-40:]:
                role = m.get("role", "user")
                txt = str(m.get("text", ""))[:2000]
                parts.append(Content(role=role if role in ("user", "model") else "user", parts=[Part.from_text(txt)]))
            prompt = Content(role="user", parts=[Part.from_text("Summarize this conversation for memory. Keep player names, team abbreviations, jersey numbers, seasons, opponents, and key intents. 6-8 lines, plain text, no markdown.")])
            resp = model.generate_content([prompt] + parts, generation_config={"temperature": 0.2, "top_p": 0.95, "max_output_tokens": 512})
            text = getattr(resp, "text", "") or ""
            return text.strip()[:2000]
        except Exception as e:
            logger.warning(f"Summarizer failed: {e}")
            return self._naive_summarize(messages)

    def _naive_summarize(self, messages: List[Dict[str, Any]]) -> str:
        # Fallback: concatenate last sentences of each message
        out: List[str] = []
        for m in messages[-20:]:
            txt = str(m.get("text", ""))
            if not txt:
                continue
            sent = txt.split(". ")[-1]
            out.append(sent.strip()[:160])
        return " | ".join(out)[:1000]

    def _update_last_entities(self, thread_key: str, state: AgentState) -> None:
        thread = self._conversations.setdefault(thread_key, {"messages": [], "last_entities": {}, "updated_at": datetime.now().isoformat()})
        last = thread.get("last_entities", {})
        for tr in state.get("tool_results", []):
            data = getattr(tr, "data", None)
            if not isinstance(data, dict):
                continue
            # Single player hit
            if data.get("tool") == "find_player_by_team_and_number":
                p = data.get("player")
                if isinstance(p, dict):
                    if p.get("full_name"):
                        last["player_name"] = p.get("full_name")
                    if p.get("team_abbrev"):
                        last["team_abbrev"] = p.get("team_abbrev")
                    if p.get("sweater"):
                        last["sweater"] = p.get("sweater")
            # Roster context can update team
            if data.get("tool") == "get_team_roster" and data.get("team"):
                last["team_abbrev"] = data.get("team")
        thread["last_entities"] = last
        thread["updated_at"] = datetime.now().isoformat()

    # --------- Public helpers for conversation listing ---------
    def list_conversations(self, user: UserContext) -> List[Dict[str, Any]]:
        prefix = f"{user.user_id}:"
        items: List[Dict[str, Any]] = []
        for key, val in self._conversations.items():
            if not key.startswith(prefix):
                continue
            conv_id = key.split(":", 1)[1]
            msgs = val.get("messages", [])
            
            # Use custom title if set, otherwise generate from first message
            custom_title = val.get("title")
            if custom_title:
                title = custom_title
            else:
                title = ""
                # Use first user message as title
                for m in msgs:
                    if m.get("role") == "user" and m.get("text"):
                        title = str(m.get("text"))[:80]
                        break
                if not title and msgs:
                    title = str(msgs[0].get("text", "")).split("\n")[0][:80]
                if not title:
                    title = f"Conversation {conv_id}"
            
            items.append({
                "conversation_id": conv_id,
                "updated_at": val.get("updated_at"),
                "title": title,
                "message_count": len(msgs)
            })
        # Most recent first
        items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return items

    def get_conversation(self, user: UserContext, conversation_id: str) -> Dict[str, Any]:
        key = self._thread_key(user, conversation_id)
        val = self._conversations.get(key) or {"messages": [], "updated_at": None}
        return {
            "conversation_id": conversation_id,
            "updated_at": val.get("updated_at"),
            "messages": val.get("messages", [])
        }

    def start_conversation(self, user: UserContext) -> str:
        conv_id = uuid4().hex[:12]
        key = self._thread_key(user, conv_id)
        if key not in self._conversations:
            self._conversations[key] = {"messages": [], "last_entities": {}, "updated_at": datetime.now().isoformat(), "title": None}
        return conv_id
    
    def rename_conversation(self, user: UserContext, conversation_id: str, new_title: str) -> bool:
        """Rename a conversation with a custom title"""
        key = self._thread_key(user, conversation_id)
        thread = self._conversations.get(key)
        if not thread:
            return False
        thread["title"] = new_title
        thread["updated_at"] = datetime.now().isoformat()
        return True
    
    def delete_conversation(self, user: UserContext, conversation_id: str) -> bool:
        """Delete a conversation"""
        key = self._thread_key(user, conversation_id)
        if key in self._conversations:
            del self._conversations[key]
            return True
        return False
    
    def _build_analytics_from_results(self, state: AgentState) -> List[Dict[str, Any]]:
        """
        Build analytics data from tool results for frontend visualization.
        
        Args:
            state: AgentState with tool results
            
        Returns:
            List of analytics data objects
        """
        analytics = []
        
        for tool_result in state.get("tool_results", []):
            # Pull raw data once and guard against non-dict payloads
            data = getattr(tool_result, "data", None)
            if not tool_result.success or not data:
                continue
            # Many downstream branches expect a dict with keys
            if not isinstance(data, dict):
                # Unsupported shape for analytics – skip safely
                continue

            # Video clips (retrieve_video_clips) — direct pass-through to UI
            if data.get("type") == "clips" and isinstance(data.get("clips"), list):
                title = data.get("title") or "Video Clips"
                analytics.append({
                    "type": "clips",
                    "title": title,
                    "clips": data.get("clips", [])
                })
                continue

            # Roster: show current team roster as a table
            if data.get("tool") == "get_team_roster":
                roster = data.get("players") or data.get("roster") or []
                if isinstance(roster, list) and roster:
                    columns = [
                        {"key": "sweater", "label": "#"},
                        {"key": "full_name", "label": "Player"},
                        {"key": "position", "label": "Pos"}
                    ]
                    rows = []
                    for p in roster[:23]:
                        if not isinstance(p, dict):
                            continue
                        rows.append({
                            "sweater": p.get("sweater"),
                            "full_name": p.get("full_name") or p.get("name"),
                            "position": p.get("position")
                        })
                    analytics.append({
                        "type": "table",
                        "title": f"{(data.get('team') or '').upper()} Roster",
                        "data": {"columns": columns, "rows": rows},
                        "metadata": {"source": data.get("source") or (data.get("telemetry") or {}).get("source")}
                    })
                continue

            # League-wide jersey holders table
            if data.get("tool") == "find_players_by_number":
                players = data.get("players", []) if isinstance(data.get("players"), list) else []
                columns = [
                    {"key": "team_abbrev", "label": "Team"},
                    {"key": "full_name", "label": "Player"},
                    {"key": "position", "label": "Pos"},
                    {"key": "sweater", "label": "#"}
                ]
                rows = []
                for p in players[:50]:
                    rows.append({
                        "team_abbrev": p.get("team_abbrev"),
                        "full_name": p.get("full_name"),
                        "position": p.get("position"),
                        "sweater": p.get("sweater")
                    })
                analytics.append({
                    "type": "table",
                    "title": f"League — # {data.get('number')}",
                    "data": {"columns": columns, "rows": rows},
                    "metadata": {"source": (data.get("telemetry") or {}).get("source")}
                })
                continue

            # Single jersey holder stat card
            if data.get("tool") == "find_player_by_team_and_number" and data.get("player"):
                p = data.get("player")
                analytics.append({
                    "type": "stat",
                    "title": f"{(p.get('team_abbrev') or '').upper()} # {p.get('sweater')}",
                    "data": {
                        "full_name": p.get("full_name"),
                        "position": p.get("position"),
                        "sweater": p.get("sweater")
                    },
                    "metadata": {"source": data.get("source")}
                })
                continue

            # Visualization spec -> chart analytics
            if data.get("tool") == "generate_visualization":
                # Prefer Vega-Lite spec if provided by the orchestrator
                vega_spec = data.get("vegaLite") or data.get("vega")
                chart_spec = data.get("chart_spec")
                if vega_spec:
                    analytics.append({
                        "type": "chart",
                        "title": "Visualization",
                        "data": {"vegaLite": vega_spec},
                        "metadata": {}
                    })
                    continue
                if isinstance(chart_spec, dict):
                    # If this looks like our lightweight ChartRenderer spec, pass it through
                    if chart_spec.get("kind"):
                        analytics.append({
                            "type": "chart",
                            "title": "Visualization",
                            "data": chart_spec,
                            "metadata": {}
                        })
                        continue
                    else:
                        # Otherwise assume it's already Vega-Lite
                        analytics.append({
                            "type": "chart",
                            "title": "Visualization",
                            "data": {"vegaLite": chart_spec},
                            "metadata": {}
                        })
                        continue

            
            # Schedule / Calendar (from get_schedule tool)
            if data.get("tool") == "get_schedule":
                games = data.get("games", []) if isinstance(data.get("games"), list) else []
                # Build tabular schema (remove game_state for cleaner layout)
                columns = [
                    {"key": "date", "label": "Date"},
                    {"key": "home", "label": "Home"},
                    {"key": "away", "label": "Away"},
                    {"key": "result", "label": "Result"},
                    {"key": "start_time_utc", "label": "Start (UTC)"},
                ]
                # Normalize rows to ensure keys present (include all games)
                rows = []
                for g in games:
                    # Compute result if scores present; otherwise TBD for future
                    hs = g.get("home_score")
                    as_ = g.get("away_score")
                    gs = (g.get("game_state") or "").upper()
                    gss = (g.get("game_schedule_state") or "").upper()
                    if isinstance(hs, (int, float)) and isinstance(as_, (int, float)):
                        result = f"{int(hs)}-{int(as_)}"
                    else:
                        if gs in ("FUT", "PRE", "SCHEDULED", ""):
                            result = "TBD"
                        elif gs == "OFF":
                            # OFF appears in season schedules for provisional/"if necessary" dates.
                            # To avoid misleading users, surface as unknown instead of implying it wasn't played.
                            result = "UNK"
                        elif gss == "PPD":
                            result = "Postponed"
                        elif gss == "SUSP":
                            result = "Suspended"
                        else:
                            result = gs.title() if gs else "TBD"
                    rows.append({
                        "date": g.get("date"),
                        "home": g.get("home"),
                        "away": g.get("away"),
                        "result": result,
                        "start_time_utc": g.get("start_time_utc")
                    })
                title_date = data.get("date") or (rows[0]["date"] if rows else "Today")
                title = f"NHL Schedule — {title_date}"
                if data.get("team"):
                    title = f"{str(data.get('team')).upper()} Schedule"
                analytics.append({
                    "type": "table",
                    "title": title,
                    "data": {"columns": columns, "rows": rows},
                    "metadata": {"source": data.get("telemetry", {}).get("source", "nhl_api")}
                })
                # If summary counts are present, add a stat card to prevent hallucinated totals
                summary = data.get("summary") if isinstance(data.get("summary"), dict) else None
                if summary:
                    analytics.append({
                        "type": "stat",
                        "title": "Schedule Summary",
                        "data": {
                            "total": summary.get("total_games"),
                            "regular_season": summary.get("regular_season"),
                            "preseason": summary.get("preseason"),
                            "postseason": summary.get("postseason")
                        },
                        "metadata": {"source": data.get("telemetry", {}).get("source", "nhl_api")}
                    })
                continue

            # Power play analytics
            if "power_play" in str(tool_result.tool_type).lower() or data.get("analysis_type") == "power_play":
                analytics.append({
                    "type": "stat",
                    "title": "Power Play Analysis",
                    "data": {
                        "pp_units": data.get("total_pp_units", 0),
                        "opponent": data.get("opponent", "All"),
                        "metrics": data.get("pp_units", [])[:5]  # Top 5 units
                    },
                    "metadata": {
                        "source": data.get("data_source", "parquet"),
                        "columns": data.get("columns_available", [])
                    }
                })
            
            # Matchup analytics
            elif "matchup" in str(tool_result.tool_type).lower() or data.get("analysis_type") == "matchup":
                analytics.append({
                    "type": "stat",
                    "title": f"Matchup Analysis - {data.get('opponent', 'Opponent')}",
                    "data": {
                        "total_matchups": data.get("total_matchups", 0),
                        "xgf": data.get("xgf", 0),
                        "metrics": data.get("summary_stats", {})
                    },
                    "metadata": {
                        "source": data.get("data_source", "parquet")
                    }
                })
            
            # Historical season results (only when actual season_results data is present)
            elif data.get("analysis_type") == "season_results":
                tbl = self._to_table_from_games(data)
                if tbl.get("rows"):
                    analytics.append({
                        "type": "table",
                        "title": "Season Results",
                        "data": tbl,
                        "metadata": {"source": data.get("data_source", "parquet")}
                    })
                    # Optional chart: goal differential trend if present
                    try:
                        series = self._series_goal_diff(data)
                        if series and len(series) >= 3:
                            analytics.append({
                                "type": "chart",
                                "title": "Goal Differential Trend",
                                "data": {"kind": "line", "xKey": "index", "yKey": "diff", "rows": series},
                                "metadata": {}
                            })
                    except Exception:
                        pass

            # Live scoreboard table (when explicitly requested)
            elif data.get("tool") == "get_live_scoreboard":
                sb = data.get("scoreboard", {})
                games = sb.get("games", []) if isinstance(sb, dict) else []
                # Resolve user timezone from state if available
                tz_name = None
                try:
                    uc = state.get("user_context")
                    if uc and getattr(uc, "preferences", None):
                        tz_name = uc.preferences.get("timezone")
                except Exception:
                    tz_name = None
                tbl = self._to_table_from_scoreboard(games, tz_name)
                if tbl.get("rows"):
                    analytics.append({
                        "type": "table",
                        "title": "Live Scoreboard",
                        "data": tbl,
                        "metadata": {"source": data.get("telemetry", {}).get("source", "nhl_api")}
                    })
            
            # Player stats analytics (if available from parquet)
            elif data.get("analysis_type") == "player_stats":
                # Build table from game logs if present
                tbl = self._to_table_from_game_logs(data)
                if tbl.get("rows"):
                    analytics.append({
                        "type": "table",
                        "title": f"{data.get('player_name','Player')} — Game Log",
                        "data": tbl,
                        "metadata": {"source": data.get("data_source", "parquet")}
                    })
                    # Chart: points per game trend
                    series = self._series_points(tbl.get("rows", []))
                    if series and len(series) >= 3:
                        analytics.append({
                            "type": "chart",
                            "title": "Points per Game",
                            "data": {"kind": "line", "xKey": "index", "yKey": "points", "rows": series},
                            "metadata": {}
                        })
        
        return analytics
    
    def _build_evidence_chain(self, state: AgentState) -> List[str]:
        """
        Build evidence chain showing reasoning steps.
        
        Args:
            state: AgentState with processing history
            
        Returns:
            List of evidence strings
        """
        evidence = []
        
        # Add query type detection
        if state.get("query_type"):
            qt = state.get("query_type")
            if isinstance(qt, dict):
                evidence.append(f"Identified query type: {qt.get('primary', 'unknown')}")
            else:
                evidence.append(f"Identified query type: {qt}")
        
        # Add tools used
        tools_used = [tr.tool_type for tr in state.get("tool_results", []) if tr.success]
        if tools_used:
            tool_names = [t.value if hasattr(t, 'value') else str(t) for t in tools_used]
            evidence.append(f"Executed {len(tools_used)} analysis tools: {', '.join(tool_names)}")
        
        # Add data sources
        data_sources = set()
        for tr in state.get("tool_results", []):
            if tr.success and tr.data and isinstance(tr.data, dict):
                source = tr.data.get("data_source")
                if source:
                    data_sources.add(source)
        
        if data_sources:
            evidence.append(f"Queried data sources: {', '.join(data_sources)}")
        
        return evidence
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of Qwen3 orchestrator.
        
        Returns:
            Health status dict
        """
        try:
            # Test that coordinator is initialized
            status = {
                "coordinator_initialized": self.orchestrator is not None,
                "vertex_ai_configured": True,  # Already validated at startup
                "status": "healthy"
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "coordinator_initialized": False,
                "vertex_ai_configured": False,
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _serialize_tool_data(self, data: Any) -> Any:
        """
        Serialize tool data for JSON response.
        Converts non-serializable types (like pandas DataFrames) to serializable formats.
        
        Args:
            data: Raw tool result data
            
        Returns:
            JSON-serializable data
        """
        import pandas as pd
        
        if data is None:
            return None
        
        # Handle pandas DataFrame
        if isinstance(data, pd.DataFrame):
            # Convert to list of dicts for JSON serialization
            return data.to_dict('records')
        
        # Handle dict with potential DataFrame values
        if isinstance(data, dict):
            serialized = {}
            for key, value in data.items():
                if isinstance(value, pd.DataFrame):
                    serialized[key] = value.to_dict('records')
                elif isinstance(value, list):
                    # Recursively handle lists
                    serialized[key] = [self._serialize_tool_data(item) for item in value]
                elif isinstance(value, dict):
                    # Recursively handle nested dicts
                    serialized[key] = self._serialize_tool_data(value)
                else:
                    serialized[key] = value
            return serialized
        
        # Handle lists
        if isinstance(data, list):
            return [self._serialize_tool_data(item) for item in data]
        
        # Return as-is if already serializable
        return data

    def _to_table_from_games(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Best-effort conversion of season_results/games payload to tabular schema for UI."""
        games = []
        try:
            games = data.get("games", []) if isinstance(data.get("games"), list) else []
        except Exception:
            games = []
        columns = [
            {"key": "date", "label": "Date"},
            {"key": "opponent", "label": "Opponent"},
            {"key": "result", "label": "Result"},
            {"key": "score", "label": "Score"},
        ]
        rows = []
        for g in games[:12]:
            try:
                rows.append({
                    "date": g.get("date") or g.get("game_date") or g.get("start_time"),
                    "opponent": g.get("opponent") or g.get("opp") or g.get("opponent_abbrev"),
                    "result": g.get("result") or g.get("win_loss") or g.get("outcome"),
                    "score": g.get("score") or f"{g.get('goals_for','')}-{g.get('goals_against','')}"
                })
            except Exception:
                continue
        if not rows:
            return {"columns": columns, "rows": []}
        return {"columns": columns, "rows": rows}

    def _to_table_from_game_logs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a generic player_stats payload to table using common keys.
        Expected per-game entries under keys such as 'game_logs', 'games', or 'logs'."""
        logs = []
        for key in ("game_logs", "games", "logs"):
            if isinstance(data.get(key), list) and data.get(key):
                logs = data.get(key)
                break
        columns = [
            {"key": "date", "label": "Date"},
            {"key": "opponent", "label": "Opponent"},
            {"key": "goals", "label": "G"},
            {"key": "assists", "label": "A"},
            {"key": "points", "label": "P"}
        ]
        rows = []
        for g in (logs or [])[:20]:
            try:
                goals = g.get("goals") if g.get("goals") is not None else g.get("g")
                assists = g.get("assists") if g.get("assists") is not None else g.get("a")
                pts = g.get("points") if g.get("points") is not None else (goals or 0) + (assists or 0)
                rows.append({
                    "date": g.get("date") or g.get("game_date") or g.get("start_time"),
                    "opponent": g.get("opponent") or g.get("opp") or g.get("opponent_abbrev"),
                    "goals": goals or 0,
                    "assists": assists or 0,
                    "points": pts or 0
                })
            except Exception:
                continue
        return {"columns": columns, "rows": rows}

    def _to_table_from_scoreboard(self, games: list[dict], tz_name: str | None = None) -> Dict[str, Any]:
        """Build a Live Scoreboard table from NHL /v1/score games list.

        - Localizes scheduled start times to the user's timezone (if provided)
        - Splits period and clock into separate columns for live games
        """
        from datetime import datetime, timezone
        try:
            from zoneinfo import ZoneInfo  # Python 3.9+
        except Exception:
            ZoneInfo = None  # Fallback to system local tz

        tzinfo = None
        if tz_name and ZoneInfo is not None:
            try:
                tzinfo = ZoneInfo(tz_name)
            except Exception:
                tzinfo = None
        if tzinfo is None:
            # System local timezone
            tzinfo = datetime.now().astimezone().tzinfo

        columns = [
            {"key": "start_local", "label": "Start (Local)"},
            {"key": "period", "label": "Per"},
            {"key": "clock", "label": "Clock"},
            {"key": "home", "label": "Home"},
            {"key": "away", "label": "Away"},
            {"key": "state", "label": "State"},
            {"key": "score", "label": "Score"},
        ]

        def _abbr(obj):
            try:
                return (obj or {}).get("abbrev") or ""
            except Exception:
                return ""

        def _team(obj, key):
            try:
                if isinstance(obj.get(key), dict):
                    return obj.get(key) or {}
                alt = key.replace("Team", "")  # home/away
                return obj.get(alt) or {}
            except Exception:
                return {}

        def _score(obj, team_key):
            t = _team(obj, team_key)
            v = t.get("score")
            if v is None:
                v = obj.get("homeScore" if team_key == "homeTeam" else "awayScore")
            try:
                return int(v) if v is not None and str(v) != "" else None
            except Exception:
                return None

        rows = []
        for g in (games or [])[:24]:
            try:
                home_t = _team(g, "homeTeam")
                away_t = _team(g, "awayTeam")
                home = _abbr(home_t)
                away = _abbr(away_t)
                state = g.get("gameState") or g.get("status") or ""
                pd = (g.get("periodDescriptor") or {}).get("number") or g.get("period")
                clock = g.get("clock") or g.get("gameClock")
                start_local = ""
                period_val = ""
                clock_val = ""
                if state in ("LIVE", "CRIT"):
                    if pd:
                        period_val = f"{int(pd)}" if isinstance(pd, (int, float)) else str(pd)
                    if clock:
                        # NHL score API returns `clock` as an object for live/final games:
                        # { timeRemaining: "MM:SS", secondsRemaining: number, running: bool, inIntermission: bool }
                        try:
                            if isinstance(clock, dict):
                                # Prefer the canonical timeRemaining field
                                tr = clock.get("timeRemaining")
                                clock_val = str(tr) if tr is not None else ""
                            else:
                                # Fallback: already a string like "MM:SS"
                                clock_val = str(clock)
                        except Exception:
                            clock_val = str(clock)
                else:
                    t_utc = g.get("startTimeUTC") or g.get("startTime") or g.get("gameDate")
                    try:
                        if isinstance(t_utc, str) and "T" in t_utc:
                            dt = datetime.fromisoformat(t_utc.replace("Z", "+00:00"))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            local_dt = dt.astimezone(tzinfo)
                            start_local = local_dt.strftime("%I:%M %p")
                        else:
                            start_local = str(t_utc or "")
                    except Exception:
                        start_local = str(t_utc or "")
                hs = _score(g, "homeTeam")
                as_ = _score(g, "awayTeam")
                score = f"{hs if hs is not None else '-'}-{as_ if as_ is not None else '-'}"
                rows.append({
                    "start_local": start_local,
                    "period": period_val,
                    "clock": clock_val,
                    "home": home,
                    "away": away,
                    "state": state,
                    "score": score,
                })
            except Exception:
                continue
        return {"columns": columns, "rows": rows}

    def _series_points(self, rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        series = []
        try:
            for i, r in enumerate(rows, start=1):
                series.append({"index": i, "points": float(r.get("points") or 0)})
        except Exception:
            return []
        return series

    def _series_goal_diff(self, data: Dict[str, Any]) -> list[Dict[str, Any]]:
        games = data.get("games", []) if isinstance(data.get("games"), list) else []
        series = []
        try:
            for i, g in enumerate(games[:30], start=1):
                gf = g.get("goals_for") or g.get("gf") or 0
                ga = g.get("goals_against") or g.get("ga") or 0
                series.append({"index": i, "diff": float((gf or 0) - (ga or 0))})
        except Exception:
            return []
        return series


# Global service instance
_qwen3_service: Optional[Qwen3OrchestratorService] = None


def get_qwen3_service() -> Qwen3OrchestratorService:
    """
    Get or create the global Qwen3 service instance.
    
    Returns:
        Qwen3OrchestratorService instance
    """
    global _qwen3_service
    
    if _qwen3_service is None:
        _qwen3_service = Qwen3OrchestratorService()
    
    return _qwen3_service
