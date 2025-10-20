#!/usr/bin/env python3
"""
Fetch Arizona Coyotes Historical Rosters for Utah Hockey Club

Fetches Arizona Coyotes roster data for seasons 2015-2016 through 2022-2023
and saves them under the UTA directory since Utah is the successor franchise.

This completes the 10-year roster history for the Utah Hockey Club.

API Endpoint: /v1/roster/ARI/{season}
Output Directory: data/processed/rosters/UTA/{season}/

Author: HeartBeat Engine
Date: October 2025
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arizona_rosters_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

NHL_API_BASE_URL = "https://api-web.nhle.com"
REQUEST_DELAY = 0.5

ARIZONA_SEASONS = [
    '20152016',
    '20162017',
    '20172018',
    '20182019',
    '20192020',
    '20202021',
    '20212022',
    '20222023'
]


def create_session() -> requests.Session:
    """Create a requests session with retry logic and proper headers."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    session.headers.update({
        'User-Agent': 'HeartBeat-Engine/1.0',
        'Accept': 'application/json'
    })
    
    return session


def fetch_arizona_roster(
    session: requests.Session,
    season: str
) -> Optional[Dict]:
    """
    Fetch Arizona Coyotes roster for a specific season.
    
    Args:
        session: Configured requests session
        season: Season in YYYYYYYY format
    
    Returns:
        Dictionary containing roster data, or None if request fails
    """
    url = f"{NHL_API_BASE_URL}/v1/roster/ARI/{season}"
    
    try:
        logger.info(f"Fetching Arizona Coyotes roster for {season}...")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched Arizona roster for {season}")
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Arizona roster not found for season {season}")
        else:
            logger.error(f"HTTP error fetching Arizona ({season}): {e}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching Arizona ({season}): {e}")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for Arizona ({season}): {e}")
        return None


def save_roster_as_utah(
    data: Dict,
    season: str,
    output_dir: Path
) -> bool:
    """
    Save Arizona roster data under UTA directory structure.
    
    Args:
        data: Roster data dictionary
        season: Season in YYYYYYYY format
        output_dir: Output directory path
    
    Returns:
        True if save successful, False otherwise
    """
    try:
        uta_season_dir = output_dir / "UTA" / season
        uta_season_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = uta_season_dir / f"UTA_roster_{season}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        player_count = 0
        if isinstance(data, dict):
            for position in ['forwards', 'defensemen', 'goalies']:
                if position in data:
                    player_count += len(data[position])
        
        logger.info(f"Saved Arizona roster as UTA to {output_file} ({player_count} players)")
        return True
        
    except Exception as e:
        logger.error(f"Error saving roster for {season}: {e}")
        return False


def fetch_all_arizona_rosters(
    output_dir: Optional[Path] = None
) -> Dict[str, bool]:
    """
    Fetch and save all historical Arizona rosters under UTA directory.
    
    Args:
        output_dir: Output directory (default: data/processed/rosters)
    
    Returns:
        Dictionary mapping seasons to success status
    """
    if output_dir is None:
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "data" / "processed" / "rosters"
    
    logger.info("=" * 80)
    logger.info("FETCHING ARIZONA COYOTES HISTORICAL ROSTERS FOR UTAH HOCKEY CLUB")
    logger.info(f"Seasons: {len(ARIZONA_SEASONS)} ({ARIZONA_SEASONS[0]} to {ARIZONA_SEASONS[-1]})")
    logger.info(f"Saving under: UTA directory structure")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 80)
    
    session = create_session()
    results = {}
    total_success = 0
    
    for season in ARIZONA_SEASONS:
        logger.info(f"\nProcessing season: {season}")
        
        roster_data = fetch_arizona_roster(session, season)
        
        if roster_data:
            if save_roster_as_utah(roster_data, season, output_dir):
                results[season] = True
                total_success += 1
            else:
                results[season] = False
        else:
            results[season] = False
        
        time.sleep(REQUEST_DELAY)
    
    logger.info("\n" + "=" * 80)
    logger.info("ARIZONA HISTORICAL ROSTER FETCH COMPLETE")
    logger.info(f"Total seasons: {len(ARIZONA_SEASONS)}")
    logger.info(f"Successful: {total_success}")
    logger.info(f"Failed: {len(ARIZONA_SEASONS) - total_success}")
    logger.info(f"Success rate: {(total_success / len(ARIZONA_SEASONS) * 100):.1f}%")
    logger.info("=" * 80)
    
    failed_seasons = [season for season, success in results.items() if not success]
    if failed_seasons:
        logger.warning(f"\nFailed seasons: {', '.join(failed_seasons)}")
    
    return results


def verify_uta_roster_completion(output_dir: Path) -> None:
    """Verify that UTA now has complete 10-year roster history."""
    uta_dir = output_dir / "UTA"
    
    if not uta_dir.exists():
        logger.error("UTA directory not found!")
        return
    
    seasons = sorted([d.name for d in uta_dir.iterdir() if d.is_dir()])
    
    logger.info("\n" + "=" * 80)
    logger.info("UTA ROSTER HISTORY VERIFICATION")
    logger.info("=" * 80)
    logger.info(f"Total seasons available: {len(seasons)}")
    logger.info("\nSeasons:")
    
    for season in seasons:
        roster_file = uta_dir / season / f"UTA_roster_{season}.json"
        if roster_file.exists():
            with open(roster_file, 'r') as f:
                data = json.load(f)
                player_count = 0
                if isinstance(data, dict):
                    for position in ['forwards', 'defensemen', 'goalies']:
                        if position in data:
                            player_count += len(data[position])
                
                season_display = f"{season[:4]}-{season[4:]}"
                source = "Utah HC" if int(season[:4]) >= 2023 else "Arizona Coyotes"
                logger.info(f"  {season_display}: {player_count} players (from {source})")
        else:
            logger.warning(f"  {season}: FILE MISSING")
    
    logger.info("=" * 80)
    
    expected_seasons = 10
    if len(seasons) >= expected_seasons:
        logger.info(f"SUCCESS: UTA has {len(seasons)}/{expected_seasons}+ years of roster history")
    else:
        logger.warning(f"INCOMPLETE: UTA has only {len(seasons)}/{expected_seasons} years of roster history")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch Arizona Coyotes historical rosters for Utah Hockey Club',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Output directory (default: data/processed/rosters)'
    )
    
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing UTA roster completion'
    )
    
    args = parser.parse_args()
    
    output_dir = args.output_dir or Path(__file__).parent.parent / "data" / "processed" / "rosters"
    
    if args.verify_only:
        verify_uta_roster_completion(output_dir)
        return 0
    
    start_time = time.time()
    results = fetch_all_arizona_rosters(output_dir=output_dir)
    elapsed_time = time.time() - start_time
    
    logger.info(f"\nTotal execution time: {elapsed_time:.2f} seconds")
    
    verify_uta_roster_completion(output_dir)
    
    total_success = sum(1 for success in results.values() if success)
    return 0 if total_success == len(ARIZONA_SEASONS) else 1


if __name__ == "__main__":
    exit(main())

