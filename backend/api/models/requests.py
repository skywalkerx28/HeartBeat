"""
HeartBeat Engine - API Request Models
Montreal Canadiens Advanced Analytics Assistant

Pydantic models for incoming API requests.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    """User roles for authentication and permissions"""
    COACH = "coach"
    PLAYER = "player" 
    ANALYST = "analyst"
    SCOUT = "scout"
    STAFF = "staff"

class LoginRequest(BaseModel):
    """Authentication request model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

class QueryRequest(BaseModel):
    """Hockey analytics query request"""
    query: str = Field(..., min_length=5, max_length=1000, description="Hockey analytics question")
    context: Optional[str] = Field(None, description="Additional context or follow-up information")
    conversation_id: Optional[str] = Field(
        None,
        description="Client-supplied conversation/thread identifier for memory and continuity"
    )
    mode: Optional[str] = Field(
        None,
        description="Chat mode to control model selection (e.g., general, visual_analysis, contract_finance, fast)"
    )
    model: Optional[str] = Field(
        None,
        description="Explicit model slug (must be allowlisted); overrides mode if provided"
    )
    
class AnalyticsRequest(BaseModel):
    """Direct analytics request for specific data"""
    metric_type: str = Field(..., description="Type of metric to calculate")
    filters: Optional[dict] = Field(None, description="Filters to apply")
    player_id: Optional[str] = Field(None, description="Specific player to analyze")
    opponent: Optional[str] = Field(None, description="Opponent team filter")
    date_range: Optional[List[str]] = Field(None, description="Date range for analysis")
    
    
