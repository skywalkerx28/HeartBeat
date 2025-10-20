#!/usr/bin/env python3
"""
Test the new contract CSV endpoint
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.routes.market import get_player_contract_from_csv
from fastapi import HTTPException
import asyncio


async def test_contract_endpoint():
    """Test the contract CSV endpoint with a known player"""
    
    test_players = [
        (8479318, "Auston Matthews"),
        (8478402, "Connor McDavid"),
        (8480222, "Sebastian Aho"),
        (9999999, "NonExistent Player - Should 404"),
    ]
    
    print("=" * 80)
    print("TESTING CONTRACT CSV ENDPOINT")
    print("=" * 80)
    
    for player_id, player_name in test_players:
        print(f"\nTesting: {player_name} (ID: {player_id})")
        print("-" * 80)
        
        try:
            response = await get_player_contract_from_csv(player_id)
            
            if response.success:
                data = response.data
                print(f"✓ SUCCESS")
                print(f"  Player: {data.get('full_name', 'N/A')}")
                print(f"  Team: {data.get('team_abbrev', 'N/A')}")
                print(f"  Position: {data.get('position', 'N/A')}")
                print(f"  Contracts: {len(data.get('contracts', []))}")
                print(f"  Contract Details (years): {len(data.get('contract_details', []))}")
                print(f"  Source: {response.source}")
                
                # Show first contract if available
                if data.get('contracts'):
                    c = data['contracts'][0]
                    print(f"\n  Latest Contract:")
                    print(f"    Type: {c.get('type', 'N/A')}")
                    print(f"    Team: {c.get('team', 'N/A')}")
                    print(f"    Signing Date: {c.get('signing_date', 'N/A')}")
                    print(f"    Length: {c.get('length_years', 'N/A')} years")
                    print(f"    Total Value: {c.get('total_value', 'N/A')}")
                
            else:
                print(f"✗ FAILED: {response.error}")
                
        except HTTPException as e:
            print(f"✗ HTTP ERROR {e.status_code}: {e.detail}")
        except Exception as e:
            print(f"✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_contract_endpoint())

