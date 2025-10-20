#!/usr/bin/env python3
"""
Fetch NHL Team Rosters by Season

Downloads complete team rosters for all 32 NHL teams across multiple seasons
using the official NHL API and stores them in structured JSON format.

API Endpoint: /v1/roster/{team}/{season}
Output Directory: data/processed/rosters/{team}/{season}/

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
        logging.FileHandler('team_rosters_fetch.log'),
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

# Default seasons to fetch (last 3 seasons)
DEFAULT_SEASONS = ['20252026', '20242025', '20232024']


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


def fetch_team_roster(
    session: requests.Session,
    team_code: str,
    season: str
) -> Optional[Dict]:
    """
    Fetch roster for a specific team and season.
    
    Args:
        session: Configured requests session
        team_code: Three-letter team code (e.g., 'MTL', 'TOR')
        season: Season in YYYYYYYY format (e.g., '20242025')
    
    Returns:
        Dictionary containing roster data, or None if request fails
    """
    url = f"{NHL_API_BASE_URL}/v1/roster/{team_code}/{season}"
    
    try:
        logger.info(f"Fetching roster for {team_code} ({season})...")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched roster for {team_code} ({season})")
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Roster not found for {team_code} (season {season})")
        else:
            logger.error(f"HTTP error fetching {team_code} ({season}): {e}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching {team_code} ({season}): {e}")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {team_code} ({season}): {e}")
        return None


def save_roster(
    data: Dict,
    team_code: str,
    season: str,
    output_dir: Path
) -> bool:
    """
    Save roster data to JSON file.
    
    Args:
        data: Roster data dictionary
        team_code: Three-letter team code
        season: Season in YYYYYYYY format
        output_dir: Output directory path
    
    Returns:
        True if save successful, False otherwise
    """
    try:
        # Create team/season directory structure
        team_season_dir = output_dir / team_code / season
        team_season_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON file
        output_file = team_season_dir / f"{team_code}_roster_{season}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved roster to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving roster for {team_code} ({season}): {e}")
        return False


def fetch_all_team_rosters(
    seasons: Optional[List[str]] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Dict[str, bool]]:
    """
    Fetch and save rosters for all NHL teams across multiple seasons.
    
    Args:
        seasons: List of seasons in YYYYYYYY format (default: last 3 seasons)
        output_dir: Output directory (default: data/processed/rosters)
    
    Returns:
        Dictionary mapping team codes to season results
    """
    if seasons is None:
        seasons = DEFAULT_SEASONS
    
    if output_dir is None:
        # Default to data/processed/rosters relative to project root
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "data" / "processed" / "rosters"
    
    logger.info("=" * 70)
    logger.info("STARTING NHL TEAM ROSTER FETCH")
    logger.info(f"Teams: {len(NHL_TEAMS)}")
    logger.info(f"Seasons: {', '.join(seasons)}")
    logger.info(f"Total requests: {len(NHL_TEAMS) * len(seasons)}")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 70)
    
    session = create_session()
    results = {team: {} for team in NHL_TEAMS.keys()}
    total_success = 0
    total_requests = len(NHL_TEAMS) * len(seasons)
    
    # Process each season
    for season in seasons:
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING SEASON: {season}")
        logger.info(f"{'='*70}")
        
        season_success = 0
        
        for team_code in sorted(NHL_TEAMS.keys()):
            # Fetch roster
            roster_data = fetch_team_roster(session, team_code, season)
            
            if roster_data:
                # Save to file
                if save_roster(roster_data, team_code, season, output_dir):
                    results[team_code][season] = True
                    season_success += 1
                    total_success += 1
                else:
                    results[team_code][season] = False
            else:
                results[team_code][season] = False
            
            # Respectful delay between requests
            time.sleep(REQUEST_DELAY)
        
        logger.info(f"\nSeason {season} complete: {season_success}/{len(NHL_TEAMS)} successful")
    
    # Final Summary
    logger.info("\n" + "=" * 70)
    logger.info("ROSTER FETCH COMPLETE")
    logger.info(f"Total requests: {total_requests}")
    logger.info(f"Successful: {total_success}")
    logger.info(f"Failed: {total_requests - total_success}")
    logger.info(f"Success rate: {(total_success / total_requests * 100):.1f}%")
    logger.info("=" * 70)
    
    # List failed fetches if any
    failed_fetches = []
    for team_code, season_results in results.items():
        for season, success in season_results.items():
            if not success:
                failed_fetches.append(f"{team_code}/{season}")
    
    if failed_fetches:
        logger.warning(f"\nFailed fetches ({len(failed_fetches)}):")
        for fetch in failed_fetches:
            logger.warning(f"  - {fetch}")
    
    return results


def generate_summary_report(
    results: Dict[str, Dict[str, bool]],
    output_dir: Path
) -> None:
    """
    Generate a summary report of the roster fetch operation.
    
    Args:
        results: Dictionary of results from fetch_all_team_rosters
        output_dir: Output directory for the report
    """
    try:
        report_file = output_dir / "fetch_summary.json"
        
        summary = {
            "fetch_timestamp": datetime.now().isoformat(),
            "total_teams": len(NHL_TEAMS),
            "seasons_fetched": list(set(season for team_results in results.values() 
                                       for season in team_results.keys())),
            "results_by_team": {},
            "results_by_season": {},
            "failed_fetches": []
        }
        
        # Organize by team
        for team_code, season_results in results.items():
            successful_seasons = [s for s, success in season_results.items() if success]
            summary["results_by_team"][team_code] = {
                "team_name": NHL_TEAMS[team_code]["name"],
                "successful_seasons": successful_seasons,
                "failed_seasons": [s for s in season_results.keys() if s not in successful_seasons],
                "success_count": len(successful_seasons),
                "total_seasons": len(season_results)
            }
        
        # Organize by season
        all_seasons = set(season for team_results in results.values() 
                         for season in team_results.keys())
        
        for season in sorted(all_seasons):
            successful_teams = [team for team, season_results in results.items() 
                              if season_results.get(season, False)]
            summary["results_by_season"][season] = {
                "successful_teams": successful_teams,
                "failed_teams": [team for team in results.keys() if team not in successful_teams],
                "success_count": len(successful_teams),
                "total_teams": len(NHL_TEAMS)
            }
        
        # List all failures
        for team_code, season_results in results.items():
            for season, success in season_results.items():
                if not success:
                    summary["failed_fetches"].append({
                        "team": team_code,
                        "team_name": NHL_TEAMS[team_code]["name"],
                        "season": season
                    })
        
        # Write summary
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nSummary report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Error generating summary report: {e}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch NHL team rosters for multiple seasons',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--seasons',
        type=str,
        nargs='+',
        default=DEFAULT_SEASONS,
        help='Seasons in YYYYYYYY format (default: 20252026 20242025 20232024)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Output directory (default: data/processed/rosters)'
    )
    
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip generating summary report'
    )
    
    args = parser.parse_args()
    
    # Validate season formats
    for season in args.seasons:
        if not (len(season) == 8 and season.isdigit()):
            logger.error(f"Invalid season format: {season}. Must be YYYYYYYY (e.g., 20242025)")
            return 1
    
    # Execute fetch
    start_time = time.time()
    results = fetch_all_team_rosters(
        seasons=args.seasons,
        output_dir=args.output_dir
    )
    elapsed_time = time.time() - start_time
    
    logger.info(f"\nTotal execution time: {elapsed_time:.2f} seconds")
    
    # Generate summary report
    if not args.no_summary:
        output_dir = args.output_dir or Path(__file__).parent.parent / "data" / "processed" / "rosters"
        generate_summary_report(results, output_dir)
    
    # Return non-zero exit code if any failures
    total_success = sum(1 for team_results in results.values() 
                       for success in team_results.values() if success)
    total_requests = len(NHL_TEAMS) * len(args.seasons)
    
    return 0 if total_success == total_requests else 1


if __name__ == "__main__":
    exit(main())

