#!/usr/bin/env python3
"""
Aggregate Player Game Logs for Temporal Charts

This script processes game log files to create cumulative progression data
for all players across all seasons. Supports game-by-game and monthly views.

Output: Cumulative stats by game date for charting
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
GAME_LOGS_DIR = Path("data/processed/player_profiles/game_logs")
OUTPUT_DIR = Path("data/processed/player_profiles/aggregated_stats")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Metrics to track (all available from game logs)
METRICS = [
    'assists', 'goals', 'points', 'plusMinus', 
    'powerPlayGoals', 'powerPlayPoints', 
    'gameWinningGoals', 'otGoals', 
    'shots', 'shifts', 
    'shorthandedGoals', 'shorthandedPoints',
    'pim', 'toi'
]

def parse_toi(toi_str: str) -> float:
    """Convert TOI string '18:36' to decimal minutes"""
    if not toi_str or toi_str == 'N/A':
        return 0.0
    try:
        parts = toi_str.split(':')
        return int(parts[0]) + int(parts[1]) / 60
    except:
        return 0.0

def process_player_season(player_id: str, season: str, game_type: str) -> Dict:
    """
    Process a single player's season to create cumulative progression data
    
    Returns dict with game-by-game cumulative totals
    """
    game_log_file = GAME_LOGS_DIR / player_id / f"{season}_{game_type}.json"
    
    if not game_log_file.exists():
        return None
    
    try:
        with open(game_log_file, 'r') as f:
            data = json.load(f)
        
        game_logs = data.get('gameLog', [])
        if not game_logs:
            return None
        
        # Sort by game date
        game_logs.sort(key=lambda x: x.get('gameDate', ''))
        
        # Calculate cumulative stats
        cumulative_data = {
            'playerId': player_id,
            'season': season,
            'gameType': game_type,
            'games': []
        }
        
        # Running totals
        running_totals = {metric: 0 for metric in METRICS}
        # Additional running totals for special-team metrics present in game logs
        extra_keys = [
            'powerPlayGoals', 'powerPlayPoints',
            'shorthandedGoals', 'shorthandedPoints',
            'gameWinningGoals', 'otGoals', 'pim'
        ]
        for k in extra_keys:
            running_totals[k] = 0
        running_totals['gamesPlayed'] = 0
        
        for game in game_logs:
            running_totals['gamesPlayed'] += 1
            
            # Update running totals
            for metric in METRICS:
                if metric == 'toi':
                    # For TOI, track total minutes played
                    running_totals[metric] += parse_toi(game.get(metric, '0:00'))
                else:
                    running_totals[metric] += game.get(metric, 0)
            
            # Calculate averages
            gp = running_totals['gamesPlayed']
            avg_toi = running_totals['toi'] / gp if gp > 0 else 0
            avg_shots = running_totals['shots'] / gp if gp > 0 else 0
            avg_shifts = running_totals['shifts'] / gp if gp > 0 else 0
            
            # Store cumulative point
            game_point = {
                'gameId': game.get('gameId'),
                'gameDate': game.get('gameDate'),
                'opponent': game.get('opponentAbbrev'),
                'homeRoadFlag': game.get('homeRoadFlag', 'H'),
                'gamesPlayed': running_totals['gamesPlayed'],
                
                # Cumulative totals
                'assists': running_totals['assists'],
                'goals': running_totals['goals'],
                'points': running_totals['points'],
                'plusMinus': running_totals['plusMinus'],
                'powerPlayGoals': running_totals['powerPlayGoals'],
                'powerPlayPoints': running_totals['powerPlayPoints'],
                'gameWinningGoals': running_totals['gameWinningGoals'],
                'otGoals': running_totals['otGoals'],
                'shots': running_totals['shots'],
                'shifts': running_totals['shifts'],
                'shorthandedGoals': running_totals['shorthandedGoals'],
                'shorthandedPoints': running_totals['shorthandedPoints'],
                'pim': running_totals['pim'],
                
                # Special team cumulative totals if present
                'powerPlayGoals': running_totals.get('powerPlayGoals'),
                'powerPlayPoints': running_totals.get('powerPlayPoints'),
                'shorthandedGoals': running_totals.get('shorthandedGoals'),
                'shorthandedPoints': running_totals.get('shorthandedPoints'),
                'gameWinningGoals': running_totals.get('gameWinningGoals'),
                'otGoals': running_totals.get('otGoals'),
                'pim': running_totals.get('pim'),

                # Averages (useful for per-game metrics)
                'avgToi': round(avg_toi, 2),
                'avgShots': round(avg_shots, 2),
                'avgShifts': round(avg_shifts, 2),
                
                # This game's individual stats (for tooltip)
                'gameStats': {
                    'assists': game.get('assists', 0),
                    'goals': game.get('goals', 0),
                    'points': game.get('points', 0),
                    'shots': game.get('shots', 0),
                    'toi': game.get('toi', '0:00'),
                    'plusMinus': game.get('plusMinus', 0),
                    'powerPlayGoals': game.get('powerPlayGoals', 0),
                    'powerPlayPoints': game.get('powerPlayPoints', 0),
                    'shorthandedGoals': game.get('shorthandedGoals', 0) or game.get('shortHandedGoals', 0),
                    'shorthandedPoints': game.get('shorthandedPoints', 0) or game.get('shortHandedPoints', 0),
                    'gameWinningGoals': game.get('gameWinningGoals', 0),
                    'otGoals': game.get('otGoals', 0),
                    'pim': game.get('pim', 0),
                }
            }
            
            # Update extra running totals using this game's stats
            gs = game_point['gameStats']
            running_totals['powerPlayGoals'] += gs.get('powerPlayGoals', 0)
            running_totals['powerPlayPoints'] += gs.get('powerPlayPoints', 0)
            running_totals['shorthandedGoals'] += gs.get('shorthandedGoals', 0)
            running_totals['shorthandedPoints'] += gs.get('shorthandedPoints', 0)
            running_totals['gameWinningGoals'] += gs.get('gameWinningGoals', 0)
            running_totals['otGoals'] += gs.get('otGoals', 0)
            running_totals['pim'] += gs.get('pim', 0)

            cumulative_data['games'].append(game_point)
        
        return cumulative_data
        
    except Exception as e:
        logger.error(f"Error processing {player_id}/{season}_{game_type}: {e}")
        return None

def aggregate_all_players():
    """Process all players and create aggregated stat files"""
    
    logger.info("Starting aggregation of all player game logs...")
    
    player_dirs = [d for d in GAME_LOGS_DIR.iterdir() if d.is_dir()]
    total_players = len(player_dirs)
    
    processed = 0
    skipped = 0
    
    for idx, player_dir in enumerate(player_dirs, 1):
        player_id = player_dir.name
        
        # Get all game log files for this player
        game_log_files = list(player_dir.glob("*.json"))
        
        if not game_log_files:
            skipped += 1
            continue
        
        # Create output directory for this player
        player_output_dir = OUTPUT_DIR / player_id
        player_output_dir.mkdir(exist_ok=True)
        
        # Process each season/game_type combination
        for game_log_file in game_log_files:
            # Extract season and game type from filename
            # Format: 20232024_regular.json or 20232024_playoffs.json
            filename = game_log_file.stem  # Remove .json
            season, game_type = filename.split('_')
            
            cumulative_data = process_player_season(player_id, season, game_type)
            
            if cumulative_data and cumulative_data['games']:
                # Save cumulative progression file
                output_file = player_output_dir / f"{season}_{game_type}_cumulative.json"
                with open(output_file, 'w') as f:
                    json.dump(cumulative_data, f, indent=2)
                
                processed += 1
        
        if idx % 50 == 0:
            logger.info(f"Progress: {idx}/{total_players} players ({processed} files processed)")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"AGGREGATION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total players processed: {total_players}")
    logger.info(f"Total aggregated files created: {processed}")
    logger.info(f"Players skipped (no game logs): {skipped}")
    logger.info(f"Output directory: {OUTPUT_DIR}")

if __name__ == "__main__":
    aggregate_all_players()

