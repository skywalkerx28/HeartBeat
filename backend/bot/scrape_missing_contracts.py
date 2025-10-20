"""
Scrape missing contracts for non-roster (AHL) players from depth chart database

This script:
1. Fetches all non-roster players from the depth chart database
2. Checks which ones don't have contract data in data/contracts/
3. Scrapes their contracts from CapWages

Usage:
    python -m backend.bot.scrape_missing_contracts --all
    python -m backend.bot.scrape_missing_contracts --team MTL
    python -m backend.bot.scrape_missing_contracts --limit 10
"""

import argparse
import logging
import time
from pathlib import Path
from typing import List, Dict, Set
import re

from . import db
from .contract_exporter import export_to_database_and_csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def player_name_to_slug(player_name: str) -> str:
    """
    Convert player name to CapWages URL slug format
    
    Examples:
        "Beck, Owen" -> "owen-beck"
        "Roy, Joshua" -> "joshua-roy"
    """
    # Handle "Last, First" format
    if ',' in player_name:
        parts = player_name.split(',')
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ''
        player_name = f"{first_name} {last_name}"
    
    # Convert to lowercase
    slug = player_name.lower()
    
    # Remove special characters except spaces and hyphens
    slug = re.sub(r'[^a-z0-9\s\-]', '', slug)
    
    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')
    
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


def get_existing_contract_player_ids(contracts_dir: str = 'data/contracts') -> Set[str]:
    """
    Get set of player IDs that already have contract CSV files
    
    Returns:
        Set of player_id strings that have contracts
    """
    contracts_path = Path(contracts_dir)
    if not contracts_path.exists():
        return set()
    
    player_ids = set()
    
    # Look for CSV files with player IDs in the format: lastname_playerid_contracts_timestamp.csv
    for csv_file in contracts_path.glob('*_contracts_*.csv'):
        # Extract player_id from filename
        # Format: lastname_playerid_contracts_timestamp.csv
        filename = csv_file.stem  # Remove .csv
        parts = filename.split('_')
        
        # Player ID should be the second part (after lastname)
        if len(parts) >= 2 and parts[1].isdigit():
            player_ids.add(parts[1])
    
    logger.info(f"Found {len(player_ids)} existing contract files")
    return player_ids


def get_non_roster_players_without_contracts(
    team_code: str = None,
    existing_contract_ids: Set[str] = None
) -> List[Dict]:
    """
    Get list of non-roster players that don't have contract data yet
    
    Args:
        team_code: Optional team filter (e.g., 'MTL')
        existing_contract_ids: Set of player IDs that already have contracts
    
    Returns:
        List of player dicts that need contracts scraped
    """
    if existing_contract_ids is None:
        existing_contract_ids = get_existing_contract_player_ids()
    
    with db.get_connection(read_only=True) as conn:
        if team_code:
            # Get non-roster players for specific team
            roster = db.get_team_roster(conn, team_code.upper(), latest_only=True)
            non_roster_players = [
                p for p in roster 
                if p.get('roster_status') == 'non_roster'
            ]
        else:
            # Get all non-roster players across all teams
            result = conn.execute("""
                SELECT DISTINCT 
                    player_id, player_name, team_code, position, age
                FROM team_rosters
                WHERE roster_status = 'non_roster'
                    AND scraped_date = (
                        SELECT MAX(scraped_date) FROM team_rosters
                    )
                ORDER BY team_code, player_name
            """).fetchall()
            
            non_roster_players = [
                {
                    'player_id': row[0],
                    'player_name': row[1],
                    'team_code': row[2],
                    'position': row[3],
                    'age': row[4]
                }
                for row in result
            ]
    
    # Filter out players that already have contracts
    players_without_contracts = []
    for player in non_roster_players:
        player_id = str(player.get('player_id')) if player.get('player_id') else None
        
        # If player has no ID or doesn't have a contract file, add to list
        if not player_id or player_id not in existing_contract_ids:
            players_without_contracts.append(player)
    
    logger.info(f"Found {len(players_without_contracts)} non-roster players without contracts")
    return players_without_contracts


def scrape_missing_contracts(
    players: List[Dict],
    output_dir: str = 'data/contracts',
    delay_seconds: float = 2.0
) -> Dict:
    """
    Scrape contracts for a list of players
    
    Args:
        players: List of player dicts with at least 'player_name'
        output_dir: Directory to save contract CSVs
        delay_seconds: Delay between requests to avoid rate limiting
    
    Returns:
        Summary dict with results
    """
    results = {
        'total': len(players),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }
    
    for idx, player in enumerate(players, 1):
        player_name = player.get('player_name')
        team_code = player.get('team_code', 'UNK')
        
        logger.info(f"[{idx}/{len(players)}] Processing {player_name} ({team_code})...")
        
        # Convert name to CapWages slug
        player_slug = player_name_to_slug(player_name)
        
        try:
            # Scrape and save contract
            result = export_to_database_and_csv(player_slug, output_dir)
            
            if result.get('success'):
                results['success'] += 1
                results['details'].append({
                    'player_name': player_name,
                    'player_slug': player_slug,
                    'team': team_code,
                    'status': 'success',
                    'csv_files': result.get('csv_files', {})
                })
                logger.info(f"✓ Successfully scraped contract for {player_name}")
            else:
                results['failed'] += 1
                results['details'].append({
                    'player_name': player_name,
                    'player_slug': player_slug,
                    'team': team_code,
                    'status': 'failed',
                    'error': result.get('error')
                })
                logger.warning(f"✗ Failed to scrape contract for {player_name}: {result.get('error')}")
        
        except Exception as e:
            results['failed'] += 1
            results['details'].append({
                'player_name': player_name,
                'player_slug': player_slug,
                'team': team_code,
                'status': 'error',
                'error': str(e)
            })
            logger.error(f"✗ Error scraping {player_name}: {e}")
        
        # Rate limiting
        if idx < len(players):
            time.sleep(delay_seconds)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Scrape missing contracts for non-roster players')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--team',
        help='Team code to scrape (e.g., MTL)'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='Scrape missing contracts for all teams'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of players to scrape'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='data/contracts',
        help='Output directory for contract CSV files'
    )
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("Missing Contract Scraper")
    logger.info("="*80)
    
    # Get existing contracts
    existing_contract_ids = get_existing_contract_player_ids(args.output_dir)
    logger.info(f"Found {len(existing_contract_ids)} existing contract files")
    
    # Get players without contracts
    if args.team:
        logger.info(f"Fetching non-roster players for {args.team}...")
        players = get_non_roster_players_without_contracts(args.team, existing_contract_ids)
    else:
        logger.info("Fetching non-roster players for all teams...")
        players = get_non_roster_players_without_contracts(None, existing_contract_ids)
    
    if not players:
        logger.info("No players need contract scraping!")
        return
    
    # Apply limit if specified
    if args.limit:
        players = players[:args.limit]
        logger.info(f"Limited to first {args.limit} players")
    
    logger.info(f"\nPlayers to scrape: {len(players)}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Delay between requests: {args.delay}s")
    logger.info("="*80)
    
    # Scrape contracts
    results = scrape_missing_contracts(players, args.output_dir, args.delay)
    
    # Print summary
    logger.info("="*80)
    logger.info("SCRAPING COMPLETE")
    logger.info("="*80)
    logger.info(f"Total processed: {results['total']}")
    logger.info(f"Successful: {results['success']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Skipped: {results['skipped']}")
    
    if results['failed'] > 0:
        logger.warning(f"\nFailed players:")
        for detail in results['details']:
            if detail['status'] in ('failed', 'error'):
                logger.warning(f"  - {detail['player_name']} ({detail['team']}): {detail.get('error')}")


if __name__ == '__main__':
    main()

