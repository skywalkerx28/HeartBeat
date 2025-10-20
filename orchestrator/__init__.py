"""
HeartBeat Engine - LangGraph Orchestrator
Montreal Canadiens Advanced Analytics Assistant

Main orchestrator module for coordinating between fine-tuned DeepSeek-R1-Distill-Qwen-32B model,
Pinecone RAG, and Parquet analytics tools.
"""

# Legacy orchestrator - deprecated
# from orchestrator.agents.heartbeat_orchestrator import HeartBeatOrchestrator, orchestrator
from orchestrator.config.settings import settings, UserRole
from orchestrator.utils.state import (
    AgentState,
    UserContext,
    QueryType,
    ToolType,
    create_initial_state
)

__version__ = "1.0.0"
__author__ = "HeartBeat Engine Team"

__all__ = [
    "settings",
    "UserRole",
    "AgentState",
    "UserContext", 
    "QueryType",
    "ToolType",
    "create_initial_state"
]
