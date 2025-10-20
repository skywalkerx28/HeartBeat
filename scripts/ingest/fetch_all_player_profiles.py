#!/usr/bin/env python3
"""
Fetch NHL Player Landing Page Data for All Active Players

This script:
1. Reads all player IDs from nhl_rosters_latest.parquet
2. Fetches landing page data from NHL API for each player
3. Saves individual JSON files for each player
4. Creates a master index file for quick lookups

Usage:
    python3 scripts/ingest/fetch_all_player_profiles.py
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('player_profile_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
ROSTER_FILE = "data/processed/rosters/nhl_rosters_latest.parquet"
OUTPUT_DIR = "data/processed/player_profiles"
NHL_API_BASE = "https://api-web.nhle.com/v1/player"
BATCH_SIZE = 50  # Save progress every N players
RATE_LIMIT_DELAY = 0.5  # Delay between API calls in seconds


class PlayerProfileFetcher:
    """Fetches and caches NHL player profile data"""
    
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.profiles_dir = self.output_dir / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)
        
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    def load_player_ids(self, roster_file: str) -> pd.DataFrame:
        """Load player IDs from roster parquet file"""
        logger.info(f"Loading player roster from {roster_file}")
        df = pd.read_parquet(roster_file)
        
        # Log column names to understand structure
        logger.info(f"Roster columns: {df.columns.tolist()}")
        logger.info(f"Total players in roster: {len(df)}")
        
        # Display sample of data
        logger.info(f"Sample roster data:\n{df.head()}")
        
        return df
    
    def fetch_player_landing(self, player_id: int) -> Optional[Dict]:
        """Fetch landing page data for a single player"""
        url = f"{NHL_API_BASE}/{player_id}/landing"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Player {player_id} not found (404)")
            else:
                logger.error(f"HTTP error for player {player_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for player {player_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for player {player_id}: {e}")
            return None
    
    def save_player_profile(self, player_id: int, data: Dict) -> bool:
        """Save player profile data to JSON file"""
        try:
            output_file = self.profiles_dir / f"{player_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving player {player_id}: {e}")
            return False
    
    def player_profile_exists(self, player_id: int) -> bool:
        """Check if player profile already exists"""
        output_file = self.profiles_dir / f"{player_id}.json"
        return output_file.exists()
    
    def fetch_all_players(self, roster_df: pd.DataFrame, skip_existing: bool = True):
        """Fetch landing page data for all players"""
        # Determine player ID column (might be 'playerId', 'player_id', 'id', etc.)
        possible_id_cols = ['nhl_player_id', 'playerId', 'player_id', 'id', 'playerID']
        player_id_col = None
        
        for col in possible_id_cols:
            if col in roster_df.columns:
                player_id_col = col
                break
        
        if player_id_col is None:
            logger.error(f"Could not find player ID column. Available columns: {roster_df.columns.tolist()}")
            return
        
        logger.info(f"Using '{player_id_col}' as player ID column")
        
        # Get unique player IDs
        player_ids = roster_df[player_id_col].unique()
        self.stats['total'] = len(player_ids)
        
        logger.info(f"Starting fetch for {self.stats['total']} players")
        logger.info(f"Skip existing: {skip_existing}")
        
        start_time = time.time()
        
        for idx, player_id in enumerate(player_ids, 1):
            # Skip if already exists and skip_existing is True
            if skip_existing and self.player_profile_exists(player_id):
                logger.info(f"[{idx}/{self.stats['total']}] Player {player_id} already exists, skipping")
                self.stats['skipped'] += 1
                continue
            
            logger.info(f"[{idx}/{self.stats['total']}] Fetching player {player_id}")
            
            # Fetch player data
            data = self.fetch_player_landing(player_id)
            
            if data:
                # Save to file
                if self.save_player_profile(player_id, data):
                    self.stats['success'] += 1
                    logger.info(f"  ✓ Successfully saved player {player_id}")
                else:
                    self.stats['failed'] += 1
                    self.stats['errors'].append(f"Player {player_id}: Failed to save")
            else:
                self.stats['failed'] += 1
                self.stats['errors'].append(f"Player {player_id}: Failed to fetch")
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
            # Progress update every BATCH_SIZE players
            if idx % BATCH_SIZE == 0:
                elapsed = time.time() - start_time
                rate = idx / elapsed
                remaining = (self.stats['total'] - idx) / rate if rate > 0 else 0
                logger.info(f"Progress: {idx}/{self.stats['total']} | "
                          f"Success: {self.stats['success']} | "
                          f"Failed: {self.stats['failed']} | "
                          f"Skipped: {self.stats['skipped']} | "
                          f"ETA: {remaining/60:.1f} min")
        
        # Final summary
        elapsed = time.time() - start_time
        logger.info("=" * 80)
        logger.info("FETCH COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total players: {self.stats['total']}")
        logger.info(f"Successfully fetched: {self.stats['success']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped (existing): {self.stats['skipped']}")
        logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
        logger.info(f"Average rate: {self.stats['total']/elapsed:.1f} players/sec")
        
        if self.stats['errors']:
            logger.warning(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                logger.warning(f"  - {error}")
    
    def create_master_index(self, roster_df: pd.DataFrame):
        """Create a master index file with basic player info"""
        logger.info("Creating master index...")
        
        index_data = []
        
        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract key information
                index_entry = {
                    'playerId': data.get('playerId'),
                    'firstName': data.get('firstName', {}).get('default'),
                    'lastName': data.get('lastName', {}).get('default'),
                    'position': data.get('position'),
                    'teamAbbrev': data.get('currentTeamAbbrev'),
                    'isActive': data.get('isActive'),
                    'jerseyNumber': data.get('sweaterNumber'),
                    'profileFile': profile_file.name,
                }
                index_data.append(index_entry)
            except Exception as e:
                logger.error(f"Error indexing {profile_file}: {e}")
        
        # Save master index
        index_df = pd.DataFrame(index_data)
        index_file = self.output_dir / "player_index.parquet"
        index_df.to_parquet(index_file, index=False)
        logger.info(f"Master index saved: {index_file}")
        logger.info(f"Indexed {len(index_data)} players")
        
        # Also save as JSON for easy browsing
        index_json = self.output_dir / "player_index.json"
        with open(index_json, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON index saved: {index_json}")


def main():
    """Main execution function"""
    logger.info("=" * 80)
    logger.info("NHL PLAYER PROFILE FETCHER")
    logger.info("=" * 80)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    fetcher = PlayerProfileFetcher()
    
    # Load roster
    try:
        roster_df = fetcher.load_player_ids(ROSTER_FILE)
    except Exception as e:
        logger.error(f"Failed to load roster file: {e}")
        return 1
    
    # Fetch all players
    try:
        fetcher.fetch_all_players(roster_df, skip_existing=True)
    except KeyboardInterrupt:
        logger.warning("\nFetch interrupted by user")
        logger.info(f"Progress saved. Success: {fetcher.stats['success']}, "
                   f"Failed: {fetcher.stats['failed']}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    
    # Create master index
    try:
        fetcher.create_master_index(roster_df)
    except Exception as e:
        logger.error(f"Failed to create master index: {e}")
    
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Done!")
    
    return 0


if __name__ == "__main__":
    exit(main())

