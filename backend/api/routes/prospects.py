"""
HeartBeat Engine - Prospects API Routes
Endpoints for prospect data and analytics
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd
from typing import List, Optional
from pydantic import BaseModel
import os
import io
import re

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
    """Load prospects CSV file from local repository (dev fallback)."""
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


def _find_latest_depth_chart_blob(client, bucket, team: str) -> Optional["storage.Blob"]:  # type: ignore
    """Find the latest depth chart blob for a team under silver/dim/depth_charts."""
    prefix = "silver/dim/depth_charts/"
    team_u = team.upper()
    team_l = team.lower()
    blobs = list(client.list_blobs(bucket, prefix=prefix))
    candidates = []
    pat = re.compile(rf"{team_u}_depth_chart_(\d{{4}}_\d{{2}}_\d{{2}})\.(parquet|csv)$", re.IGNORECASE)
    for b in blobs:
        name = b.name.split("/")[-1]
        if team_u in name or team_l in name:
            if pat.search(name):
                candidates.append(b)
    if not candidates:
        return None
    # Sort by filename (date component) and pick last
    candidates.sort(key=lambda b: b.name)
    return candidates[-1]


def _load_depth_chart_from_gcs(team: str) -> Optional[pd.DataFrame]:
    """
    Load the latest depth chart for a team from GCS if GCS_LAKE_BUCKET is set.
    Returns a pandas DataFrame or None on failure/not found.
    """
    bucket_name = os.getenv("GCS_LAKE_BUCKET")
    if not bucket_name:
        return None
    try:
        from google.cloud import storage  # lazy import to keep local dev light
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = _find_latest_depth_chart_blob(client, bucket, team)
        if not blob:
            return None
        data = blob.download_as_bytes()
        # Detect format by extension
        if blob.name.lower().endswith(".parquet"):
            return pd.read_parquet(io.BytesIO(data))
        # Fallback to CSV
        return pd.read_csv(io.BytesIO(data))
    except Exception:
        return None


def _get_first_case_insensitive(row: pd.Series, candidates: List[str]) -> Optional[str]:
    """Return first non-empty value for any candidate column name (case-insensitive)."""
    row_lc = {str(k).strip().lower(): row[k] for k in row.index}
    for name in candidates:
        v = row_lc.get(name.lower())
        if v is not None and str(v).strip() != "":
            return str(v)
    return None

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
        # Prefer depth chart from GCS for production
        df = _load_depth_chart_from_gcs(team_id.upper())
        if df is None:
            # Fallback to local prospects CSV in dev
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
            # Depth chart schema: normalize column names
            name = _get_first_case_insensitive(row, [
                'Name','Player','PlayerName','player','full_name','fullName'
            ])
            if not name or str(name).strip() == '':
                continue
            
            # Parse age
            # Age is often not present in depth charts; default to 0
            try:
                age_val = _get_first_case_insensitive(row, ['Age']) or '0'
                age = int(age_val) if str(age_val).strip().isdigit() else 0
            except Exception:
                age = 0
            
            # Parse draft info
            draft_round, draft_pick, draft_year = parse_draft_info(
                _get_first_case_insensitive(row, ['Draft Round','draft_round','draftRound']) or '',
                _get_first_case_insensitive(row, ['Draft Pick','draft_pick','draftPick']) or '',
                _get_first_case_insensitive(row, ['Draft Year','draft_year','draftYear']) or ''
            )
            
            # Parse UFA year
            ufa_year = parse_ufa_year(_get_first_case_insensitive(row, ['UFA Year','ufa_year']) or '')
            
            position = _get_first_case_insensitive(row, ['Position','Pos','position']) or ''
            shot = _get_first_case_insensitive(row, ['Shot/Catches','Shoots','Catches','shot_catches'])
            height = _get_first_case_insensitive(row, ['Height','height'])
            weight = _get_first_case_insensitive(row, ['Weight','weight'])

            prospect = Prospect(
                name=str(name).strip(),
                age=age,
                position=str(position).strip(),
                shot_catches=str(shot).strip() if shot else None,
                height=str(height).strip() if height else None,
                weight=str(weight).strip() if weight else None,
                draft_round=draft_round,
                draft_pick=draft_pick,
                draft_year=draft_year,
                birthdate=str(_get_first_case_insensitive(row, ['Birthdate','DOB','birthdate']) or '').strip() or None,
                birthplace=str(_get_first_case_insensitive(row, ['Birthplace','birthplace']) or '').strip() or None,
                nationality=str(_get_first_case_insensitive(row, ['Nationality','nationality']) or '').strip() or None,
                sign_by_date=str(_get_first_case_insensitive(row, ['Sign By Date','sign_by_date']) or '').strip() or None,
                ufa_year=ufa_year,
                waivers_eligibility=str(_get_first_case_insensitive(row, ['Waivers Eligibility','waivers_eligibility']) or '').strip() or None,
                est_career_earnings=str(_get_first_case_insensitive(row, ['Est Career Earnings','est_career_earnings']) or '').strip() or None
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

