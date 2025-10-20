#!/usr/bin/env python3
"""
Populate Missing Player Stats - Complete Pipeline

This script processes all players in unified_roster_historical.json that don't have
aggregated stats yet. It performs the complete pipeline:
1. Identify missing players
2. Fetch their profiles from NHL API (if not already cached)
3. Fetch game logs for all their seasons
4. Aggregate into cumulative stats

This enables the performance charts to work for all historical players.
"""

import json
import requests
import time
from pathlib import Path
from typing import Set, Dict, List, Optional
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('populate_missing_stats.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ROSTER_FILE = BASE_DIR / "data" / "processed" / "rosters" / "unified_roster_historical.json"
AGGREGATED_STATS_DIR = BASE_DIR / "data" / "processed" / "player_profiles" / "aggregated_stats"
GAME_LOGS_DIR = BASE_DIR / "data" / "processed" / "player_profiles" / "game_logs"
PROFILES_DIR = BASE_DIR / "data" / "processed" / "player_profiles" / "profiles"
PROGRESS_FILE = BASE_DIR / "data" / "processed" / "player_profiles" / "missing_stats_progress.json"

# Ensure directories exist
GAME_LOGS_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
AGGREGATED_STATS_DIR.mkdir(parents=True, exist_ok=True)

# NHL API Configuration
NHL_API_BASE = "https://api-web.nhle.com/v1/player"
RATE_LIMIT_DELAY = 0.5  # Seconds between API calls
SAVE_INTERVAL = 10  # Save progress every N players

GAME_TYPES = {
    2: 'regular',
    3: 'playoffs'
}


class PlayerStatsPopulator:
    """Populates missing player stats from NHL API"""
    
    def __init__(self):
        self.stats = {
            'total_players': 0,
            'processed': 0,
            'profiles_fetched': 0,
            'game_logs_fetched': 0,
            'aggregated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        self.progress_data = self.load_progress()
    
    def load_progress(self) -> Dict:
        """Load progress from previous run"""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    data = json.load(f)
                logger.info(f"Resuming from previous run. Last player: {data.get('last_player_id', 'N/A')}")
                return data
            except:
                return {'processed_ids': []}
        return {'processed_ids': []}
    
    def save_progress(self, player_id: int):
        """Save progress"""
        self.progress_data['last_player_id'] = player_id
        self.progress_data['last_updated'] = datetime.now().isoformat()
        self.progress_data['stats'] = self.stats
        
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress_data, f, indent=2)
    
    def get_missing_players(self) -> List[int]:
        """Get list of player IDs that don't have aggregated stats"""
        logger.info("Identifying missing players...")
        
        # Get players from roster
        with open(ROSTER_FILE, 'r') as f:
            roster = json.load(f)
        
        all_player_ids = {p['id'] for p in roster['players']}
        
        # Get players with aggregated stats
        existing_stats = {int(d.name) for d in AGGREGATED_STATS_DIR.iterdir() if d.is_dir() and d.name.isdigit()}
        
        # Get missing players
        missing = list(all_player_ids - existing_stats)
        
        # Remove already processed from this run
        processed_ids = set(self.progress_data.get('processed_ids', []))
        missing = [pid for pid in missing if pid not in processed_ids]
        
        logger.info(f"Total players in roster: {len(all_player_ids)}")
        logger.info(f"Players with stats: {len(existing_stats)}")
        logger.info(f"Missing players: {len(missing)}")
        logger.info(f"Already processed this run: {len(processed_ids)}")
        logger.info(f"Remaining to process: {len(missing)}")
        
        return sorted(missing)
    
    def fetch_player_profile(self, player_id: int) -> Optional[Dict]:
        """Fetch player profile from NHL API"""
        # Check if profile already exists
        profile_file = PROFILES_DIR / f"{player_id}.json"
        if profile_file.exists():
            try:
                with open(profile_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Fetch from API
        url = f"{NHL_API_BASE}/{player_id}/landing"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Save profile
            with open(profile_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"Player {player_id} not found (404)")
            else:
                logger.error(f"HTTP error fetching player {player_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching player {player_id}: {e}")
            return None
    
    def get_player_seasons(self, profile_data: Dict) -> List[tuple]:
        """Extract seasons from player profile"""
        seasons_map = {}
        
        season_totals = profile_data.get('seasonTotals', [])
        for season_data in season_totals:
            if season_data.get('leagueAbbrev') == 'NHL':
                season = season_data.get('season')
                game_type = season_data.get('gameTypeId')
                
                if season and game_type in GAME_TYPES:
                    if season not in seasons_map:
                        seasons_map[season] = []
                    if game_type not in seasons_map[season]:
                        seasons_map[season].append(game_type)
        
        return [(season, game_types) for season, game_types in sorted(seasons_map.items())]
    
    def fetch_game_log(self, player_id: int, season: int, game_type: int) -> Optional[Dict]:
        """Fetch game log from NHL API"""
        # Check if already exists
        player_dir = GAME_LOGS_DIR / str(player_id)
        game_type_str = GAME_TYPES[game_type]
        log_file = player_dir / f"{season}_{game_type_str}.json"
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Fetch from API
        url = f"{NHL_API_BASE}/{player_id}/game-log/{season}/{game_type}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('gameLog'):
                return None
            
            # Save game log
            player_dir.mkdir(exist_ok=True)
            with open(log_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 404:
                logger.debug(f"Game log not found: {player_id}/{season}/{game_type}")
            return None
        except Exception as e:
            logger.error(f"Error fetching game log {player_id}/{season}/{game_type}: {e}")
            return None
    
    def aggregate_season(self, player_id: int, season: int, game_type_str: str) -> bool:
        """Aggregate a season's game logs into cumulative stats"""
        game_log_file = GAME_LOGS_DIR / str(player_id) / f"{season}_{game_type_str}.json"
        
        if not game_log_file.exists():
            return False
        
        try:
            with open(game_log_file, 'r') as f:
                data = json.load(f)
            
            game_logs = data.get('gameLog', [])
            if not game_logs:
                return False
            
            # Sort by date
            game_logs.sort(key=lambda x: x.get('gameDate', ''))
            
            # Build cumulative data
            cumulative = {
                'playerId': str(player_id),
                'season': str(season),
                'gameType': game_type_str,
                'games': []
            }
            
            # Running totals
            totals = {
                'gamesPlayed': 0,
                'assists': 0, 'goals': 0, 'points': 0, 'plusMinus': 0,
                'powerPlayGoals': 0, 'powerPlayPoints': 0,
                'gameWinningGoals': 0, 'otGoals': 0,
                'shots': 0, 'shifts': 0,
                'shorthandedGoals': 0, 'shorthandedPoints': 0,
                'pim': 0, 'toi': 0.0
            }
            
            for game in game_logs:
                totals['gamesPlayed'] += 1
                
                # Update totals
                for key in ['assists', 'goals', 'points', 'plusMinus', 'shots', 'shifts', 'pim',
                           'powerPlayGoals', 'powerPlayPoints', 'gameWinningGoals', 'otGoals',
                           'shorthandedGoals', 'shorthandedPoints']:
                    totals[key] += game.get(key, 0)
                
                # Parse TOI
                toi_str = game.get('toi', '0:00')
                if toi_str and toi_str != 'N/A':
                    try:
                        parts = toi_str.split(':')
                        totals['toi'] += int(parts[0]) + int(parts[1]) / 60
                    except:
                        pass
                
                # Calculate averages
                gp = totals['gamesPlayed']
                
                # Add game point
                cumulative['games'].append({
                    'gameId': game.get('gameId'),
                    'gameDate': game.get('gameDate'),
                    'opponent': game.get('opponentAbbrev'),
                    'homeRoadFlag': game.get('homeRoadFlag', 'H'),
                    'gamesPlayed': gp,
                    'assists': totals['assists'],
                    'goals': totals['goals'],
                    'points': totals['points'],
                    'plusMinus': totals['plusMinus'],
                    'powerPlayGoals': totals['powerPlayGoals'],
                    'powerPlayPoints': totals['powerPlayPoints'],
                    'gameWinningGoals': totals['gameWinningGoals'],
                    'otGoals': totals['otGoals'],
                    'shots': totals['shots'],
                    'shifts': totals['shifts'],
                    'shorthandedGoals': totals['shorthandedGoals'],
                    'shorthandedPoints': totals['shorthandedPoints'],
                    'pim': totals['pim'],
                    'avgToi': round(totals['toi'] / gp, 2) if gp > 0 else 0,
                    'avgShots': round(totals['shots'] / gp, 2) if gp > 0 else 0,
                    'avgShifts': round(totals['shifts'] / gp, 2) if gp > 0 else 0,
                    'gameStats': {
                        'assists': game.get('assists', 0),
                        'goals': game.get('goals', 0),
                        'points': game.get('points', 0),
                        'shots': game.get('shots', 0),
                        'toi': game.get('toi', '0:00'),
                        'plusMinus': game.get('plusMinus', 0),
                    }
                })
            
            # Save cumulative file
            player_output_dir = AGGREGATED_STATS_DIR / str(player_id)
            player_output_dir.mkdir(exist_ok=True)
            
            output_file = player_output_dir / f"{season}_{game_type_str}_cumulative.json"
            with open(output_file, 'w') as f:
                json.dump(cumulative, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error aggregating {player_id}/{season}/{game_type_str}: {e}")
            return False
    
    def process_player(self, player_id: int, player_info: Dict) -> bool:
        """Process a single player through the complete pipeline"""
        player_name = player_info.get('name', f'Player {player_id}')
        
        try:
            # Step 1: Fetch or load profile
            profile = self.fetch_player_profile(player_id)
            if not profile:
                logger.warning(f"  └─ No profile available for {player_name}")
                return False
            
            self.stats['profiles_fetched'] += 1
            
            # Step 2: Get seasons
            seasons = self.get_player_seasons(profile)
            if not seasons:
                logger.info(f"  └─ No NHL seasons found for {player_name}")
                return False
            
            logger.info(f"  └─ Found {len(seasons)} seasons")
            
            # Step 3: Fetch game logs for each season
            game_logs_count = 0
            for season, game_types in seasons:
                for game_type_id in game_types:
                    game_log = self.fetch_game_log(player_id, season, game_type_id)
                    if game_log:
                        game_logs_count += 1
                        self.stats['game_logs_fetched'] += 1
                        
                        # Step 4: Aggregate immediately
                        game_type_str = GAME_TYPES[game_type_id]
                        if self.aggregate_season(player_id, season, game_type_str):
                            self.stats['aggregated'] += 1
                    
                    time.sleep(RATE_LIMIT_DELAY)
            
            logger.info(f"  └─ Aggregated {game_logs_count} season files")
            return True
            
        except Exception as e:
            logger.error(f"Error processing player {player_id}: {e}")
            self.stats['errors'].append(f"{player_id} ({player_name}): {str(e)}")
            return False
    
    def run(self, max_players: Optional[int] = None, start_index: int = 0):
        """Run the complete population process"""
        logger.info("=" * 80)
        logger.info("POPULATE MISSING PLAYER STATS - COMPLETE PIPELINE")
        logger.info("=" * 80)
        logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Get missing players
        missing_players = self.get_missing_players()
        
        if max_players:
            missing_players = missing_players[start_index:start_index + max_players]
            logger.info(f"Processing subset: {len(missing_players)} players (starting at index {start_index})")
        
        self.stats['total_players'] = len(missing_players)
        
        # Load roster for player names
        with open(ROSTER_FILE, 'r') as f:
            roster = json.load(f)
        player_lookup = {p['id']: p for p in roster['players']}
        
        start_time = time.time()
        
        # Process each player
        for idx, player_id in enumerate(missing_players, 1):
            player_info = player_lookup.get(player_id, {})
            player_name = player_info.get('name', f'Player {player_id}')
            team = player_info.get('currentTeam', '??')
            
            logger.info(f"\n[{idx}/{len(missing_players)}] Processing: {player_name} (ID: {player_id}, Team: {team})")
            
            success = self.process_player(player_id, player_info)
            
            if success:
                self.stats['processed'] += 1
            else:
                self.stats['failed'] += 1
            
            # Track as processed
            if player_id not in self.progress_data['processed_ids']:
                self.progress_data['processed_ids'].append(player_id)
            
            # Save progress periodically
            if idx % SAVE_INTERVAL == 0:
                self.save_progress(player_id)
                elapsed = time.time() - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                remaining = (len(missing_players) - idx) / rate if rate > 0 else 0
                
                logger.info("")
                logger.info("=" * 80)
                logger.info("PROGRESS UPDATE")
                logger.info("=" * 80)
                logger.info(f"Players: {idx}/{len(missing_players)}")
                logger.info(f"Profiles fetched: {self.stats['profiles_fetched']}")
                logger.info(f"Game logs fetched: {self.stats['game_logs_fetched']}")
                logger.info(f"Files aggregated: {self.stats['aggregated']}")
                logger.info(f"Failed: {self.stats['failed']}")
                logger.info(f"Rate: {rate:.2f} players/sec")
                logger.info(f"Estimated remaining: {remaining/60:.1f} minutes")
                logger.info("=" * 80)
        
        # Final save
        if missing_players:
            self.save_progress(missing_players[-1])
        
        # Final summary
        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 80)
        logger.info("POPULATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total players processed: {self.stats['processed']}/{len(missing_players)}")
        logger.info(f"Profiles fetched: {self.stats['profiles_fetched']}")
        logger.info(f"Game logs fetched: {self.stats['game_logs_fetched']}")
        logger.info(f"Cumulative files created: {self.stats['aggregated']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
        logger.info(f"Average rate: {self.stats['processed']/elapsed:.2f} players/sec")
        logger.info("=" * 80)
        
        if self.stats['errors']:
            logger.warning(f"\nErrors ({len(self.stats['errors'])} total):")
            for error in self.stats['errors'][:10]:
                logger.warning(f"  - {error}")
    
    def get_missing_players(self) -> List[int]:
        """Same as before but integrated"""
        with open(ROSTER_FILE, 'r') as f:
            roster = json.load(f)
        
        all_player_ids = {p['id'] for p in roster['players']}
        existing_stats = {int(d.name) for d in AGGREGATED_STATS_DIR.iterdir() if d.is_dir() and d.name.isdigit()}
        missing = list(all_player_ids - existing_stats)
        
        # Remove already processed
        processed_ids = set(self.progress_data.get('processed_ids', []))
        return sorted([pid for pid in missing if pid not in processed_ids])


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Populate missing player aggregated stats')
    parser.add_argument('--max', type=int, help='Maximum number of players to process')
    parser.add_argument('--start', type=int, default=0, help='Start index')
    parser.add_argument('--reset-progress', action='store_true', help='Reset progress file')
    
    args = parser.parse_args()
    
    # Reset progress if requested
    if args.reset_progress and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        logger.info("Progress file reset")
    
    populator = PlayerStatsPopulator()
    populator.run(max_players=args.max, start_index=args.start)


if __name__ == "__main__":
    main()

