"""
Pydantic models for NHL market analytics API.

Defines data structures for contracts, cap management, trades, and market comparables.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


class PlayerContract(BaseModel):
    """Player contract details with performance metrics."""
    
    nhl_player_id: int = Field(..., description="NHL player ID")
    player_name: str = Field(..., description="Player full name")
    team_abbrev: str = Field(..., description="Team abbreviation")
    position: str = Field(..., description="Player position")
    age: int = Field(..., description="Current age")
    cap_hit: float = Field(..., description="Annual cap hit (AAV)")
    cap_hit_percentage: float = Field(..., description="Percentage of team cap")
    years_remaining: int = Field(..., description="Years remaining on contract")
    contract_type: str = Field(..., description="Contract type (ELC, RFA, UFA, Extension)")
    no_trade_clause: bool = Field(False, description="Has no-trade clause")
    no_movement_clause: bool = Field(False, description="Has no-movement clause")
    contract_status: str = Field("active", description="Contract status")
    
    # Performance metrics
    performance_index: Optional[float] = Field(None, description="Composite performance score")
    contract_efficiency: Optional[float] = Field(None, description="Performance / cap hit ratio")
    market_value: Optional[float] = Field(None, description="Estimated fair market value")
    surplus_value: Optional[float] = Field(None, description="Market value - cap hit")
    status: Optional[str] = Field(None, description="overperforming, fair, underperforming")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nhl_player_id": 8480018,
                "player_name": "Nick Suzuki",
                "team_abbrev": "MTL",
                "position": "C",
                "age": 25,
                "cap_hit": 7875000,
                "cap_hit_percentage": 9.5,
                "years_remaining": 6,
                "contract_type": "UFA",
                "no_trade_clause": False,
                "no_movement_clause": True,
                "contract_status": "active",
                "performance_index": 135.2,
                "contract_efficiency": 1.42,
                "market_value": 9200000,
                "surplus_value": 1325000,
                "status": "overperforming"
            }
        }


class ContractEfficiencyComponent(BaseModel):
    """Individual component of contract efficiency calculation."""
    
    points_value: Optional[float] = None
    xg_value: Optional[float] = None
    defensive_value: Optional[float] = None
    age_adjustment: Optional[float] = None
    term_penalty: Optional[float] = None


class ContractEfficiency(BaseModel):
    """Detailed contract efficiency analysis."""
    
    nhl_player_id: int
    player_name: str
    contract_efficiency: float = Field(..., description="Overall efficiency index (0-200)")
    market_value: float = Field(..., description="Estimated fair market value")
    surplus_value: float = Field(..., description="Annual surplus/deficit")
    status: str = Field(..., description="overperforming, fair, underperforming")
    percentile: float = Field(..., description="Efficiency percentile (0-100)")
    components: ContractEfficiencyComponent


class TeamCapSummary(BaseModel):
    """Team salary cap summary with projections."""
    
    team_abbrev: str = Field(..., description="Team abbreviation")
    season: str = Field(..., description="Season")
    cap_ceiling: float = Field(..., description="Salary cap ceiling")
    cap_space: float = Field(..., description="Available cap space")
    cap_hit_total: float = Field(..., description="Total cap hit")
    ltir_pool: float = Field(0, description="LTIR relief pool")
    deadline_cap_space: float = Field(..., description="Projected deadline cap space")
    active_contracts: int = Field(..., description="Number of active contracts")
    contracts_expiring: int = Field(..., description="Contracts expiring this season")
    
    # Optional contract details
    contracts: Optional[List[PlayerContract]] = Field(None, description="Team contract list")
    
    # Multi-year projections
    projections: Optional[List[Dict[str, Any]]] = Field(None, description="Future season projections")
    
    class Config:
        json_schema_extra = {
            "example": {
                "team_abbrev": "MTL",
                "season": "2025-2026",
                "cap_ceiling": 92000000,
                "cap_space": 5200000,
                "cap_hit_total": 86800000,
                "ltir_pool": 0,
                "deadline_cap_space": 8500000,
                "active_contracts": 21,
                "contracts_expiring": 5
            }
        }


class ContractComparable(BaseModel):
    """Comparable contract for market analysis."""
    
    player_id: int = Field(..., description="NHL player ID")
    player_name: str = Field(..., description="Player full name")
    team: str = Field(..., description="Team abbreviation")
    position: str = Field(..., description="Position")
    cap_hit: float = Field(..., description="Annual cap hit")
    age_at_signing: int = Field(..., description="Age when contract was signed")
    contract_years: int = Field(..., description="Total contract length")
    production_last_season: float = Field(..., description="Production metric")
    similarity_score: float = Field(..., description="Similarity score (0-100)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "player_id": 8478420,
                "player_name": "Sebastian Aho",
                "team": "CAR",
                "position": "C",
                "cap_hit": 8460250,
                "age_at_signing": 21,
                "contract_years": 5,
                "production_last_season": 83.0,
                "similarity_score": 87.5
            }
        }


class TradePlayer(BaseModel):
    """Player involved in a trade."""
    
    player_id: int
    player_name: str
    from_team: str
    to_team: str


class TradePick(BaseModel):
    """Draft pick involved in a trade."""
    
    year: int
    round: int
    from_team: str
    to_team: str
    conditions: Optional[str] = None


class TradeCapImpact(BaseModel):
    """Cap impact for a team in a trade."""
    
    team: str
    cap_change: float  # Positive = cap relief, negative = cap added


class Trade(BaseModel):
    """NHL trade with cap implications."""
    
    trade_id: str = Field(..., description="Unique trade identifier")
    trade_date: date = Field(..., description="Date of trade")
    season: str = Field(..., description="Season")
    teams_involved: List[str] = Field(..., description="Team abbreviations")
    players_moved: List[TradePlayer] = Field(..., description="Players traded")
    draft_picks_moved: Optional[List[TradePick]] = Field(None, description="Draft picks traded")
    cap_implications: List[TradeCapImpact] = Field(..., description="Cap impact per team")
    trade_type: str = Field(..., description="Trade classification")
    trade_deadline: bool = Field(False, description="Trade deadline deal")
    
    class Config:
        json_schema_extra = {
            "example": {
                "trade_id": "2025-trade-001",
                "trade_date": "2025-03-01",
                "season": "2024-2025",
                "teams_involved": ["MTL", "TOR"],
                "players_moved": [
                    {
                        "player_id": 8477493,
                        "player_name": "Joel Armia",
                        "from_team": "MTL",
                        "to_team": "TOR"
                    }
                ],
                "cap_implications": [
                    {"team": "MTL", "cap_change": 3400000},
                    {"team": "TOR", "cap_change": -3400000}
                ],
                "trade_type": "player_for_picks",
                "trade_deadline": True
            }
        }


class MarketTierBreakdown(BaseModel):
    """Market tier breakdown by position."""
    
    elite_count: int = Field(..., description="Number of elite contracts")
    elite_avg: float = Field(..., description="Average elite contract value")
    top_line_count: int = Field(..., description="Top line contract count")
    top_line_avg: float = Field(..., description="Average top line value")
    middle_count: int = Field(..., description="Middle tier count")
    middle_avg: float = Field(..., description="Average middle tier value")
    bottom_count: int = Field(..., description="Bottom tier count")
    bottom_avg: float = Field(..., description="Average bottom tier value")


class PositionMarketSummary(BaseModel):
    """Market summary for a specific position."""
    
    position: str = Field(..., description="Position (C, RW, LW, D, G)")
    total_contracts: int = Field(..., description="Total active contracts")
    avg_cap_hit: float = Field(..., description="Average cap hit")
    median_cap_hit: float = Field(..., description="Median cap hit")
    min_cap_hit: float = Field(..., description="Minimum cap hit")
    max_cap_hit: float = Field(..., description="Maximum cap hit")
    tier_breakdown: Optional[MarketTierBreakdown] = None


class LeagueMarketOverview(BaseModel):
    """League-wide market statistics."""
    
    season: str = Field(..., description="Season")
    positions: List[PositionMarketSummary] = Field(..., description="Position breakdowns")
    total_contracts: int = Field(..., description="Total league contracts")
    avg_contract_value: float = Field(..., description="League average contract")
    last_updated: datetime = Field(..., description="Last update timestamp")


class ContractAlert(BaseModel):
    """Contract alert for upcoming decisions."""
    
    player_id: int
    player_name: str
    team_abbrev: str
    alert_type: str = Field(..., description="expiring, rfa_eligible, ufa_eligible, arbitration")
    contract_end_date: date
    estimated_market_value: Optional[float] = None
    current_cap_hit: float
    priority: str = Field(..., description="high, medium, low")


class MarketAnalyticsResponse(BaseModel):
    """Generic market analytics response wrapper."""
    
    success: bool = Field(True, description="Request success status")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    source: str = Field("bigquery", description="Data source (bigquery, parquet, cache)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

