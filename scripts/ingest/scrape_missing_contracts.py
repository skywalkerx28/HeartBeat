#!/usr/bin/env python3
"""
Scrape Missing Player Contracts
Scrape contract data from CapWages for all players in missing_contracts_players.csv
"""

import sys
import csv
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import unicodedata
import re

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from bot.contract_exporter import export_to_database_and_csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/contracts/missing_contracts_scrape.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """
    Normalize player name for CapWages slug generation
    - Remove accents and special characters
    - Handle special cases (apostrophes, hyphens, periods)
    """
    # Remove accents
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    
    # Convert apostrophes to hyphens (for O'Reilly -> o-reilly)
    name = name.replace("'", '-')
    
    # Convert periods followed by letters to just letters with hyphen (J.T. -> j-t)
    # This handles cases like "J.T. Miller" -> "j-t-miller"
    name = re.sub(r'\.(?=[A-Z])', '-', name)
    
    # Remove any remaining periods
    name = name.replace('.', '')
    
    # Replace other special chars with spaces
    name = re.sub(r'[^a-zA-Z0-9\s-]', ' ', name)
    
    return name.strip()


def construct_capwages_slug(player_name: str) -> str:
    """
    Construct CapWages player slug from player name
    Format: firstname-lastname (lowercase, normalized)
    
    Examples:
        Sidney Crosby -> sidney-crosby
        Connor McDavid -> connor-mcdavid
        J.T. Miller -> jt-miller
        Aleksi Saarela -> aleksi-saarela
        Marc-Édouard Vlasic -> marc-edouard-vlasic
    """
    # Normalize the name
    normalized = normalize_name(player_name)
    
    # Split into parts
    parts = normalized.lower().split()
    
    if len(parts) < 2:
        # If only one part, just use it
        return parts[0] if parts else player_name.lower()
    
    # Join all parts with hyphens
    slug = '-'.join(parts)
    
    # Clean up multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    
    return slug


def load_missing_players(csv_path: str = 'data/contracts/missing_contracts_players.csv') -> List[Dict]:
    """Load players from missing contracts CSV"""
    players = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            players.append({
                'player_id': row['player_id'],
                'player_name': row['player_name'],
                'num_seasons': int(row['num_seasons']),
                'most_recent_season': row['most_recent_season']
            })
    
    logger.info(f"Loaded {len(players)} missing players from {csv_path}")
    return players


def scrape_missing_contracts(
    output_dir: str = 'data/contracts',
    progress_file: str = 'data/contracts/missing_contracts_progress.json',
    delay_seconds: float = 2.0,
    start_index: int = 0,
    max_players: int = None,
    priority_season: str = None
) -> Dict[str, Any]:
    """
    Batch scrape contracts for all missing players
    
    Args:
        output_dir: Directory to save CSV files (will create team subdirectories)
        progress_file: Path to progress tracking file
        delay_seconds: Delay between requests (rate limiting)
        start_index: Start from this player index (for resuming)
        max_players: Maximum number of players to process (None = all)
        priority_season: If set, prioritize players from this season (e.g., '2024-2025')
    
    Returns:
        Dict with batch scrape results
    """
    players = load_missing_players()
    
    # Filter by priority season if specified
    if priority_season:
        original_count = len(players)
        players = [p for p in players if p['most_recent_season'] == priority_season]
        logger.info(f"Filtered to {len(players)} players from {priority_season} season (from {original_count} total)")
    
    # Load progress if resuming
    progress = {
        'started_at': datetime.now().isoformat(),
        'total_players': len(players),
        'processed': 0,
        'succeeded': 0,
        'failed': 0,
        'not_found': 0,
        'successes': [],
        'failures': [],
        'not_found_players': [],
        'current_index': start_index
    }
    
    progress_path = Path(progress_file)
    if progress_path.exists() and start_index > 0:
        logger.info(f"Loading existing progress from {progress_file}")
        with open(progress_path, 'r') as f:
            existing_progress = json.load(f)
            progress.update(existing_progress)
    
    # Determine end index
    end_index = len(players)
    if max_players:
        end_index = min(start_index + max_players, len(players))
    
    logger.info("=" * 100)
    logger.info("MISSING CONTRACTS SCRAPER - STARTING")
    logger.info("=" * 100)
    logger.info(f"Total Missing Players: {len(players)}")
    logger.info(f"Processing Range: {start_index} to {end_index}")
    logger.info(f"Delay Between Requests: {delay_seconds}s")
    logger.info(f"Output Directory: {output_dir}")
    if priority_season:
        logger.info(f"Priority Season: {priority_season}")
    logger.info("=" * 100)
    
    # Process each player
    for idx in range(start_index, end_index):
        player = players[idx]
        player_name = player['player_name']
        player_id = player['player_id']
        most_recent_season = player['most_recent_season']
        
        progress['current_index'] = idx
        
        try:
            # Construct CapWages slug
            capwages_slug = construct_capwages_slug(player_name)
            
            logger.info(f"\n[{idx+1}/{len(players)}] Processing: {player_name} (ID: {player_id})")
            logger.info(f"  Most Recent Season: {most_recent_season}")
            logger.info(f"  CapWages Slug: {capwages_slug}")
            logger.info(f"  URL: https://capwages.com/players/{capwages_slug}")
            
            # Scrape contract data
            result = export_to_database_and_csv(capwages_slug, output_dir)
            
            if result.get('success'):
                progress['succeeded'] += 1
                progress['successes'].append({
                    'index': idx,
                    'player_name': player_name,
                    'player_id': player_id,
                    'nhl_id': result.get('player_id'),
                    'most_recent_season': most_recent_season,
                    'slug': capwages_slug,
                    'contracts': len(result.get('contract_ids', [])),
                    'details': len(result.get('detail_ids', []))
                })
                logger.info(f"  ✓ SUCCESS: {len(result.get('contract_ids', []))} contracts scraped")
            else:
                error_msg = result.get('error', 'Unknown error')
                
                # Check if player not found on CapWages (404 or no data)
                if 'No data scraped' in error_msg or '404' in error_msg or 'not found' in error_msg.lower():
                    progress['not_found'] += 1
                    progress['not_found_players'].append({
                        'index': idx,
                        'player_name': player_name,
                        'player_id': player_id,
                        'most_recent_season': most_recent_season,
                        'slug': capwages_slug,
                        'reason': 'Player not found on CapWages (possibly retired or older player)'
                    })
                    logger.info(f"  ⊘ NOT FOUND: Player not on CapWages (likely retired/older)")
                else:
                    progress['failed'] += 1
                    progress['failures'].append({
                        'index': idx,
                        'player_name': player_name,
                        'player_id': player_id,
                        'most_recent_season': most_recent_season,
                        'slug': capwages_slug,
                        'error': error_msg
                    })
                    logger.warning(f"  ✗ FAILED: {error_msg}")
        
        except Exception as e:
            logger.error(f"  ✗ ERROR: {e}")
            progress['failed'] += 1
            progress['failures'].append({
                'index': idx,
                'player_name': player_name,
                'player_id': player_id,
                'most_recent_season': most_recent_season,
                'error': str(e)
            })
        
        progress['processed'] += 1
        
        # Save progress every 10 players
        if progress['processed'] % 10 == 0:
            with open(progress_path, 'w') as f:
                json.dump(progress, f, indent=2)
            logger.info(f"\n  Progress: {progress['processed']}/{end_index-start_index} | "
                       f"Success: {progress['succeeded']} | "
                       f"Failed: {progress['failed']} | "
                       f"Not Found: {progress['not_found']}")
        
        # Rate limiting - delay between requests
        if idx < end_index - 1:  # Don't delay after last player
            time.sleep(delay_seconds)
    
    # Final progress save
    progress['completed_at'] = datetime.now().isoformat()
    with open(progress_path, 'w') as f:
        json.dump(progress, f, indent=2)
    
    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("MISSING CONTRACTS SCRAPE COMPLETE")
    logger.info("=" * 100)
    logger.info(f"Total Processed: {progress['processed']}")
    logger.info(f"Succeeded: {progress['succeeded']}")
    logger.info(f"Not Found (CapWages): {progress['not_found']}")
    logger.info(f"Failed (Errors): {progress['failed']}")
    logger.info(f"Success Rate: {progress['succeeded']/progress['processed']*100:.1f}%")
    logger.info(f"Progress File: {progress_file}")
    logger.info("=" * 100)
    
    # Export summary CSV
    summary_csv = Path(output_dir) / f"missing_contracts_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(summary_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        writer.writerow(['MISSING CONTRACTS SCRAPE SUMMARY'])
        writer.writerow(['Completed At', progress.get('completed_at')])
        writer.writerow(['Total Players', progress['processed']])
        writer.writerow(['Succeeded', progress['succeeded']])
        writer.writerow(['Not Found on CapWages', progress['not_found']])
        writer.writerow(['Failed (Errors)', progress['failed']])
        writer.writerow(['Success Rate', f"{progress['succeeded']/progress['processed']*100:.1f}%"])
        writer.writerow([])
        
        writer.writerow(['SUCCESSFUL SCRAPES'])
        writer.writerow(['Index', 'Player Name', 'NHL ID', 'Most Recent Season', 'CapWages Slug', 'Contracts', 'Details'])
        for success in progress['successes']:
            writer.writerow([
                success['index'],
                success['player_name'],
                success.get('nhl_id', success['player_id']),
                success['most_recent_season'],
                success['slug'],
                success.get('contracts', 0),
                success.get('details', 0)
            ])
        
        writer.writerow([])
        writer.writerow(['NOT FOUND ON CAPWAGES (Likely Retired/Older Players)'])
        writer.writerow(['Index', 'Player Name', 'NHL ID', 'Most Recent Season', 'CapWages Slug', 'Reason'])
        for not_found in progress['not_found_players']:
            writer.writerow([
                not_found['index'],
                not_found['player_name'],
                not_found['player_id'],
                not_found['most_recent_season'],
                not_found.get('slug', 'N/A'),
                not_found.get('reason', 'Not found')
            ])
        
        writer.writerow([])
        writer.writerow(['FAILED SCRAPES (Errors)'])
        writer.writerow(['Index', 'Player Name', 'NHL ID', 'Most Recent Season', 'CapWages Slug', 'Error'])
        for failure in progress['failures']:
            writer.writerow([
                failure['index'],
                failure['player_name'],
                failure['player_id'],
                failure['most_recent_season'],
                failure.get('slug', 'N/A'),
                failure.get('error', 'Unknown')
            ])
    
    logger.info(f"Summary exported to: {summary_csv}")
    
    return progress


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scrape contracts for players missing from contracts database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Scrape all missing players
  python scripts/ingest/scrape_missing_contracts.py
  
  # Scrape only 2024-2025 season players (priority)
  python scripts/ingest/scrape_missing_contracts.py --priority-season 2024-2025
  
  # Test with first 10 players
  python scripts/ingest/scrape_missing_contracts.py --max 10
  
  # Resume from player 100
  python scripts/ingest/scrape_missing_contracts.py --start 100
  
  # Fast mode (1 second delay) - use cautiously
  python scripts/ingest/scrape_missing_contracts.py --delay 1.0
'''
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='data/contracts',
        help='Output directory for CSV files (default: data/contracts)'
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)'
    )
    
    parser.add_argument(
        '--start', '-s',
        type=int,
        default=0,
        help='Start from this player index (default: 0)'
    )
    
    parser.add_argument(
        '--max', '-m',
        type=int,
        default=None,
        help='Maximum number of players to process (default: all)'
    )
    
    parser.add_argument(
        '--priority-season', '-p',
        type=str,
        default=None,
        help='Only scrape players from this season (e.g., 2024-2025)'
    )
    
    parser.add_argument(
        '--progress-file',
        default='data/contracts/missing_contracts_progress.json',
        help='Progress tracking file (default: data/contracts/missing_contracts_progress.json)'
    )
    
    args = parser.parse_args()
    
    try:
        result = scrape_missing_contracts(
            output_dir=args.output_dir,
            progress_file=args.progress_file,
            delay_seconds=args.delay,
            start_index=args.start,
            max_players=args.max,
            priority_season=args.priority_season
        )
        
        print("\n" + "=" * 100)
        print("MISSING CONTRACTS SCRAPE SUMMARY")
        print("=" * 100)
        print(f"Processed: {result['processed']}")
        print(f"Succeeded: {result['succeeded']} ({result['succeeded']/result['processed']*100:.1f}%)")
        print(f"Not Found: {result['not_found']} ({result['not_found']/result['processed']*100:.1f}%)")
        print(f"Failed: {result['failed']} ({result['failed']/result['processed']*100:.1f}%)")
        print("=" * 100)
        
        return 0 if result['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        logger.warning("\n\nScrape interrupted by user. Progress has been saved.")
        logger.info("To resume, run with --start <index> flag")
        return 2
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

