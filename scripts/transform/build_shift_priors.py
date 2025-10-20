#!/usr/bin/env python3
"""
Build shift priors from play-by-play data.

This script analyzes all play-by-play CSV files to extract:
- Average shift length by game situation (EV, PP, PK, 3v3, etc.)
- Average time on ice per game
- Shift frequency patterns
- Rest time statistics

Output: data/processed/dim/player_shift_priors.parquet
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
import logging
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class ShiftExtractor:
    """Extract shift-level statistics from play-by-play data."""
    
    def __init__(self, data_dir: str, player_ids_file: str):
        self.data_dir = Path(data_dir)
        self.player_ids_file = Path(player_ids_file)
        
        # Load player ID mapping
        self.player_lookup = self._load_player_ids()
        
        # Initialize storage for shift data
        self.shift_data = defaultdict(lambda: {
            'EV_shifts': [],      # Even strength 5v5
            'PP_shifts': [],      # Power play (5v4, 5v3)
            'PK_shifts': [],      # Penalty kill (4v5, 3v5)  
            'OT_shifts': [],      # Overtime 3v3, 4v4
            'total_toi': [],      # Time on ice per game
            'games_played': set() # Track unique games played
        })
        
        # Manpower situation mapping
        self.situation_map = {
            'evenstrength': 'EV',
            'powerplay': 'PP', 
            'shorthanded': 'PK',
            'penaltyshot': 'PS',
            '4v4': 'OT',
            '3v3': 'OT',
            '6v5': 'PP',  # Empty net situations
            '5v6': 'PK',
            '6v4': 'PP', 
            '4v6': 'PK',
            '6v3': 'PP',
            '3v6': 'PK'
        }

    def _load_player_ids(self) -> dict:
        """Load player ID mapping from CSV."""
        logger.info(f"Loading player IDs from {self.player_ids_file}")
        df = pd.read_csv(self.player_ids_file)
        
        # Create mapping from reference_id to player info
        player_map = {}
        for _, row in df.iterrows():
            if pd.notna(row['reference_id']):
                player_map[str(int(row['reference_id']))] = {
                    'name': row['full_name'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name']
                }
        
        logger.info(f"Loaded {len(player_map)} player mappings")
        return player_map

    def _clean_player_list(self, player_str: str) -> list:
        """Clean and parse comma-separated player ID string."""
        if pd.isna(player_str) or not player_str.strip():
            return []
        
        # Remove tabs, spaces, and split by comma
        player_ids = [p.strip().replace('\t', '') for p in str(player_str).split(',')]
        return [p for p in player_ids if p and p.isdigit()]

    def _get_manpower_situation(self, manpower_str: str) -> str:
        """Map manpower situation string to category."""
        if pd.isna(manpower_str) or manpower_str == '':
            return 'EV'
        
        # Convert to string and clean
        manpower_clean = str(manpower_str).lower().replace(' ', '').strip()
        
        # Skip if it looks like a numeric coordinate value
        try:
            float(manpower_clean)
            return 'EV'  # Default to even strength for numeric values
        except ValueError:
            pass
        
        return self.situation_map.get(manpower_clean, 'EV')

    def _process_game(self, file_path: Path) -> bool:
        """Process a single game file to extract shift data."""
        try:
            # Load game data
            df = pd.read_csv(file_path)
            
            if df.empty:
                logger.warning(f"Empty file: {file_path}")
                return False
            
            # Sort by game time
            df = df.sort_values('gameTime', ascending=True).reset_index(drop=True)
            
            # Get game identifier for tracking games played
            game_id = file_path.stem
            
            # Track shifts for each player in this game
            # Structure: {player_id: [{start_time, end_time, situation}, ...]}
            player_shifts = defaultdict(list)
            
            # First pass: collect all on-ice appearances for each player
            for idx, row in df.iterrows():
                game_time = row['gameTime']
                situation = self._get_manpower_situation(row.get('manpowerSituation'))
                
                # Get all players on ice
                mtl_forwards = self._clean_player_list(row.get('opposingTeamForwardsOnIceRefs', ''))
                mtl_defense = self._clean_player_list(row.get('opposingTeamDefencemenOnIceRefs', ''))
                opp_forwards = self._clean_player_list(row.get('teamForwardsOnIceRefs', ''))
                opp_defense = self._clean_player_list(row.get('teamDefencemenOnIceRefs', ''))
                
                all_players = set(mtl_forwards + mtl_defense + opp_forwards + opp_defense)
                
                # Record this time point for each player on ice
                for player_id in all_players:
                    if player_id in self.player_lookup:
                        player_shifts[player_id].append({
                            'time': game_time,
                            'situation': situation,
                            'on_ice': True
                        })
            
            # Second pass: identify shift boundaries for each player
            for player_id, appearances in player_shifts.items():
                if not appearances:
                    continue
                
                # Sort appearances by time
                appearances.sort(key=lambda x: x['time'])
                
                # Identify continuous shifts (gaps > 10 seconds indicate shift change)
                shifts = []
                current_shift = None
                
                for i, app in enumerate(appearances):
                    if current_shift is None:
                        # Start new shift
                        current_shift = {
                            'start': app['time'],
                            'end': app['time'],
                            'situation': app['situation']
                        }
                    else:
                        # Check if this is continuation of current shift
                        time_gap = app['time'] - current_shift['end']
                        
                        if time_gap <= 10:  # Within 10 seconds, same shift
                            current_shift['end'] = app['time']
                            # Update situation if it changed during shift
                            if app['situation'] != 'EV' and current_shift['situation'] == 'EV':
                                current_shift['situation'] = app['situation']
                        else:
                            # Gap too large, end current shift and start new one
                            shift_length = current_shift['end'] - current_shift['start']
                            if 20 <= shift_length <= 120:  # Realistic shift bounds
                                shifts.append({
                                    'length': shift_length,
                                    'situation': current_shift['situation']
                                })
                            
                            # Start new shift
                            current_shift = {
                                'start': app['time'],
                                'end': app['time'],
                                'situation': app['situation']
                            }
                
                # Don't forget the last shift
                if current_shift:
                    shift_length = current_shift['end'] - current_shift['start']
                    if 20 <= shift_length <= 120:  # Realistic shift bounds
                        shifts.append({
                            'length': shift_length,
                            'situation': current_shift['situation']
                        })
                
                # Record all shifts for this player
                for shift in shifts:
                    self._record_shift(player_id, shift['length'], shift['situation'], game_id)
                
                # Calculate total TOI for this game
                if shifts:
                    total_toi = sum(s['length'] for s in shifts)
                    self.shift_data[player_id]['total_toi'].append(total_toi)
                    self.shift_data[player_id]['games_played'].add(game_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return False

    def _record_shift(self, player_id: str, shift_length: float, situation: str, game_id: str):
        """Record a completed shift."""
        if player_id not in self.player_lookup:
            return
            
        # Map situation to storage key
        situation_key = f"{situation}_shifts"
        if situation_key in self.shift_data[player_id]:
            self.shift_data[player_id][situation_key].append(shift_length)

    def process_all_seasons(self):
        """Process all seasons of play-by-play data."""
        seasons = ['2022-2023', '2023-2024', '2024-2025']
        
        total_files = 0
        processed_files = 0
        
        for season in seasons:
            season_dir = self.data_dir / season
            if not season_dir.exists():
                logger.warning(f"Season directory not found: {season_dir}")
                continue
            
            csv_files = list(season_dir.glob('*.csv'))
            total_files += len(csv_files)
            
            logger.info(f"Processing {len(csv_files)} games from {season}")
            
            for file_path in tqdm(csv_files, desc=f"Processing {season}"):
                if self._process_game(file_path):
                    processed_files += 1
        
        logger.info(f"Processed {processed_files}/{total_files} game files successfully")

    def calculate_statistics(self) -> pd.DataFrame:
        """Calculate final statistics for all players."""
        logger.info("Calculating player shift statistics...")
        
        stats_list = []
        
        for player_id, data in tqdm(self.shift_data.items(), desc="Computing statistics"):
            if player_id not in self.player_lookup:
                continue
                
            player_info = self.player_lookup[player_id]
            stats = {
                'player_id': int(player_id),
                'player_name': player_info['name'],
                'first_name': player_info['first_name'],
                'last_name': player_info['last_name']
            }
            
            # Calculate statistics for each situation
            for situation in ['EV', 'PP', 'PK', 'OT']:
                shifts = data[f'{situation}_shifts']
                
                if len(shifts) > 0:
                    stats[f'{situation}_shift_mean'] = np.mean(shifts)
                    stats[f'{situation}_shift_std'] = np.std(shifts)
                    stats[f'{situation}_shift_count'] = len(shifts)
                    stats[f'{situation}_shift_median'] = np.median(shifts)
                    stats[f'{situation}_shift_p25'] = np.percentile(shifts, 25)
                    stats[f'{situation}_shift_p75'] = np.percentile(shifts, 75)
                else:
                    stats[f'{situation}_shift_mean'] = 0.0
                    stats[f'{situation}_shift_std'] = 0.0
                    stats[f'{situation}_shift_count'] = 0
                    stats[f'{situation}_shift_median'] = 0.0
                    stats[f'{situation}_shift_p25'] = 0.0
                    stats[f'{situation}_shift_p75'] = 0.0
            
            # Overall statistics
            all_shifts = (data['EV_shifts'] + data['PP_shifts'] + 
                         data['PK_shifts'] + data['OT_shifts'])
            
            if len(all_shifts) > 0:
                stats['overall_shift_mean'] = np.mean(all_shifts)
                stats['overall_shift_std'] = np.std(all_shifts)
                stats['total_shifts'] = len(all_shifts)
                
                # Use unique games count
                games_played = len(data['games_played'])
                stats['avg_shifts_per_game'] = len(all_shifts) / max(1, games_played)
                
                # Average TOI per game
                if data['total_toi']:
                    stats['avg_toi_per_game'] = np.mean(data['total_toi'])
                else:
                    stats['avg_toi_per_game'] = 0.0
            else:
                stats['overall_shift_mean'] = 0.0
                stats['overall_shift_std'] = 0.0
                stats['total_shifts'] = 0
                stats['avg_shifts_per_game'] = 0.0
                stats['avg_toi_per_game'] = 0.0
            
            stats['games_played'] = len(data['games_played'])
            
            stats_list.append(stats)
        
        df = pd.DataFrame(stats_list)
        
        # Sort by total shifts to see most active players
        df = df.sort_values('total_shifts', ascending=False)
        
        logger.info(f"Calculated statistics for {len(df)} players")
        
        return df

    def save_results(self, stats_df: pd.DataFrame, output_path: str):
        """Save results to parquet file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as parquet for efficient loading
        stats_df.to_parquet(output_path, index=False, compression='snappy')
        logger.info(f"Saved shift priors to {output_path}")
        
        # Also save as CSV for inspection
        csv_path = output_path.with_suffix('.csv')
        stats_df.to_csv(csv_path, index=False)
        logger.info(f"Saved shift priors CSV to {csv_path}")
        
        # Print summary statistics
        logger.info("\n=== SHIFT STATISTICS SUMMARY ===")
        logger.info(f"Total players: {len(stats_df)}")
        logger.info(f"Players with EV shifts: {(stats_df['EV_shift_count'] > 0).sum()}")
        logger.info(f"Players with PP shifts: {(stats_df['PP_shift_count'] > 0).sum()}")
        logger.info(f"Players with PK shifts: {(stats_df['PK_shift_count'] > 0).sum()}")
        
        active_players = stats_df[stats_df['total_shifts'] > 100]
        logger.info(f"\nActive players (>100 shifts): {len(active_players)}")
        
        if len(active_players) > 0:
            logger.info(f"Average EV shift length: {active_players[active_players['EV_shift_count'] > 0]['EV_shift_mean'].mean():.1f}s")
            logger.info(f"Average PP shift length: {active_players[active_players['PP_shift_count'] > 0]['PP_shift_mean'].mean():.1f}s")
            logger.info(f"Average PK shift length: {active_players[active_players['PK_shift_count'] > 0]['PK_shift_mean'].mean():.1f}s")
            logger.info(f"Average shifts per game: {active_players['avg_shifts_per_game'].mean():.1f}")
            logger.info(f"Average TOI per game: {active_players['avg_toi_per_game'].mean():.1f}s")
        
        # Show top 10 players by total shifts
        logger.info("\n=== TOP 10 PLAYERS BY TOTAL SHIFTS ===")
        top_10 = stats_df.head(10)[['player_name', 'total_shifts', 'games_played', 'avg_shifts_per_game', 'EV_shift_mean']]
        for _, player in top_10.iterrows():
            logger.info(f"{player['player_name']}: {int(player['total_shifts'])} shifts in {int(player['games_played'])} games "
                       f"({player['avg_shifts_per_game']:.1f} per game, {player['EV_shift_mean']:.1f}s avg)")


def main():
    """Main execution function."""
    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / 'data' / 'mtl_play_by_play'
    player_ids_file = project_root / 'data' / 'processed' / 'dim' / 'player_ids.csv'
    output_file = project_root / 'data' / 'processed' / 'dim' / 'player_shift_priors.parquet'
    
    # Check input files exist
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)
    
    if not player_ids_file.exists():
        logger.error(f"Player IDs file not found: {player_ids_file}")
        sys.exit(1)
    
    logger.info("Starting shift statistics extraction...")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Player IDs file: {player_ids_file}")
    logger.info(f"Output file: {output_file}")
    
    # Initialize extractor
    extractor = ShiftExtractor(data_dir, player_ids_file)
    
    # Process all data
    extractor.process_all_seasons()
    
    # Calculate statistics
    stats_df = extractor.calculate_statistics()
    
    # Save results
    extractor.save_results(stats_df, output_file)
    
    logger.info("Shift statistics extraction completed successfully!")


if __name__ == '__main__':
    main()