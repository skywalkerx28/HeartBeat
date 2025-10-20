#!/usr/bin/env python3
"""
Find all players that appear in league_player_stats but don't have contracts.
This script will identify which players need contract data scraped.
"""

import os
import glob
import pandas as pd
from pathlib import Path
import re
import json
from datetime import datetime

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATS_DIR = BASE_DIR / "data" / "processed" / "league_player_stats"
CONTRACTS_DIR = BASE_DIR / "data" / "contracts"
OUTPUT_FILE = BASE_DIR / "data" / "contracts" / "missing_contracts_players.json"

def extract_player_ids_from_stats():
    """Extract all unique player IDs from league_player_stats CSV files."""
    print("Extracting player IDs from league_player_stats...")
    
    all_player_ids = {}
    
    # Find all unified_player_stats CSV files
    stats_files = glob.glob(str(STATS_DIR / "*" / "unified_player_stats_*.csv"))
    
    print(f"Found {len(stats_files)} stat files to process")
    
    for stats_file in stats_files:
        season = Path(stats_file).parent.name
        print(f"  Processing {season}...")
        
        try:
            # Read CSV with player data
            df = pd.read_csv(stats_file)
            
            # Check if Player ID column exists
            if 'Player ID' not in df.columns:
                print(f"    WARNING: No 'Player ID' column in {stats_file}")
                continue
            
            # Extract player IDs (filter out NaN and empty strings)
            player_ids = df['Player ID'].dropna()
            player_ids = player_ids[player_ids != '']
            
            # Convert to integers (some may be stored as floats)
            player_ids = player_ids.astype(int).astype(str)
            
            # Also extract player names for reference
            for idx, row in df.iterrows():
                player_id = row.get('Player ID')
                player_name = row.get('Player')
                
                if pd.notna(player_id) and player_id != '':
                    player_id_str = str(int(player_id))
                    
                    if player_id_str not in all_player_ids:
                        all_player_ids[player_id_str] = {
                            'name': player_name,
                            'seasons': []
                        }
                    
                    if season not in all_player_ids[player_id_str]['seasons']:
                        all_player_ids[player_id_str]['seasons'].append(season)
            
        except Exception as e:
            print(f"    ERROR processing {stats_file}: {e}")
    
    print(f"\nTotal unique players in stats: {len(all_player_ids)}")
    return all_player_ids

def extract_player_ids_from_contracts():
    """Extract all player IDs from contract CSV filenames."""
    print("\nExtracting player IDs from contract files...")
    
    player_ids_with_contracts = set()
    
    # Find all contract CSV files (excluding batch summaries)
    contract_files = glob.glob(str(CONTRACTS_DIR / "*" / "*.csv"))
    
    # Pattern to extract player ID from filename: lastname_PLAYERID_summary_timestamp.csv
    pattern = re.compile(r'_(\d{7})_summary_')
    
    for contract_file in contract_files:
        filename = os.path.basename(contract_file)
        
        # Skip batch summary files
        if filename.startswith('batch_summary'):
            continue
        
        match = pattern.search(filename)
        if match:
            player_id = match.group(1)
            player_ids_with_contracts.add(player_id)
    
    print(f"Total unique players with contracts: {len(player_ids_with_contracts)}")
    return player_ids_with_contracts

def find_missing_contracts(stats_players, contract_player_ids):
    """Find players in stats but not in contracts."""
    print("\nFinding players missing contracts...")
    
    missing = []
    
    for player_id, info in stats_players.items():
        if player_id not in contract_player_ids:
            missing.append({
                'player_id': player_id,
                'player_name': info['name'],
                'seasons_played': info['seasons'],
                'num_seasons': len(info['seasons']),
                'most_recent_season': max(info['seasons']) if info['seasons'] else None
            })
    
    # Sort by most recent season (descending) and then by name
    missing.sort(key=lambda x: (x['most_recent_season'] or '', x['player_name'] or ''), reverse=True)
    
    print(f"\nPlayers missing contracts: {len(missing)}")
    return missing

def save_missing_players(missing_players):
    """Save missing players to JSON file."""
    print(f"\nSaving missing players to {OUTPUT_FILE}...")
    
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'total_missing': len(missing_players),
        'players': missing_players
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Saved {len(missing_players)} missing players")
    
    # Also create a simple CSV for easy viewing
    csv_output = OUTPUT_FILE.parent / "missing_contracts_players.csv"
    df = pd.DataFrame(missing_players)
    df.to_csv(csv_output, index=False)
    print(f"Also saved to CSV: {csv_output}")
    
    return output_data

def print_summary(missing_players):
    """Print summary statistics."""
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if not missing_players:
        print("All players in stats have contract data!")
        return
    
    # Show first 20 missing players
    print(f"\nFirst 20 missing players (most recent to oldest):")
    print(f"{'Player Name':<30} {'Player ID':<12} {'Seasons':<10} {'Most Recent':<12}")
    print("-" * 80)
    
    for player in missing_players[:20]:
        name = player['player_name'][:28] if player['player_name'] else 'Unknown'
        player_id = player['player_id']
        num_seasons = player['num_seasons']
        recent = player['most_recent_season'] or 'N/A'
        print(f"{name:<30} {player_id:<12} {num_seasons:<10} {recent:<12}")
    
    if len(missing_players) > 20:
        print(f"\n... and {len(missing_players) - 20} more players")
    
    # Statistics by most recent season
    print("\n\nBreakdown by most recent season:")
    season_counts = {}
    for player in missing_players:
        season = player['most_recent_season'] or 'Unknown'
        season_counts[season] = season_counts.get(season, 0) + 1
    
    for season in sorted(season_counts.keys(), reverse=True):
        print(f"  {season}: {season_counts[season]} players")

def main():
    print("="*80)
    print("FIND PLAYERS MISSING CONTRACT DATA")
    print("="*80)
    
    # Step 1: Extract player IDs from stats
    stats_players = extract_player_ids_from_stats()
    
    # Step 2: Extract player IDs from contracts
    contract_player_ids = extract_player_ids_from_contracts()
    
    # Step 3: Find missing players
    missing_players = find_missing_contracts(stats_players, contract_player_ids)
    
    # Step 4: Save results
    output_data = save_missing_players(missing_players)
    
    # Step 5: Print summary
    print_summary(missing_players)
    
    print("\n" + "="*80)
    print(f"Results saved to:")
    print(f"  JSON: {OUTPUT_FILE}")
    print(f"  CSV:  {OUTPUT_FILE.parent / 'missing_contracts_players.csv'}")
    print("="*80)

if __name__ == "__main__":
    main()

