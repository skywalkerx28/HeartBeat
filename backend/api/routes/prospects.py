"""
HeartBeat Engine - Prospects API Routes
Endpoints for prospect data and analytics
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/prospects", tags=["prospects"])

class Prospect(BaseModel):
    """Prospect data model"""
    name: str
    age: int
    position: str
    shot_catches: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None
    draft_year: Optional[int] = None
    birthdate: Optional[str] = None
    birthplace: Optional[str] = None
    nationality: Optional[str] = None
    sign_by_date: Optional[str] = None
    ufa_year: Optional[int] = None
    waivers_eligibility: Optional[str] = None
    est_career_earnings: Optional[str] = None

class ProspectsResponse(BaseModel):
    """Response model for prospects endpoint"""
    prospects: List[Prospect]
    total: int
    team: str
    season: str

def load_prospects_csv(team: str = "MTL", season: str = "20252026") -> pd.DataFrame:
    """Load prospects CSV file"""
    prospects_path = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "rosters" / team / season / "prospects" / f"{team.lower()}_prospects_{season[0:4]}{season[4:6]}{season[6:8]}.csv"
    
    # Try different date formats
    if not prospects_path.exists():
        # Try to find any prospects file for this team/season
        prospect_dir = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "rosters" / team / season / "prospects"
        if prospect_dir.exists():
            csv_files = list(prospect_dir.glob(f"{team.lower()}_prospects_*.csv"))
            if csv_files:
                prospects_path = csv_files[0]  # Use the first found
    
    if not prospects_path.exists():
        raise HTTPException(status_code=404, detail=f"Prospects file not found for {team} {season}")
    
    df = pd.read_csv(prospects_path)
    
    # Clean up the dataframe
    df = df.dropna(how='all')  # Remove empty rows
    df = df.fillna('')  # Fill NaN with empty strings
    
    return df

def parse_draft_info(draft_round: str, draft_pick: str, draft_year: str):
    """Parse draft information from CSV strings"""
    try:
        round_val = int(draft_round) if draft_round and str(draft_round).strip() else None
    except (ValueError, TypeError):
        round_val = None
    
    try:
        pick_val = int(draft_pick) if draft_pick and str(draft_pick).strip() else None
    except (ValueError, TypeError):
        pick_val = None
    
    try:
        year_val = int(draft_year) if draft_year and str(draft_year).strip() else None
    except (ValueError, TypeError):
        year_val = None
    
    return round_val, pick_val, year_val

def parse_ufa_year(ufa_str: str):
    """Parse UFA year from CSV"""
    try:
        return int(ufa_str) if ufa_str and str(ufa_str).strip() else None
    except (ValueError, TypeError):
        return None

@router.get("/team/{team_id}", response_model=ProspectsResponse)
async def get_team_prospects(
    team_id: str,
    season: str = "20252026",
    position: Optional[str] = None
):
    """
    Get prospects for a specific team
    
    - **team_id**: Team abbreviation (e.g., MTL)
    - **season**: Season in format YYYYMMDD (default: 20252026)
    - **position**: Filter by position (F, D, G)
    """
    try:
        df = load_prospects_csv(team_id.upper(), season)
        
        # Filter by position if provided
        if position:
            if position == 'F':
                # Include all forward positions
                df = df[df['Position'].str.contains('C|W|LW|RW', case=False, na=False)]
            elif position == 'D':
                df = df[df['Position'].str.contains('D', case=False, na=False)]
            elif position == 'G':
                df = df[df['Position'].str.contains('G', case=False, na=False)]
        
        prospects = []
        for _, row in df.iterrows():
            if not row.get('Name') or str(row.get('Name')).strip() == '':
                continue
            
            # Parse age
            try:
                age = int(row.get('Age', 0)) if row.get('Age') else 0
            except (ValueError, TypeError):
                age = 0
            
            # Parse draft info
            draft_round, draft_pick, draft_year = parse_draft_info(
                row.get('Draft Round', ''),
                row.get('Draft Pick', ''),
                row.get('Draft Year', '')
            )
            
            # Parse UFA year
            ufa_year = parse_ufa_year(row.get('UFA Year', ''))
            
            prospect = Prospect(
                name=str(row.get('Name', '')).strip(),
                age=age,
                position=str(row.get('Position', '')).strip(),
                shot_catches=str(row.get('Shot/Catches', '')).strip() if row.get('Shot/Catches') else None,
                height=str(row.get('Height', '')).strip() if row.get('Height') else None,
                weight=str(row.get('Weight', '')).strip() if row.get('Weight') else None,
                draft_round=draft_round,
                draft_pick=draft_pick,
                draft_year=draft_year,
                birthdate=str(row.get('Birthdate', '')).strip() if row.get('Birthdate') else None,
                birthplace=str(row.get('Birthplace', '')).strip() if row.get('Birthplace') else None,
                nationality=str(row.get('Nationality', '')).strip() if row.get('Nationality') else None,
                sign_by_date=str(row.get('Sign By Date', '')).strip() if row.get('Sign By Date') else None,
                ufa_year=ufa_year,
                waivers_eligibility=str(row.get('Waivers Eligibility', '')).strip() if row.get('Waivers Eligibility') else None,
                est_career_earnings=str(row.get('Est Career Earnings', '')).strip() if row.get('Est Career Earnings') else None
            )
            prospects.append(prospect)
        
        return ProspectsResponse(
            prospects=prospects,
            total=len(prospects),
            team=team_id.upper(),
            season=season
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading prospects: {str(e)}")

@router.get("/team/{team_id}/position/{position}", response_model=ProspectsResponse)
async def get_team_prospects_by_position(
    team_id: str,
    position: str,
    season: str = "20252026"
):
    """
    Get prospects for a specific team filtered by position
    
    - **team_id**: Team abbreviation (e.g., MTL)
    - **position**: Position filter (F, D, G)
    - **season**: Season in format YYYYMMDD (default: 20252026)
    """
    return await get_team_prospects(team_id, season, position)

