#!/usr/bin/env python3
"""
Re-scrape specific players by their indices
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scrape_missing_contracts import scrape_missing_contracts

# The 20 players that weren't found due to slug issues
FAILED_INDICES = [0, 1, 19, 25, 27, 51, 59, 73, 74, 83, 89, 107, 113, 114, 120, 121, 129, 151, 169, 176]

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-scrape specific failed players')
    parser.add_argument('--delay', '-d', type=float, default=2.0, help='Delay between requests')
    args = parser.parse_args()
    
    print("=" * 80)
    print("RE-SCRAPING 20 FAILED PLAYERS WITH FIXED SLUG GENERATION")
    print("=" * 80)
    print(f"Player indices: {FAILED_INDICES}")
    print("=" * 80)
    
    # For each failed index, scrape just that player
    for idx in FAILED_INDICES:
        result = scrape_missing_contracts(
            output_dir='data/contracts',
            progress_file='data/contracts/rescrape_progress.json',
            delay_seconds=args.delay,
            start_index=idx,
            max_players=1,
            priority_season='2024-2025'
        )
        
        if result['processed'] > 0:
            print(f"\nPlayer {idx}: ", end='')
            if result['succeeded'] > 0:
                print("✓ SUCCESS")
            elif result['not_found'] > 0:
                print("⊘ NOT FOUND (confirmed)")
            else:
                print("✗ FAILED")
    
    print("\n" + "=" * 80)
    print("RE-SCRAPE COMPLETE")
    print("=" * 80)

