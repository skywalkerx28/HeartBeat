"""
HeartBeat Engine - Vector Retriever Node (Vertex-backed)

Retrieves context via the ontology-aware retriever using the configured
vector backend (Vertex AI Vector Search). Provides structured context
packs for synthesis.
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from orchestrator.utils.state import (
    AgentState,
    ToolType,
    ToolResult,
    update_state_step,
    add_tool_result,
    add_error,
)
from orchestrator.tools.ontology_retriever import OntologyRetriever
from orchestrator.tools.pinecone_mcp_client import VectorStoreFactory
from orchestrator.config.settings import settings

logger = logging.getLogger(__name__)


class VectorRetrieverNode:
    def __init__(self) -> None:
        try:
            backend = VectorStoreFactory.create_backend()
        except Exception as e:
            logger.warning(f"Vector backend unavailable: {e}")
            backend = None
        self.retriever = OntologyRetriever(
            project_id=settings.bigquery.project_id,
            dataset="raw",
            vector_backend=backend,
        )

    async def process(self, state: AgentState) -> AgentState:
        state = update_state_step(state, "vector_retrieval")
        start = datetime.now()
        try:
            query = state["original_query"]
            pack = await self.retriever.retrieve_objects(query=query, top_k=5)
            data = pack.to_dict()
            exec_ms = int((datetime.now() - start).total_seconds() * 1000)
            tr = ToolResult(
                tool_type=ToolType.VECTOR_SEARCH,
                success=True,
                data=data,
                execution_time_ms=exec_ms,
                citations=[o.get("object_type") for o in data.get("primary_objects", [])],
            )
            state = add_tool_result(state, tr)
            state["retrieved_context"] = data
            return state
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            exec_ms = int((datetime.now() - start).total_seconds() * 1000)
            tr = ToolResult(
                tool_type=ToolType.VECTOR_SEARCH,
                success=False,
                error=str(e),
                execution_time_ms=exec_ms,
            )
            state = add_tool_result(state, tr)
            state = add_error(state, str(e))
            return state

