#!/usr/bin/env python3
"""
Compare player IDs from aggregated_stats with unified_roster_historical.json
to identify players that need to be added to the roster.
"""

import json
from pathlib import Path
from typing import Set, Dict, List

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
AGGREGATED_STATS_DIR = BASE_DIR / "data" / "processed" / "player_profiles" / "aggregated_stats"
ROSTER_FILE = BASE_DIR / "data" / "processed" / "rosters" / "unified_roster_historical.json"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "rosters" / "missing_players_from_aggregated_stats.json"

def extract_player_ids_from_aggregated_stats() -> Set[int]:
    """Extract all unique player IDs from aggregated_stats directory."""
    print("Extracting player IDs from aggregated_stats...")
    
    player_ids = set()
    
    if not AGGREGATED_STATS_DIR.exists():
        print(f"ERROR: Aggregated stats directory not found: {AGGREGATED_STATS_DIR}")
        return player_ids
    
    # Each subdirectory is a player ID
    for player_dir in AGGREGATED_STATS_DIR.iterdir():
        if player_dir.is_dir():
            try:
                player_id = int(player_dir.name)
                player_ids.add(player_id)
            except ValueError:
                # Skip non-numeric directory names
                continue
    
    print(f"Found {len(player_ids)} unique player IDs in aggregated_stats")
    return player_ids


def extract_player_ids_from_roster() -> Dict[int, dict]:
    """Extract all player IDs from unified_roster_historical.json."""
    print("Extracting player IDs from unified_roster_historical.json...")
    
    player_data = {}
    
    if not ROSTER_FILE.exists():
        print(f"ERROR: Roster file not found: {ROSTER_FILE}")
        return player_data
    
    try:
        with open(ROSTER_FILE, 'r', encoding='utf-8') as f:
            roster = json.load(f)
        
        players = roster.get('players', [])
        
        for player in players:
            player_id = player.get('id')
            if player_id:
                player_data[player_id] = {
                    'name': player.get('name', ''),
                    'firstName': player.get('firstName', ''),
                    'lastName': player.get('lastName', ''),
                    'currentTeam': player.get('currentTeam', ''),
                    'position': player.get('position', ''),
                }
        
        print(f"Found {len(player_data)} unique player IDs in roster")
        return player_data
        
    except Exception as e:
        print(f"ERROR loading roster: {e}")
        return player_data


def find_missing_players(stats_ids: Set[int], roster_ids: Dict[int, dict]) -> List[int]:
    """Find player IDs in aggregated_stats but not in roster."""
    missing = []
    
    for player_id in sorted(stats_ids):
        if player_id not in roster_ids:
            missing.append(player_id)
    
    return missing


def get_player_info_from_stats(player_id: int) -> dict:
    """Try to extract player info from their aggregated stats files."""
    player_dir = AGGREGATED_STATS_DIR / str(player_id)
    
    if not player_dir.exists():
        return {}
    
    # Look for any JSON file to extract metadata
    json_files = list(player_dir.glob("*.json"))
    
    if not json_files:
        return {}
    
    try:
        with open(json_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract metadata if available
        return {
            'playerId': data.get('playerId', player_id),
            'season': data.get('season', ''),
            'gameType': data.get('gameType', ''),
            'files_count': len(json_files),
        }
    except Exception as e:
        return {'error': str(e)}


def main():
    print("=" * 80)
    print("COMPARING AGGREGATED_STATS WITH UNIFIED_ROSTER_HISTORICAL")
    print("=" * 80)
    print()
    
    # Extract player IDs from both sources
    stats_ids = extract_player_ids_from_aggregated_stats()
    roster_data = extract_player_ids_from_roster()
    
    print()
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    # Find missing players
    missing_ids = find_missing_players(stats_ids, roster_data)
    
    print(f"\nPlayers in aggregated_stats: {len(stats_ids)}")
    print(f"Players in roster: {len(roster_data)}")
    print(f"Missing from roster: {len(missing_ids)}")
    
    if missing_ids:
        print(f"\n--- MISSING PLAYERS (first 20) ---")
        
        missing_details = []
        for i, player_id in enumerate(missing_ids[:20]):
            info = get_player_info_from_stats(player_id)
            print(f"{i+1:3}. Player ID: {player_id:8} - {info}")
            
            missing_details.append({
                'player_id': player_id,
                'metadata': info
            })
        
        if len(missing_ids) > 20:
            print(f"\n... and {len(missing_ids) - 20} more players")
        
        # Save full list to JSON
        output_data = {
            'total_missing': len(missing_ids),
            'missing_player_ids': missing_ids,
            'sample_details': missing_details,
            'stats': {
                'total_in_aggregated_stats': len(stats_ids),
                'total_in_roster': len(roster_data),
                'overlap': len(stats_ids) - len(missing_ids),
                'coverage_percentage': ((len(stats_ids) - len(missing_ids)) / len(stats_ids) * 100) if stats_ids else 0
            }
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✓ Full list saved to: {OUTPUT_FILE}")
    else:
        print("\n✓ All players from aggregated_stats are in the roster!")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Coverage: {((len(stats_ids) - len(missing_ids)) / len(stats_ids) * 100):.1f}%")
    print(f"Missing players need to be added to unified_roster_historical.json")
    print("=" * 80)


if __name__ == "__main__":
    main()

