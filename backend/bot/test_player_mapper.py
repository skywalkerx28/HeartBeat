#!/usr/bin/env python3
"""
Test Player Mapper
Verify that player name mapping works correctly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.player_mapper import get_player_mapper, map_player_name_to_id, get_player_info
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def test_mapper():
    """Test the player mapper with various name formats"""
    
    print("=" * 80)
    print("TESTING PLAYER NAME MAPPER")
    print("=" * 80)
    
    test_cases = [
        # (CapWages name, team_code, expected_result)
        ("Sidney#87 Crosby", "PIT"),
        ("Sidney Crosby", "PIT"),
        ("Crosby, Sidney", "PIT"),
        ("Connor McDavid", "EDM"),
        ("Auston Matthews", "TOR"),
        ("Nathan MacKinnon", "COL"),
        # Test with potential typos
        ("Sidney Crosby", None),  # No team
        ("Crosby", "PIT"),  # Last name only
    ]
    
    mapper = get_player_mapper()
    
    for name, team in test_cases:
        print(f"\n{'=' * 80}")
        print(f"Testing: '{name}' (Team: {team or 'Not specified'})")
        print("-" * 80)
        
        # Get player ID
        player_id = map_player_name_to_id(name, team)
        
        if player_id:
            # Get full player info
            player = get_player_info(name, team)
            
            print(f"✓ MATCH FOUND")
            print(f"  Player ID: {player_id}")
            print(f"  Full Name: {player['name']}")
            print(f"  Team: {player['team']} ({player['teamName']})")
            print(f"  Position: {player['position']}")
            print(f"  Number: #{player['sweaterNumber']}")
        else:
            print(f"✗ NO MATCH FOUND")
    
    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    test_mapper()

