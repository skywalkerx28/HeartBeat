"""
HeartBeat Engine - News API Models
Pydantic models for news content responses
"""

from pydantic import BaseModel, Field
from datetime import datetime
from datetime import date as DateType
from typing import Optional, List, Dict, Any


class Transaction(BaseModel):
    """NHL transaction model"""
    id: int
    date: DateType = Field(description="Actual transaction date (when event occurred)")
    player_name: str
    player_id: Optional[str] = None
    team_from: Optional[str] = None
    team_to: Optional[str] = None
    transaction_type: str = Field(description="Type: trade, signing, waiver, call-up, etc.")
    description: str
    source_url: Optional[str] = None
    created_at: datetime = Field(description="When we scraped this transaction")


class TeamNews(BaseModel):
    """Team-specific news item"""
    id: int
    team_code: str = Field(description="Three-letter team code (e.g., MTL, TOR)")
    date: DateType = Field(description="News publication date")
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Source metadata (sources, source_count, etc.)")
    created_at: datetime


class GameSummary(BaseModel):
    """NHL game summary"""
    game_id: str
    date: DateType = Field(description="Game date")
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    highlights: Optional[str] = None
    top_performers: List[Dict[str, Any]] = Field(default_factory=list)
    game_recap: Optional[str] = None
    created_at: datetime


class PlayerUpdate(BaseModel):
    """Player performance update"""
    id: int
    player_id: str
    player_name: str
    team_code: Optional[str] = None
    date: DateType = Field(description="Update date")
    summary: str
    recent_stats: Dict[str, Any] = Field(default_factory=dict)
    notable_achievements: List[str] = Field(default_factory=list)
    created_at: datetime


class DailyArticle(BaseModel):
    """AI-generated daily NHL digest"""
    date: DateType = Field(description="Article date")
    title: str
    content: str = Field(description="Full article content")
    summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    source_count: Optional[int] = Field(default=None, description="Number of sources used")
    created_at: datetime


class NewsStats(BaseModel):
    """News content statistics"""
    transactions_24h: int
    games_today: int
    team_news_count: int
    latest_article_date: Optional[DateType] = None
    database_size_mb: Optional[float] = None

