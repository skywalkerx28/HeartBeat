"""
HeartBeat Engine - Query Routes

Main query endpoints that integrate with the orchestrator.
This API uses the OpenRouter coordinator exclusively.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, AsyncGenerator

from orchestrator.utils.state import UserContext
from ..models.requests import QueryRequest
from ..models.responses import QueryResponse, ErrorResponse, AnalyticsData, ToolResult, ClipData
from ..dependencies import get_current_user_context
from ..services.openrouter_service import get_openrouter_service

logger = logging.getLogger(__name__)

# OpenRouter is the only orchestrator path

# Disable automatic trailing-slash redirects to avoid CORS preflight 307/308
router = APIRouter(prefix="/api/v1/query", tags=["query"], redirect_slashes=False)

# --- Simple input hygiene/clarification helpers ---
_SHORT_GREETINGS = {"hi", "hey", "yo", "ok", "k", "sup", "hello"}

def _is_ambiguous(text: str) -> bool:
    """Return True when the input is too short/ambiguous to run heavy tools."""
    if not text:
        return True
    t = text.strip().lower()
    if len(t) <= 2:
        return True
    if all(ch in "?!.,;:-_ '" for ch in t):
        return True
    if t in _SHORT_GREETINGS:
        return True
    return False

def _clarification_message(original: str) -> str:
    return (
        "I can help with NHL analytics. Could you clarify what you need?\n\n"
        "For example, try one of these: \n"
        "- Compare a player's xGF% over the last 10 games\n"
        "- Show a team's power-play efficiency this season\n"
        "- Retrieve clips of a player's goals against a specific opponent\n"
        "- What is a team's expected goals trend this week?\n\n"
        f"You wrote: '{original.strip()}'. A bit more detail will help me give a precise answer."
    )

@router.post("", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    user_context: UserContext = Depends(get_current_user_context),
):
    """
    Process a hockey analytics query using the selected orchestrator.
    
    Default: OpenRouter-selected model with HeartBeat tools/RAG.
    """
    
    start_time = datetime.now()
    
    try:
        # Clarify when input is too short/ambiguous instead of returning a hard error
        if _is_ambiguous(request.query):
            logger.info("Returning clarification prompt for ambiguous/short input")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return QueryResponse(
                success=True,
                response=_clarification_message(request.query),
                query_type="clarification",
                tool_results=[],
                processing_time_ms=processing_time,
                evidence=[],
                citations=[],
                analytics=[],
                user_role=user_context.role.value,
                conversation_id=getattr(request, 'conversation_id', None),
                timestamp=datetime.now(),
                errors=[],
                warnings=["clarification_required"],
            )

        logger.info(f"Processing query from {user_context.role.value}: {request.query[:100]}...")
        
        # Use OpenRouter orchestrator
        logger.info("Using OpenRouter orchestrator")
        svc = get_openrouter_service()
        orchestrator_result = await svc.process_query(
            query=request.query,
            user_context=user_context,
            mode=getattr(request, 'mode', None),
            model=getattr(request, 'model', None),
            conversation_id=getattr(request, 'conversation_id', None)
        )
        
        # Convert orchestrator result to API response format
        response = _convert_orchestrator_result(orchestrator_result, user_context, start_time)
        
        logger.info(f"Query processed successfully in {response.processing_time_ms}ms")
        return response
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Query processing failed",
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }
        )

# Keep a second handler for '/'
@router.post("/", response_model=QueryResponse)
async def process_query_slash(
    request: QueryRequest,
    user_context: UserContext = Depends(get_current_user_context),
):
    return await process_query(request, user_context)

@router.post("/stream")
async def stream_query(
    request: QueryRequest,
    user_context: UserContext = Depends(get_current_user_context),
):
    """
    Stream query response for real-time updates.
    
    Returns Server-Sent Events (SSE) for real-time response streaming.
    Works with OpenRouter coordinator.
    """
    
    async def generate_response() -> AsyncGenerator[str, None]:
        """Generate streaming response"""
        
        try:
            # Send initial status
            status_msg = 'Processing query with OpenRouter...'
            yield f"data: {json.dumps({'type': 'status', 'message': status_msg})}\n\n"
            
            # Process query through appropriate orchestrator
            svc = get_openrouter_service()
            result = await svc.process_query(
                query=request.query,
                user_context=user_context,
                mode=getattr(request, 'mode', None),
                model=getattr(request, 'model', None),
                conversation_id=getattr(request, 'conversation_id', None)
            )
            
            # Send partial results as they become available
            if "tool_results" in result:
                for tool_result in result["tool_results"]:
                    yield f"data: {json.dumps({'type': 'tool_result', 'data': tool_result})}\n\n"
            
            # Send final response
            final_response = _convert_orchestrator_result(result, user_context, datetime.now(), getattr(request, 'conversation_id', None))
            yield f"data: {json.dumps({'type': 'final_response', 'data': final_response.dict()})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}", exc_info=True)
            error_data = {
                "type": "error", 
                "message": "Query processing failed",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# ------- Conversation management endpoints -------

@router.get("/conversations")
async def list_conversations(user_context: UserContext = Depends(get_current_user_context)):
    service = get_openrouter_service()
    items = service.list_conversations(user_context)
    return {"success": True, "conversations": items}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user_context: UserContext = Depends(get_current_user_context)):
    service = get_openrouter_service()
    conv = service.get_conversation(user_context, conversation_id)
    return {"success": True, "conversation": conv}


@router.post("/conversations/new")
async def new_conversation(user_context: UserContext = Depends(get_current_user_context)):
    service = get_openrouter_service()
    conv_id = service.start_conversation(user_context)
    return {"success": True, "conversation_id": conv_id}


@router.put("/conversations/{conversation_id}/rename")
async def rename_conversation(
    conversation_id: str,
    request: Dict[str, Any],
    user_context: UserContext = Depends(get_current_user_context)
):
    """Rename a conversation with a custom title"""
    service = get_openrouter_service()
    new_title = request.get("title", "").strip()
    
    if not new_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title cannot be empty"
        )
    
    success = service.rename_conversation(user_context, conversation_id, new_title)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"success": True, "message": "Conversation renamed successfully"}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_context: UserContext = Depends(get_current_user_context)
):
    """Delete a conversation"""
    service = get_openrouter_service()
    success = service.delete_conversation(user_context, conversation_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"success": True, "message": "Conversation deleted successfully"}

def _convert_orchestrator_result(
    orchestrator_result: Dict[str, Any], 
    user_context: UserContext,
    start_time: datetime,
    conversation_id: str | None = None
) -> QueryResponse:
    """Convert orchestrator result to API response format"""
    
    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    # Extract tool results if available
    tool_results = []
    if "tool_results" in orchestrator_result:
        for result in orchestrator_result["tool_results"]:
            tool_results.append(ToolResult(
                tool=result.get("tool", "unknown"),
                success=result.get("success", False),
                data=result.get("data"),
                processing_time_ms=result.get("processing_time_ms", 0),
                citations=result.get("citations", []),
                error=result.get("error")
            ))
    
    # Create analytics data for frontend (if available)
    analytics = []
    if "analytics" in orchestrator_result:
        for item in orchestrator_result["analytics"]:
            analytics.append(AnalyticsData(
                type=item.get("type", "stat"),
                title=item.get("title", "Analysis"),
                data=item.get("data", {}),
                metadata=item.get("metadata", {}),
                clips=item.get("clips")
            ))
    
    # Check for clip data in tool results and add a SINGLE analytics entry (deduplicated)
    clips_models: list[ClipData] = []
    for result in tool_results:
        if hasattr(result, 'tool') and result.tool == "clip_retrieval" and result.success:
            clip_data = result.data or {}
            for clip_dict in clip_data.get("clips", []):
                clips_models.append(ClipData(
                    clip_id=clip_dict.get("clip_id", ""),
                    title=clip_dict.get("title", ""),
                    player_name=clip_dict.get("player_name", ""),
                    game_info=clip_dict.get("game_info", ""),
                    event_type=clip_dict.get("event_type", ""),
                    description=clip_dict.get("description", ""),
                    file_url=clip_dict.get("file_url", ""),
                    thumbnail_url=clip_dict.get("thumbnail_url", ""),
                    duration=clip_dict.get("duration", 0.0),
                    relevance_score=clip_dict.get("relevance_score", 1.0)
                ))

    if clips_models:
        # Deduplicate by clip_id to avoid duplicates from multiple tool entries
        unique_by_id = {}
        for c in clips_models:
            if c.clip_id not in unique_by_id:
                unique_by_id[c.clip_id] = c
        clips_models = list(unique_by_id.values())

        analytics.append(AnalyticsData(
            type="clips",
            title=f"Video Highlights ({len(clips_models)} clips)",
            data={"total_clips": len(clips_models)},
            clips=clips_models
        ))
    
    # Build response
    return QueryResponse(
        success=orchestrator_result.get("success", True),
        response=orchestrator_result.get("response", ""),
        query_type=orchestrator_result.get("query_type"),
        tool_results=tool_results,
        processing_time_ms=orchestrator_result.get("processing_time_ms", processing_time),
        # Be resilient to different keys used upstream
        evidence=orchestrator_result.get("evidence", orchestrator_result.get("evidence_chain", [])),
        citations=_extract_all_citations(tool_results),
        analytics=analytics,
        user_role=user_context.role.value,
        conversation_id=conversation_id,
        timestamp=datetime.now(),
        errors=orchestrator_result.get("errors", []),
        warnings=orchestrator_result.get("warnings", [])
    )

def _extract_all_citations(tool_results: list) -> list:
    """Extract all citations from tool results"""
    citations = []
    for result in tool_results:
        citations.extend(result.citations)
    return list(set(citations))  # Remove duplicates
