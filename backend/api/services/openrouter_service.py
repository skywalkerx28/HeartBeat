"""
HeartBeat Engine - OpenRouter Orchestrator Service

Service wrapper that routes synthesis (and later tool planning) through
OpenRouter-selected models while preserving the API response contract.
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from uuid import uuid4

from orchestrator.utils.state import AgentState, create_initial_state, UserContext
from orchestrator.config.modes import modes
from orchestrator.providers.openrouter_provider import OpenRouterProvider
from orchestrator.agents.openrouter_coordinator import OpenRouterCoordinator

logger = logging.getLogger(__name__)


class OpenRouterOrchestratorService:
    """Service to process queries using OpenRouter-selected models."""

    def __init__(self):
        self.provider = OpenRouterProvider()
        # In-memory conversation store compatible with API expectations
        self._conversations: Dict[str, Dict[str, Any]] = {}
        self._max_turns: int = 20
        self._summary_compact_to: int = 8

    async def process_query(
        self,
        query: str,
        user_context: UserContext,
        mode: Optional[str] = None,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        try:
            # Build initial state (keeps time awareness and structure)
            state = create_initial_state(user_context=user_context, query=query)
            # Attach prior conversation messages (if any)
            thread_key = self._thread_key(user_context, conversation_id)
            prior_messages = self._get_prior_messages(thread_key)
            if prior_messages:
                state["prior_messages"] = prior_messages

            # Resolve model and generation parameters
            selection = modes.resolve(mode, explicit_model=model)
            model_slug = selection["model"]
            gen = selection.get("generation", {})
            temperature = float(gen.get("temperature", 0.2))
            max_tokens = int(gen.get("max_tokens", 2048))
            top_p = float(gen.get("top_p", 0.95))

            # Planner-executor coordinator
            coordinator = OpenRouterCoordinator(
                provider=self.provider,
                model_slug=model_slug,
                generation={"temperature": temperature, "max_tokens": max_tokens, "top_p": top_p},
            )
            result_state = await coordinator.process_query(query=query, user_context=user_context, mode=mode, prior_messages=prior_messages)
            text = result_state.get("final_response", "Analysis complete.")

            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            api_response = {
                "success": True,
                "response": text,
                "query_type": result_state.get("query_type"),
                "tool_results": [
                    {
                        "tool": tr.tool_type.value if hasattr(tr.tool_type, 'value') else str(tr.tool_type),
                        "success": tr.success,
                        "data": tr.data,
                        "processing_time_ms": getattr(tr, 'execution_time_ms', 0),
                        "citations": getattr(tr, 'citations', []),
                        "error": getattr(tr, 'error', None),
                    }
                    for tr in result_state.get("tool_results", [])
                ],
                "processing_time_ms": processing_time_ms,
                "evidence": result_state.get("evidence_chain", []),
                "analytics": result_state.get("analytics", []),
                "errors": [],
                "warnings": [],
            }

            # Persist this turn in the conversation store
            try:
                self._append_to_thread(thread_key, role="user", text=query)
                final_text = api_response.get("response") if isinstance(api_response, dict) else str(text)
                self._append_to_thread(thread_key, role="model", text=str(final_text))
                await self._maybe_summarize_thread(thread_key)
            except Exception:
                pass

            return api_response
        except Exception as e:
            logger.error(f"OpenRouter service failed: {e}", exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error processing your request.",
                "query_type": "unknown",
                "tool_results": [],
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                "evidence": [],
                "analytics": [],
                "errors": [str(e)],
                "warnings": [],
            }


# Global accessor
_openrouter_service: Optional[OpenRouterOrchestratorService] = None


def get_openrouter_service() -> OpenRouterOrchestratorService:
    global _openrouter_service
    if _openrouter_service is None:
        _openrouter_service = OpenRouterOrchestratorService()
    return _openrouter_service


# ---------------- Conversation helpers ----------------

def _now_iso() -> str:
    return datetime.now().isoformat()


def _thread_key(self, user: UserContext, conversation_id: str | None) -> str:  # type: ignore
    return f"{user.user_id}:{conversation_id or 'default'}"


def _get_prior_messages(self, thread_key: str) -> List[Dict[str, Any]]:  # type: ignore
    thread = self._conversations.get(thread_key)
    if not thread:
        return []
    return thread.get("messages", [])


def _append_to_thread(self, thread_key: str, role: str, text: str) -> None:  # type: ignore
    if not text:
        return
    thread = self._conversations.setdefault(
        thread_key, {"messages": [], "last_entities": {}, "updated_at": _now_iso(), "title": None}
    )
    thread["messages"].append({"role": role, "text": text})
    if len(thread["messages"]) > (self._max_turns * 2):
        thread["messages"] = thread["messages"][-self._max_turns * 2 :]
    thread["updated_at"] = _now_iso()


async def _maybe_summarize_thread(self, thread_key: str) -> None:  # type: ignore
    thread = self._conversations.get(thread_key)
    if not thread:
        return
    msgs = thread.get("messages", [])
    if len(msgs) <= self._max_turns:
        return
    head = msgs[: len(msgs) - self._summary_compact_to]
    tail = msgs[len(msgs) - self._summary_compact_to :]
    parts: List[str] = []
    for m in head[-40:]:
        txt = str(m.get("text", ""))
        if not txt:
            continue
        parts.append(txt.split(". ")[-1].strip()[:160])
    summary_text = " | ".join(parts)[:1000]
    thread["messages"] = [{"role": "model", "text": f"Conversation summary: {summary_text}"}] + tail
    thread["updated_at"] = _now_iso()


# Bind helper methods to the class
OpenRouterOrchestratorService._thread_key = _thread_key  # type: ignore
OpenRouterOrchestratorService._get_prior_messages = _get_prior_messages  # type: ignore
OpenRouterOrchestratorService._append_to_thread = _append_to_thread  # type: ignore
OpenRouterOrchestratorService._maybe_summarize_thread = _maybe_summarize_thread  # type: ignore


# Public conversation APIs to mirror Qwen3 service
def list_conversations(self, user: UserContext) -> List[Dict[str, Any]]:  # type: ignore
    prefix = f"{user.user_id}:"
    items: List[Dict[str, Any]] = []
    for key, val in self._conversations.items():
        if not key.startswith(prefix):
            continue
        conv_id = key.split(":", 1)[1]
        msgs = val.get("messages", [])
        custom_title = val.get("title")
        if custom_title:
            title = custom_title
        else:
            title = ""
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
    items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return items


def get_conversation(self, user: UserContext, conversation_id: str) -> Dict[str, Any]:  # type: ignore
    key = self._thread_key(user, conversation_id)
    val = self._conversations.get(key) or {"messages": [], "updated_at": None}
    return {
        "conversation_id": conversation_id,
        "updated_at": val.get("updated_at"),
        "messages": val.get("messages", [])
    }


def start_conversation(self, user: UserContext) -> str:  # type: ignore
    conv_id = uuid4().hex[:12]
    key = self._thread_key(user, conv_id)
    if key not in self._conversations:
        self._conversations[key] = {"messages": [], "last_entities": {}, "updated_at": _now_iso(), "title": None}
    return conv_id


def rename_conversation(self, user: UserContext, conversation_id: str, new_title: str) -> bool:  # type: ignore
    key = self._thread_key(user, conversation_id)
    thread = self._conversations.get(key)
    if not thread:
        return False
    thread["title"] = new_title
    thread["updated_at"] = _now_iso()
    return True


def delete_conversation(self, user: UserContext, conversation_id: str) -> bool:  # type: ignore
    key = self._thread_key(user, conversation_id)
    if key in self._conversations:
        del self._conversations[key]
        return True
    return False


OpenRouterOrchestratorService.list_conversations = list_conversations  # type: ignore
OpenRouterOrchestratorService.get_conversation = get_conversation  # type: ignore
OpenRouterOrchestratorService.start_conversation = start_conversation  # type: ignore
OpenRouterOrchestratorService.rename_conversation = rename_conversation  # type: ignore
OpenRouterOrchestratorService.delete_conversation = delete_conversation  # type: ignore


