"""
Test script for Daily Active Roster Sync

This script tests the roster sync functionality without requiring
a full environment setup. It validates the logic and data processing.
"""

import sys
from pathlib import Path

# Mock data for testing
MOCK_ACTIVE_ROSTERS = {
    "MTL": [8478445, 8477500, 8475314],  # Sample player IDs
    "NYI": [8478445, 8477494, 8481601],
}

MOCK_CONTRACTS = [
    {"nhl_player_id": 8478445, "full_name": "Player A", "team_abbrev": "MTL", "roster_status": "MINOR"},
    {"nhl_player_id": 8477500, "full_name": "Player B", "team_abbrev": "MTL", "roster_status": "MINOR"},
    {"nhl_player_id": 8475314, "full_name": "Player C", "team_abbrev": "MTL", "roster_status": "NHL"},
    {"nhl_player_id": 8477494, "full_name": "Player D", "team_abbrev": "NYI", "roster_status": "MINOR"},
    {"nhl_player_id": 9999999, "full_name": "Player E", "team_abbrev": "MTL", "roster_status": "NHL"},  # Not on roster
    {"nhl_player_id": 8481601, "full_name": "Player F (IR)", "team_abbrev": "NYI", "roster_status": "IR"},  # On roster but injured
    {"nhl_player_id": 8888888, "full_name": "Player G (LTIR)", "team_abbrev": "MTL", "roster_status": "LTIR"},  # Not on roster, LTIR
    {"nhl_player_id": 8481601, "full_name": "Player H (soir)", "team_abbrev": "NYI", "roster_status": "soir"},  # On roster, signed on IR
    {"nhl_player_id": 9999998, "full_name": "Player I (Loan)", "team_abbrev": "MTL", "roster_status": "Loan"},  # Not on roster, on loan
]


def test_roster_status_logic():
    """Test the roster status assignment logic"""
    print("Testing Roster Status Logic")
    print("=" * 50)
    
    # Build active NHL player set
    active_nhl_players = set()
    for team, players in MOCK_ACTIVE_ROSTERS.items():
        active_nhl_players.update(players)
    
    print(f"Active NHL Players: {active_nhl_players}")
    print()
    
    # Test status updates
    status_changes = []
    ir_preserved = []
    
    for contract in MOCK_CONTRACTS:
        player_id = contract['nhl_player_id']
        old_status = contract['roster_status']
        
        # Preserve special contract statuses
        special_statuses = ['IR', 'LTIR', 'ir', 'ltir', 'soir', 'Loan', 'loan']
        if old_status in special_statuses:
            new_status = old_status  # Keep same status
            ir_preserved.append(contract['full_name'])
            print(f"{contract['full_name']:25} {contract['team_abbrev']:5} {old_status:10} -> {new_status:10} (PRESERVED)")
            continue
        
        # Determine new status
        if player_id in active_nhl_players:
            new_status = 'NHL'
        else:
            new_status = 'MINOR'
        
        # Log change
        if old_status != new_status:
            status_changes.append({
                'player': contract['full_name'],
                'team': contract['team_abbrev'],
                'old': old_status,
                'new': new_status
            })
        
        print(f"{contract['full_name']:25} {contract['team_abbrev']:5} {old_status:10} -> {new_status:10}")
    
    print()
    print(f"Status Changes: {len(status_changes)}")
    for change in status_changes:
        print(f"  - {change['player']} ({change['team']}): {change['old']} -> {change['new']}")
    
    # Validate expectations
    print()
    print(f"Special Statuses Preserved: {len(ir_preserved)}")
    for player in ir_preserved:
        print(f"  - {player}")
    
    print()
    print("Validation:")
    
    expected_changes = 4  # Player A, B (MINOR->NHL), Player D (MINOR->NHL), Player E (NHL->MINOR)
    if len(status_changes) == expected_changes:
        print(f"✓ Correct number of status changes: {expected_changes}")
    else:
        print(f"✗ Expected {expected_changes} changes, got {len(status_changes)}")
    
    # Check special status preservation
    expected_preserved = 4  # Player F (IR), Player G (LTIR), Player H (soir), Player I (Loan)
    if len(ir_preserved) == expected_preserved:
        print(f"✓ Correct number of special statuses preserved: {expected_preserved}")
    else:
        print(f"✗ Expected {expected_preserved} special statuses preserved, got {len(ir_preserved)}")
    
    # Check specific changes
    player_d_change = next((c for c in status_changes if c['player'] == 'Player D'), None)
    if player_d_change and player_d_change['new'] == 'NHL':
        print("✓ Player D correctly moved to NHL")
    else:
        print("✗ Player D status incorrect")
    
    player_e_change = next((c for c in status_changes if c['player'] == 'Player E'), None)
    if player_e_change and player_e_change['new'] == 'MINOR':
        print("✓ Player E correctly moved to MINOR")
    else:
        print("✗ Player E status incorrect")
    
    # Check special status preservation
    if 'Player F (IR)' in ir_preserved:
        print("✓ Player F (IR) status preserved correctly")
    else:
        print("✗ Player F (IR) not preserved")
    
    if 'Player G (LTIR)' in ir_preserved:
        print("✓ Player G (LTIR) status preserved correctly")
    else:
        print("✗ Player G (LTIR) not preserved")
    
    if 'Player H (soir)' in ir_preserved:
        print("✓ Player H (soir) status preserved correctly")
    else:
        print("✗ Player H (soir) not preserved")
    
    if 'Player I (Loan)' in ir_preserved:
        print("✓ Player I (Loan) status preserved correctly")
    else:
        print("✗ Player I (Loan) not preserved")
    
    print()
    print("Test Complete!")


if __name__ == "__main__":
    test_roster_status_logic()

