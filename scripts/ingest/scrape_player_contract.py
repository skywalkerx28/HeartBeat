#!/usr/bin/env python3
"""
Player Contract Scraper CLI
Command-line tool to scrape player contract data from CapWages
"""

import sys
import os
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.bot.contract_exporter import export_to_database_and_csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Scrape player contract data from CapWages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python scripts/ingest/scrape_player_contract.py sidney-crosby
  python scripts/ingest/scrape_player_contract.py auston-matthews -o data/custom_contracts
  python scripts/ingest/scrape_player_contract.py connor-mcdavid --verbose
        '''
    )
    
    parser.add_argument(
        'player_slug',
        help='Player URL slug from CapWages (e.g., sidney-crosby, auston-matthews)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='data/contracts',
        help='Output directory for CSV files (default: data/contracts)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Scraping contract data for: {args.player_slug}")
    logger.info(f"Output directory: {args.output_dir}")
    
    try:
        result = export_to_database_and_csv(args.player_slug, args.output_dir)
        
        if result.get('success'):
            print("\n" + "=" * 80)
            print("SUCCESS: Contract data scraped and exported")
            print("=" * 80)
            print(f"\nPlayer: {result.get('player_name')}")
            print(f"Contracts: {len(result.get('contract_ids', []))}")
            print(f"Stats: {len(result.get('stat_ids', []))}")
            
            print("\nCSV Files:")
            for file_type, file_path in result.get('csv_files', {}).items():
                print(f"  {file_type}: {file_path}")
            
            print("\n" + "=" * 80)
            return 0
        else:
            print(f"\nERROR: {result.get('error')}")
            return 1
            
    except Exception as e:
        logger.exception(f"Failed to scrape contract data: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

