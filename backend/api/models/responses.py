"""
HeartBeat Engine - API Response Models
Montreal Canadiens Advanced Analytics Assistant

Pydantic models for API responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool
    access_token: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None
    message: str
    expires_in: Optional[int] = Field(None, description="Token expiration in seconds")

class ToolResult(BaseModel):
    """Tool execution result"""
    tool: str = Field(..., description="Tool that was executed")
    success: bool = Field(..., description="Whether tool executed successfully")
    data: Optional[Any] = Field(None, description="Tool output data")
    processing_time_ms: int = Field(..., description="Tool execution time in milliseconds")
    citations: List[str] = Field(default_factory=list, description="Data sources and citations")
    error: Optional[str] = Field(None, description="Error message if tool failed")

class ClipData(BaseModel):
    """Video clip data model"""
    clip_id: str = Field(..., description="Unique clip identifier")
    title: str = Field(..., description="Clip title")
    player_name: str = Field(..., description="Player featured in clip")
    game_info: str = Field(..., description="Game information")
    event_type: str = Field(..., description="Type of event (goal, assist, save, etc.)")
    description: str = Field(..., description="Clip description")
    file_url: str = Field(..., description="URL to video file")
    thumbnail_url: str = Field(..., description="URL to thumbnail image")
    duration: float = Field(..., description="Clip duration in seconds")
    relevance_score: Optional[float] = Field(None, description="Relevance score for search query")

class AnalyticsData(BaseModel):
    """Analytics data for frontend display"""
    type: str = Field(..., description="Type of analytics (stat, chart, table, clips)")
    title: str = Field(..., description="Display title")
    data: Any = Field(..., description="Analytics data payload")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    clips: Optional[List[ClipData]] = Field(None, description="Video clips data (when type=clips)")

class QueryResponse(BaseModel):
    """Main query response model"""
    success: bool = Field(..., description="Whether query was processed successfully")
    response: str = Field(..., description="Main response text from Stanley")
    query_type: Optional[str] = Field(None, description="Classified query type")
    
    # Tool and processing information
    tool_results: List[ToolResult] = Field(default_factory=list, description="Results from tool execution")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    
    # Evidence and citations
    evidence: List[str] = Field(default_factory=list, description="Evidence supporting the response")
    citations: List[str] = Field(default_factory=list, description="Data sources and citations")
    
    # Analytics for frontend display
    analytics: List[AnalyticsData] = Field(default_factory=list, description="Analytics data for visualization")
    
    # User and session info
    user_role: str = Field(..., description="Role of the requesting user")
    conversation_id: Optional[str] = Field(None, description="Conversation/thread identifier for continuity")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Non-fatal errors during processing")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "response": "Nick Suzuki has been performing exceptionally well this season...",
                "query_type": "player_performance",
                "tool_results": [
                    {
                        "tool": "vector_search",
                        "success": True,
                        "processing_time_ms": 120,
                        "citations": ["game_recap:events", "hockey_knowledge:analytics"]
                    }
                ],
                "processing_time_ms": 1250,
                "evidence": ["Recent game data from Vertex vector search"],
                "analytics": [
                    {
                        "type": "stat",
                        "title": "Season Performance", 
                        "data": {"goals": 12, "assists": 18, "points": 30}
                    }
                ],
                "user_role": "analyst",
                "errors": [],
                "warnings": []
            }
        }

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    processing_time_ms: int = Field(..., description="Time taken before error occurred")
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    orchestrator_available: bool = Field(..., description="Whether orchestrator is available")
    vertex_configured: bool = Field(..., description="Whether Vertex Vector Search is configured")
    data_directory_exists: bool = Field(..., description="Whether data directory exists")
    configuration_valid: bool = Field(..., description="Whether configuration is valid")
    version: str = Field("2.1.0", description="API version")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
