#!/usr/bin/env python3
"""
Debug script to understand matchup extraction
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict

def debug_matchup_extraction():
    """Debug matchup extraction to understand the numbers"""
    
    # Load data
    pbp_file = Path("data/processed/analytics/nhl_play_by_play/BOS/2024-2025/playsequence-20241008-NHL-BOSvsFLA-20242025-20004.csv")
    data = pd.read_csv(pbp_file)
    
    # Track specific player appearances
    target_player = "8479365"  # Trent Frederic
    shifts = []
    on_ice = False
    shift_start = None
    
    print(f"Tracking player {target_player} shifts...")
    print("=" * 60)
    
    for idx, row in data.iterrows():
        if pd.isna(row['teamForwardsOnIceRefs']) and pd.isna(row['opposingTeamForwardsOnIceRefs']):
            continue
        
        # Check if player is on ice
        team_forwards = str(row.get('teamForwardsOnIceRefs', '')).strip()
        opp_forwards = str(row.get('opposingTeamForwardsOnIceRefs', '')).strip()
        all_forwards = team_forwards + " " + opp_forwards
        
        player_on = target_player in all_forwards
        
        # Track shift starts and ends
        if player_on and not on_ice:
            # Shift start
            shift_start = {
                'start_time': row['gameTime'],
                'period': row['period'],
                'start_idx': idx
            }
            on_ice = True
        elif not player_on and on_ice:
            # Shift end
            if shift_start:
                shift_duration = row['gameTime'] - shift_start['start_time']
                shifts.append({
                    'period': shift_start['period'],
                    'start_time': shift_start['start_time'],
                    'end_time': row['gameTime'],
                    'duration': shift_duration,
                    'events': idx - shift_start['start_idx']
                })
            on_ice = False
            shift_start = None
    
    # Close final shift if still on ice
    if on_ice and shift_start:
        final_time = data.iloc[-1]['gameTime']
        shifts.append({
            'period': shift_start['period'],
            'start_time': shift_start['start_time'],
            'end_time': final_time,
            'duration': final_time - shift_start['start_time'],
            'events': len(data) - shift_start['start_idx']
        })
    
    print(f"Total shifts for player {target_player}: {len(shifts)}")
    print("\nFirst 10 shifts:")
    for i, shift in enumerate(shifts[:10], 1):
        print(f"  Shift {i}: Period {shift['period']}, Duration {shift['duration']:.1f}s, Events: {shift['events']}")
    
    # Now check matchup counts
    print("\n" + "=" * 60)
    print("Checking matchup logic...")
    
    # Simple matchup counter
    matchups_simple = defaultdict(int)
    active_matchups = set()
    
    for idx, row in data.iterrows():
        if pd.isna(row['teamForwardsOnIceRefs']) or pd.isna(row['opposingTeamForwardsOnIceRefs']):
            continue
        
        # Parse players
        team_forwards = set(p.strip() for p in str(row['teamForwardsOnIceRefs']).strip().split(',') if p.strip())
        opp_forwards = set(p.strip() for p in str(row['opposingTeamForwardsOnIceRefs']).strip().split(',') if p.strip())
        
        # Check if our target player is on ice
        if target_player in team_forwards or target_player in opp_forwards:
            # Get all current matchups for this player
            if target_player in team_forwards:
                opponents = opp_forwards
            else:
                opponents = team_forwards
            
            current_pairs = set()
            for opp in opponents:
                pair = f"{target_player}_vs_{opp}"
                current_pairs.add(pair)
                
                # Count if new matchup
                if pair not in active_matchups:
                    matchups_simple[pair] += 1
            
            # Update active matchups for this player
            # Remove old matchups
            to_remove = [m for m in active_matchups if m.startswith(f"{target_player}_vs_")]
            for m in to_remove:
                active_matchups.remove(m)
            # Add new ones
            active_matchups.update(current_pairs)
    
    print(f"\nMatchups for player {target_player}:")
    sorted_matchups = sorted(matchups_simple.items(), key=lambda x: x[1], reverse=True)
    for matchup, count in sorted_matchups[:10]:
        print(f"  {matchup}: {count} appearances")
    
    total_matchup_appearances = sum(matchups_simple.values())
    print(f"\nTotal matchup appearances: {total_matchup_appearances}")
    print(f"Average opponents per shift: {total_matchup_appearances / len(shifts) if shifts else 0:.1f}")


if __name__ == "__main__":
    debug_matchup_extraction()
