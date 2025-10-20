#!/usr/bin/env python3
"""
Fetch NHL Player Game Logs for All Active Players

This script:
1. Reads player profiles to get season availability
2. Fetches game-by-game logs for each player, season, and game type
3. Saves separate files per player/season/game-type for efficient loading
4. Creates an index for quick lookups

Usage:
    python3 scripts/ingest/fetch_player_game_logs.py
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('player_game_logs_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
PROFILES_DIR = "data/processed/player_profiles/profiles"
OUTPUT_DIR = "data/processed/player_profiles/game_logs"
NHL_API_BASE = "https://api-web.nhle.com/v1/player"
RATE_LIMIT_DELAY = 0.3  # Delay between API calls in seconds
BATCH_SIZE = 25  # Save progress every N API calls

# Game type mapping
GAME_TYPES = {
    2: 'regular',
    3: 'playoffs'
}


class GameLogFetcher:
    """Fetches and caches NHL player game-by-game logs"""
    
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'total_requests': 0,
            'success': 0,
            'failed': 0,
            'skipped_existing': 0,
            'skipped_empty': 0,
            'errors': []
        }
    
    def get_player_seasons(self, player_id: int) -> List[Tuple[int, List[int]]]:
        """
        Read player profile to get available seasons and game types
        Returns: List of (season, [game_types])
        """
        profile_file = Path(PROFILES_DIR) / f"{player_id}.json"
        
        if not profile_file.exists():
            logger.warning(f"Profile not found for player {player_id}")
            return []
        
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get season totals which tells us which seasons they played
            season_totals = data.get('seasonTotals', [])
            
            # Filter for NHL regular season games (gameTypeId == 2, leagueAbbrev == 'NHL')
            seasons_map = {}
            for season_data in season_totals:
                if season_data.get('leagueAbbrev') == 'NHL':
                    season = season_data.get('season')
                    game_type = season_data.get('gameTypeId')
                    
                    if season and game_type in GAME_TYPES:
                        if season not in seasons_map:
                            seasons_map[season] = []
                        if game_type not in seasons_map[season]:
                            seasons_map[season].append(game_type)
            
            # Convert to list of tuples
            result = [(season, game_types) for season, game_types in sorted(seasons_map.items())]
            return result
            
        except Exception as e:
            logger.error(f"Error reading profile for player {player_id}: {e}")
            return []
    
    def game_log_exists(self, player_id: int, season: int, game_type: int) -> bool:
        """Check if game log already exists"""
        player_dir = self.output_dir / str(player_id)
        game_type_str = GAME_TYPES.get(game_type, str(game_type))
        filename = f"{season}_{game_type_str}.json"
        file_path = player_dir / filename
        return file_path.exists()
    
    def fetch_game_log(self, player_id: int, season: int, game_type: int) -> Optional[Dict]:
        """Fetch game log for a specific player, season, and game type"""
        url = f"{NHL_API_BASE}/{player_id}/game-log/{season}/{game_type}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check if gameLog exists and has entries
            game_log = data.get('gameLog', [])
            if not game_log:
                return None
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"No game log found for player {player_id}, season {season}, type {game_type}")
            else:
                logger.error(f"HTTP error for player {player_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for player {player_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for player {player_id}: {e}")
            return None
    
    def save_game_log(self, player_id: int, season: int, game_type: int, data: Dict) -> bool:
        """Save game log to file"""
        try:
            # Create player directory
            player_dir = self.output_dir / str(player_id)
            player_dir.mkdir(exist_ok=True)
            
            # Save file
            game_type_str = GAME_TYPES.get(game_type, str(game_type))
            filename = f"{season}_{game_type_str}.json"
            output_file = player_dir / filename
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Error saving game log for player {player_id}: {e}")
            return False
    
    def fetch_all_game_logs(self, skip_existing: bool = True):
        """Fetch game logs for all players"""
        # Get all player profile files
        profile_dir = Path(PROFILES_DIR)
        player_files = list(profile_dir.glob("*.json"))
        
        logger.info(f"Found {len(player_files)} player profiles")
        logger.info(f"Skip existing: {skip_existing}")
        logger.info("=" * 80)
        
        start_time = time.time()
        api_call_count = 0
        
        for idx, profile_file in enumerate(player_files, 1):
            player_id = int(profile_file.stem)
            
            # Get seasons this player played
            seasons = self.get_player_seasons(player_id)
            
            if not seasons:
                logger.debug(f"[{idx}/{len(player_files)}] Player {player_id}: No NHL seasons found")
                continue
            
            logger.info(f"[{idx}/{len(player_files)}] Player {player_id}: {len(seasons)} seasons found")
            
            # Fetch game logs for each season and game type
            for season, game_types in seasons:
                for game_type in game_types:
                    game_type_str = GAME_TYPES.get(game_type, str(game_type))
                    
                    # Skip if already exists
                    if skip_existing and self.game_log_exists(player_id, season, game_type):
                        logger.debug(f"  └─ {season} {game_type_str}: Already exists")
                        self.stats['skipped_existing'] += 1
                        continue
                    
                    # Fetch from API
                    logger.info(f"  └─ Fetching {season} {game_type_str}")
                    data = self.fetch_game_log(player_id, season, game_type)
                    api_call_count += 1
                    self.stats['total_requests'] += 1
                    
                    if data:
                        game_count = len(data.get('gameLog', []))
                        if self.save_game_log(player_id, season, game_type, data):
                            self.stats['success'] += 1
                            logger.info(f"      ✓ Saved {game_count} games")
                        else:
                            self.stats['failed'] += 1
                            self.stats['errors'].append(
                                f"Player {player_id}, {season} {game_type_str}: Failed to save"
                            )
                    else:
                        self.stats['skipped_empty'] += 1
                        logger.debug(f"      ○ No games found")
                    
                    # Rate limiting
                    time.sleep(RATE_LIMIT_DELAY)
                    
                    # Progress update every BATCH_SIZE API calls
                    if api_call_count % BATCH_SIZE == 0:
                        elapsed = time.time() - start_time
                        rate = api_call_count / elapsed if elapsed > 0 else 0
                        remaining_est = (self.stats['total_requests'] * 2) / rate if rate > 0 else 0
                        
                        logger.info("")
                        logger.info(f"Progress Update:")
                        logger.info(f"  API Calls: {api_call_count} | Success: {self.stats['success']} | "
                                  f"Failed: {self.stats['failed']} | Skipped: {self.stats['skipped_existing']}")
                        logger.info(f"  Rate: {rate:.1f} req/sec | Elapsed: {elapsed/60:.1f} min")
                        logger.info("")
        
        # Final summary
        elapsed = time.time() - start_time
        logger.info("=" * 80)
        logger.info("FETCH COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total API requests: {self.stats['total_requests']}")
        logger.info(f"Successfully saved: {self.stats['success']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped (existing): {self.stats['skipped_existing']}")
        logger.info(f"Skipped (empty): {self.stats['skipped_empty']}")
        logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
        logger.info(f"Average rate: {self.stats['total_requests']/elapsed:.1f} requests/sec")
        
        if self.stats['errors']:
            logger.warning(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:20]:  # Show first 20 errors
                logger.warning(f"  - {error}")
    
    def create_game_log_index(self):
        """Create an index of all game logs for quick lookups"""
        logger.info("Creating game log index...")
        
        index_data = []
        
        for player_dir in self.output_dir.iterdir():
            if not player_dir.is_dir():
                continue
            
            player_id = int(player_dir.name)
            
            for log_file in player_dir.glob("*.json"):
                try:
                    # Parse filename: {season}_{game_type}.json
                    parts = log_file.stem.split('_')
                    if len(parts) != 2:
                        continue
                    
                    season = int(parts[0])
                    game_type_str = parts[1]
                    
                    # Get game count
                    with open(log_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    game_count = len(data.get('gameLog', []))
                    
                    index_entry = {
                        'playerId': player_id,
                        'season': season,
                        'gameType': game_type_str,
                        'gameCount': game_count,
                        'filePath': f"{player_id}/{log_file.name}"
                    }
                    index_data.append(index_entry)
                    
                except Exception as e:
                    logger.error(f"Error indexing {log_file}: {e}")
        
        # Save index
        index_df = pd.DataFrame(index_data)
        index_file = self.output_dir.parent / "game_log_index.parquet"
        index_df.to_parquet(index_file, index=False)
        logger.info(f"Game log index saved: {index_file}")
        logger.info(f"Indexed {len(index_data)} game logs")
        
        # Also save as JSON for easy browsing
        index_json = self.output_dir.parent / "game_log_index.json"
        with open(index_json, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON index saved: {index_json}")
        
        # Summary stats
        total_games = index_df['gameCount'].sum()
        players_with_data = index_df['playerId'].nunique()
        seasons_covered = index_df['season'].nunique()
        
        logger.info(f"Summary:")
        logger.info(f"  Players with game logs: {players_with_data}")
        logger.info(f"  Seasons covered: {seasons_covered}")
        logger.info(f"  Total games tracked: {total_games:,}")


def main():
    """Main execution function"""
    logger.info("=" * 80)
    logger.info("NHL PLAYER GAME LOG FETCHER")
    logger.info("=" * 80)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    fetcher = GameLogFetcher()
    
    # Fetch all game logs
    try:
        fetcher.fetch_all_game_logs(skip_existing=True)
    except KeyboardInterrupt:
        logger.warning("\nFetch interrupted by user")
        logger.info(f"Progress saved. Success: {fetcher.stats['success']}, "
                   f"Failed: {fetcher.stats['failed']}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    
    # Create index
    try:
        fetcher.create_game_log_index()
    except Exception as e:
        logger.error(f"Failed to create game log index: {e}")
    
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Done!")
    
    return 0


if __name__ == "__main__":
    exit(main())

