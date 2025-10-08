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
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "How is Suzuki performing this season?",
                "context": "Focus on 5v5 play",
                "conversation_id": "conv_12345"
            }
        }

class AnalyticsRequest(BaseModel):
    """Direct analytics request for specific data"""
    metric_type: str = Field(..., description="Type of metric to calculate")
    filters: Optional[dict] = Field(None, description="Filters to apply")
    player_id: Optional[str] = Field(None, description="Specific player to analyze")
    opponent: Optional[str] = Field(None, description="Opponent team filter")
    date_range: Optional[List[str]] = Field(None, description="Date range for analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric_type": "player_performance",
                "filters": {"situation": "5v5", "period": [1, 2, 3]},
                "player_id": "nick_suzuki",
                "date_range": ["2024-10-01", "2024-12-01"]
            }
        }
