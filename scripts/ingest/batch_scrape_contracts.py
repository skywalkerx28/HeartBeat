#!/usr/bin/env python3
"""
Batch Contract Scraper
Scrape contract data for all NHL players from unified roster
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import csv

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from bot.contract_exporter import export_to_database_and_csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/contracts/batch_scrape.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_unified_roster(roster_path: str = 'data/processed/rosters/unified_roster_20252026.json') -> List[Dict]:
    """Load players from unified roster"""
    with open(roster_path, 'r') as f:
        data = json.load(f)
    
    players = data.get('players', [])
    logger.info(f"Loaded {len(players)} players from roster")
    return players


def construct_capwages_slug(player: Dict) -> str:
    """
    Construct CapWages player slug from first and last name
    Format: firstname-lastname (lowercase, spaces to hyphens)
    
    Examples:
        Sidney Crosby -> sidney-crosby
        Connor McDavid -> connor-mcdavid
        J.T. Miller -> jt-miller
    """
    first_name = player.get('firstName', '').strip()
    last_name = player.get('lastName', '').strip()
    
    # Handle special characters
    # Remove periods and apostrophes, convert to lowercase
    first_clean = first_name.replace('.', '').replace("'", '').lower()
    last_clean = last_name.replace('.', '').replace("'", '').lower()
    
    # Replace spaces with hyphens
    first_clean = first_clean.replace(' ', '-')
    last_clean = last_clean.replace(' ', '-')
    
    slug = f"{first_clean}-{last_clean}"
    
    return slug


def batch_scrape_contracts(
    output_dir: str = 'data/contracts',
    progress_file: str = 'data/contracts/batch_progress.json',
    delay_seconds: float = 2.0,
    start_index: int = 0,
    max_players: int = None
) -> Dict[str, Any]:
    """
    Batch scrape contracts for all players in unified roster
    
    Args:
        output_dir: Directory to save CSV files
        progress_file: Path to progress tracking file
        delay_seconds: Delay between requests (rate limiting)
        start_index: Start from this player index (for resuming)
        max_players: Maximum number of players to process (None = all)
    
    Returns:
        Dict with batch scrape results
    """
    players = load_unified_roster()
    
    # Load progress if resuming
    progress = {
        'started_at': datetime.now().isoformat(),
        'total_players': len(players),
        'processed': 0,
        'succeeded': 0,
        'failed': 0,
        'skipped': 0,
        'successes': [],
        'failures': [],
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
    logger.info("BATCH CONTRACT SCRAPER - STARTING")
    logger.info("=" * 100)
    logger.info(f"Total Players in Roster: {len(players)}")
    logger.info(f"Processing Range: {start_index} to {end_index}")
    logger.info(f"Delay Between Requests: {delay_seconds}s")
    logger.info(f"Output Directory: {output_dir}")
    logger.info("=" * 100)
    
    # Process each player
    for idx in range(start_index, end_index):
        player = players[idx]
        player_name = player['name']
        player_id = player['id']
        team = player['team']
        
        progress['current_index'] = idx
        
        try:
            # Construct CapWages slug
            capwages_slug = construct_capwages_slug(player)
            
            logger.info(f"\n[{idx+1}/{len(players)}] Processing: {player_name} ({team}) - ID: {player_id}")
            logger.info(f"  CapWages URL: https://capwages.com/players/{capwages_slug}")
            
            # Scrape contract data
            result = export_to_database_and_csv(capwages_slug, output_dir)
            
            if result.get('success'):
                progress['succeeded'] += 1
                progress['successes'].append({
                    'index': idx,
                    'player_name': player_name,
                    'player_id': player_id,
                    'nhl_id': result.get('player_id'),
                    'team': team,
                    'slug': capwages_slug,
                    'contracts': len(result.get('contract_ids', [])),
                    'details': len(result.get('detail_ids', []))
                })
                logger.info(f"  ✓ SUCCESS: {result.get('contracts', 0)} contracts, {result.get('details', 0)} details")
            else:
                progress['failed'] += 1
                progress['failures'].append({
                    'index': idx,
                    'player_name': player_name,
                    'player_id': player_id,
                    'team': team,
                    'slug': capwages_slug,
                    'error': result.get('error', 'Unknown error')
                })
                logger.warning(f"  ✗ FAILED: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"  ✗ ERROR: {e}")
            progress['failed'] += 1
            progress['failures'].append({
                'index': idx,
                'player_name': player_name,
                'player_id': player_id,
                'team': team,
                'error': str(e)
            })
        
        progress['processed'] += 1
        
        # Save progress every 10 players
        if progress['processed'] % 10 == 0:
            with open(progress_path, 'w') as f:
                json.dump(progress, f, indent=2)
            logger.info(f"\n  Progress: {progress['processed']}/{end_index-start_index} | Success: {progress['succeeded']} | Failed: {progress['failed']}")
        
        # Rate limiting - delay between requests
        if idx < end_index - 1:  # Don't delay after last player
            time.sleep(delay_seconds)
    
    # Final progress save
    progress['completed_at'] = datetime.now().isoformat()
    with open(progress_path, 'w') as f:
        json.dump(progress, f, indent=2)
    
    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("BATCH SCRAPE COMPLETE")
    logger.info("=" * 100)
    logger.info(f"Total Processed: {progress['processed']}")
    logger.info(f"Succeeded: {progress['succeeded']}")
    logger.info(f"Failed: {progress['failed']}")
    logger.info(f"Success Rate: {progress['succeeded']/progress['processed']*100:.1f}%")
    logger.info(f"Progress File: {progress_file}")
    logger.info("=" * 100)
    
    # Export summary CSV
    summary_csv = Path(output_dir) / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(summary_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        
        writer.writerow(['BATCH CONTRACT SCRAPE SUMMARY'])
        writer.writerow(['Completed At', progress.get('completed_at')])
        writer.writerow(['Total Players', progress['processed']])
        writer.writerow(['Succeeded', progress['succeeded']])
        writer.writerow(['Failed', progress['failed']])
        writer.writerow(['Success Rate', f"{progress['succeeded']/progress['processed']*100:.1f}%"])
        writer.writerow([])
        
        writer.writerow(['SUCCESSFUL SCRAPES'])
        writer.writerow(['Index', 'Player Name', 'NHL ID', 'Team', 'CapWages Slug', 'Contracts', 'Details'])
        for success in progress['successes']:
            writer.writerow([
                success['index'],
                success['player_name'],
                success.get('nhl_id', success['player_id']),
                success['team'],
                success['slug'],
                success.get('contracts', 0),
                success.get('details', 0)
            ])
        
        writer.writerow([])
        writer.writerow(['FAILED SCRAPES'])
        writer.writerow(['Index', 'Player Name', 'Player ID', 'Team', 'CapWages Slug', 'Error'])
        for failure in progress['failures']:
            writer.writerow([
                failure['index'],
                failure['player_name'],
                failure['player_id'],
                failure['team'],
                failure.get('slug', 'N/A'),
                failure.get('error', 'Unknown')
            ])
    
    logger.info(f"Summary exported to: {summary_csv}")
    
    return progress


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Batch scrape contracts for all NHL players',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Scrape all players
  python scripts/ingest/batch_scrape_contracts.py
  
  # Scrape first 10 players (testing)
  python scripts/ingest/batch_scrape_contracts.py --max 10
  
  # Resume from player 100
  python scripts/ingest/batch_scrape_contracts.py --start 100
  
  # Scrape specific range (players 50-100)
  python scripts/ingest/batch_scrape_contracts.py --start 50 --max 50
  
  # Fast mode (1 second delay)
  python scripts/ingest/batch_scrape_contracts.py --delay 1.0
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
        '--progress-file', '-p',
        default='data/contracts/batch_progress.json',
        help='Progress tracking file (default: data/contracts/batch_progress.json)'
    )
    
    args = parser.parse_args()
    
    try:
        result = batch_scrape_contracts(
            output_dir=args.output_dir,
            progress_file=args.progress_file,
            delay_seconds=args.delay,
            start_index=args.start,
            max_players=args.max
        )
        
        print("\n" + "=" * 100)
        print("BATCH SCRAPE SUMMARY")
        print("=" * 100)
        print(f"Processed: {result['processed']}")
        print(f"Succeeded: {result['succeeded']} ({result['succeeded']/result['processed']*100:.1f}%)")
        print(f"Failed: {result['failed']} ({result['failed']/result['processed']*100:.1f}%)")
        print("=" * 100)
        
        return 0 if result['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        logger.warning("\n\nBatch scrape interrupted by user. Progress has been saved.")
        logger.info("To resume, run with --start <index> flag")
        return 2
    except Exception as e:
        logger.error(f"Batch scrape failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

