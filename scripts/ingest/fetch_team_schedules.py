#!/usr/bin/env python3
"""
Fetch NHL Team Season Schedules

Downloads the complete season schedule for all 32 NHL teams using the official
NHL API and stores them in structured JSON format.

API Endpoint: /v1/club-schedule-season/{team}/{season}
Output Directory: data/processed/schedule/{season}/

Author: HeartBeat Engine
Last Updated: 2025-10-11
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('team_schedules_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# NHL API Configuration
NHL_API_BASE_URL = "https://api-web.nhle.com"
REQUEST_DELAY = 0.5  # Delay between requests in seconds to be respectful to API

# All 32 NHL Teams (2024-25 Season)
NHL_TEAMS = {
    # Atlantic Division
    'MTL': {'name': 'Montreal Canadiens', 'id': 8},
    'TOR': {'name': 'Toronto Maple Leafs', 'id': 10},
    'BOS': {'name': 'Boston Bruins', 'id': 6},
    'BUF': {'name': 'Buffalo Sabres', 'id': 7},
    'OTT': {'name': 'Ottawa Senators', 'id': 9},
    'DET': {'name': 'Detroit Red Wings', 'id': 17},
    'FLA': {'name': 'Florida Panthers', 'id': 13},
    'TBL': {'name': 'Tampa Bay Lightning', 'id': 14},
    
    # Metropolitan Division
    'NYR': {'name': 'New York Rangers', 'id': 3},
    'NYI': {'name': 'New York Islanders', 'id': 2},
    'PHI': {'name': 'Philadelphia Flyers', 'id': 4},
    'WSH': {'name': 'Washington Capitals', 'id': 15},
    'CAR': {'name': 'Carolina Hurricanes', 'id': 12},
    'NJD': {'name': 'New Jersey Devils', 'id': 1},
    'CBJ': {'name': 'Columbus Blue Jackets', 'id': 29},
    'PIT': {'name': 'Pittsburgh Penguins', 'id': 5},
    
    # Central Division
    'COL': {'name': 'Colorado Avalanche', 'id': 21},
    'DAL': {'name': 'Dallas Stars', 'id': 25},
    'MIN': {'name': 'Minnesota Wild', 'id': 30},
    'NSH': {'name': 'Nashville Predators', 'id': 18},
    'STL': {'name': 'St. Louis Blues', 'id': 19},
    'WPG': {'name': 'Winnipeg Jets', 'id': 52},
    'CHI': {'name': 'Chicago Blackhawks', 'id': 16},
    'UTA': {'name': 'Utah Hockey Club', 'id': 59},
    
    # Pacific Division
    'VGK': {'name': 'Vegas Golden Knights', 'id': 54},
    'SEA': {'name': 'Seattle Kraken', 'id': 55},
    'LAK': {'name': 'Los Angeles Kings', 'id': 26},
    'SJS': {'name': 'San Jose Sharks', 'id': 28},
    'ANA': {'name': 'Anaheim Ducks', 'id': 24},
    'VAN': {'name': 'Vancouver Canucks', 'id': 23},
    'CGY': {'name': 'Calgary Flames', 'id': 20},
    'EDM': {'name': 'Edmonton Oilers', 'id': 22},
}


def create_session() -> requests.Session:
    """
    Create a requests session with retry logic and proper headers.
    
    Returns:
        Configured requests.Session object
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # Set headers
    session.headers.update({
        'User-Agent': 'HeartBeat-Engine/1.0',
        'Accept': 'application/json'
    })
    
    return session


def fetch_team_schedule(
    session: requests.Session,
    team_code: str,
    season: str
) -> Optional[Dict]:
    """
    Fetch season schedule for a specific team.
    
    Args:
        session: Configured requests session
        team_code: Three-letter team code (e.g., 'MTL', 'TOR')
        season: Season in YYYYYYYY format (e.g., '20242025')
    
    Returns:
        Dictionary containing schedule data, or None if request fails
    """
    url = f"{NHL_API_BASE_URL}/v1/club-schedule-season/{team_code}/{season}"
    
    try:
        logger.info(f"Fetching schedule for {team_code} ({NHL_TEAMS[team_code]['name']})...")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched schedule for {team_code}")
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Schedule not found for {team_code} (season {season})")
        else:
            logger.error(f"HTTP error fetching {team_code}: {e}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching {team_code}: {e}")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {team_code}: {e}")
        return None


def save_schedule(
    data: Dict,
    team_code: str,
    season: str,
    output_dir: Path
) -> bool:
    """
    Save schedule data to JSON file.
    
    Args:
        data: Schedule data dictionary
        team_code: Three-letter team code
        season: Season in YYYYYYYY format
        output_dir: Output directory path
    
    Returns:
        True if save successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        season_dir = output_dir / season
        season_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON file
        output_file = season_dir / f"{team_code}_schedule_{season}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved schedule to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving schedule for {team_code}: {e}")
        return False


def fetch_all_team_schedules(
    season: str = "20242025",
    output_dir: Optional[Path] = None
) -> Dict[str, bool]:
    """
    Fetch and save schedules for all NHL teams.
    
    Args:
        season: Season in YYYYYYYY format (default: current season)
        output_dir: Output directory (default: data/processed/schedule)
    
    Returns:
        Dictionary mapping team codes to success status
    """
    if output_dir is None:
        # Default to data/processed/schedule relative to project root
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "data" / "processed" / "schedule"
    
    logger.info(f"Starting schedule fetch for {len(NHL_TEAMS)} teams")
    logger.info(f"Season: {season}")
    logger.info(f"Output directory: {output_dir}")
    
    session = create_session()
    results = {}
    success_count = 0
    
    for team_code in sorted(NHL_TEAMS.keys()):
        # Fetch schedule
        schedule_data = fetch_team_schedule(session, team_code, season)
        
        if schedule_data:
            # Save to file
            if save_schedule(schedule_data, team_code, season, output_dir):
                results[team_code] = True
                success_count += 1
            else:
                results[team_code] = False
        else:
            results[team_code] = False
        
        # Respectful delay between requests
        time.sleep(REQUEST_DELAY)
    
    # Summary
    logger.info("=" * 70)
    logger.info("SCHEDULE FETCH COMPLETE")
    logger.info(f"Total teams: {len(NHL_TEAMS)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {len(NHL_TEAMS) - success_count}")
    logger.info("=" * 70)
    
    # List failed teams if any
    failed_teams = [code for code, success in results.items() if not success]
    if failed_teams:
        logger.warning(f"Failed teams: {', '.join(failed_teams)}")
    
    return results


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch NHL team season schedules',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--season',
        type=str,
        default='20242025',
        help='Season in YYYYYYYY format (default: 20242025)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Output directory (default: data/processed/schedule)'
    )
    
    args = parser.parse_args()
    
    # Validate season format
    if not (len(args.season) == 8 and args.season.isdigit()):
        logger.error("Season must be in YYYYYYYY format (e.g., 20242025)")
        return 1
    
    # Execute fetch
    start_time = time.time()
    results = fetch_all_team_schedules(
        season=args.season,
        output_dir=args.output_dir
    )
    elapsed_time = time.time() - start_time
    
    logger.info(f"Total execution time: {elapsed_time:.2f} seconds")
    
    # Return non-zero exit code if any failures
    success_count = sum(1 for success in results.values() if success)
    return 0 if success_count == len(NHL_TEAMS) else 1


if __name__ == "__main__":
    exit(main())

