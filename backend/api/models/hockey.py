"""
HeartBeat Engine - Hockey-Specific Models
Montreal Canadiens Advanced Analytics Assistant

Hockey domain-specific data models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class Team(str, Enum):
    """NHL team abbreviations"""
    MTL = "MTL"  # Montreal Canadiens (primary)
    TOR = "TOR"  # Toronto Maple Leafs
    BOS = "BOS"  # Boston Bruins
    OTT = "OTT"  # Ottawa Senators
    # Add other teams as needed

class PlayerPosition(str, Enum):
    """Hockey player positions"""
    C = "C"      # Center
    LW = "LW"    # Left Wing
    RW = "RW"    # Right Wing
    D = "D"      # Defense
    G = "G"      # Goalie

class GameSituation(str, Enum):
    """Game situations for analytics"""
    FIVE_ON_FIVE = "5v5"
    POWER_PLAY = "PP"
    SHORT_HANDED = "SH"
    FOUR_ON_FOUR = "4v4"
    PENALTY_SHOT = "PS"
    EMPTY_NET = "EN"

class QueryCategory(str, Enum):
    """Categories of hockey analytics queries"""
    PLAYER_PERFORMANCE = "player_performance"
    TEAM_ANALYTICS = "team_analytics"
    GAME_ANALYSIS = "game_analysis"
    MATCHUP_COMPARISON = "matchup_comparison"
    TACTICAL_ANALYSIS = "tactical_analysis"
    STATISTICAL_QUERY = "statistical_query"

class PlayerStats(BaseModel):
    """Player statistics model"""
    player_id: str = Field(..., description="Player identifier")
    name: str = Field(..., description="Player name")
    position: PlayerPosition = Field(..., description="Player position")
    
    # Basic stats
    games_played: int = Field(0, description="Games played")
    goals: int = Field(0, description="Goals scored")
    assists: int = Field(0, description="Assists")
    points: int = Field(0, description="Total points")
    
    # Advanced stats
    shots: int = Field(0, description="Shots on goal")
    shooting_percentage: float = Field(0.0, description="Shooting percentage")
    expected_goals: float = Field(0.0, description="Expected goals (xG)")
    plus_minus: int = Field(0, description="Plus/minus rating")
    
    # Time on ice
    toi_per_game: str = Field("00:00", description="Time on ice per game")
    pp_toi: str = Field("00:00", description="Power play time on ice")
    sh_toi: str = Field("00:00", description="Short handed time on ice")

class GameInfo(BaseModel):
    """Game information model"""
    game_id: str = Field(..., description="Unique game identifier")
    date: str = Field(..., description="Game date")
    home_team: Team = Field(..., description="Home team")
    away_team: Team = Field(..., description="Away team")
    
    # Score
    home_score: int = Field(..., description="Home team final score")
    away_score: int = Field(..., description="Away team final score")
    
    # Game state
    period: int = Field(..., description="Current/final period")
    game_state: str = Field(..., description="Game state (final, in_progress, etc.)")
    
    # Key players
    key_players: List[str] = Field(default_factory=list, description="Key players from the game")

class MatchupAnalysis(BaseModel):
    """Team matchup analysis model"""
    team_a: Team = Field(..., description="First team")
    team_b: Team = Field(..., description="Second team")
    
    # Head-to-head record
    wins_a: int = Field(0, description="Team A wins")
    wins_b: int = Field(0, description="Team B wins")
    overtime_games: int = Field(0, description="Games decided in overtime")
    
    # Performance metrics
    avg_goals_for_a: float = Field(0.0, description="Team A average goals for")
    avg_goals_against_a: float = Field(0.0, description="Team A average goals against")
    avg_goals_for_b: float = Field(0.0, description="Team B average goals for") 
    avg_goals_against_b: float = Field(0.0, description="Team B average goals against")
    
    # Advanced metrics
    expected_goals_a: float = Field(0.0, description="Team A expected goals")
    expected_goals_b: float = Field(0.0, description="Team B expected goals")
    
    # Context
    games_analyzed: int = Field(0, description="Number of games in analysis")
    season: str = Field("2024-25", description="Season analyzed")

class ZoneAnalysis(BaseModel):
    """Hockey zone analysis model"""
    zone_type: str = Field(..., description="Zone type (offensive, defensive, neutral)")
    
    # Entry/exit stats
    entries: int = Field(0, description="Zone entries")
    exits: int = Field(0, description="Zone exits") 
    controlled_entries: int = Field(0, description="Controlled zone entries")
    controlled_exits: int = Field(0, description="Controlled zone exits")
    
    # Success rates
    entry_success_rate: float = Field(0.0, description="Zone entry success rate")
    exit_success_rate: float = Field(0.0, description="Zone exit success rate")
    
    # Time-based
    time_in_zone: str = Field("00:00", description="Time spent in zone")
    avg_possession_time: str = Field("00:00", description="Average possession time")
