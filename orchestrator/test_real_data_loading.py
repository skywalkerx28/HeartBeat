"""
Test that real Parquet data is loading correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from orchestrator.tools.parquet_data_client import ParquetDataClient

async def test_data_loading():
    """Test loading real Parquet files"""
    
    print("=" * 80)
    print("TESTING REAL DATA LOADING")
    print("=" * 80)
    
    client = ParquetDataClient("data/processed")
    
    # Test 1: Power Play Stats
    print("\n[TEST 1] Power Play Stats (Toronto)")
    print("-" * 80)
    pp_data = await client.get_power_play_stats(opponent="Toronto")
    print(f"Analysis Type: {pp_data.get('analysis_type')}")
    print(f"Data Source: {pp_data.get('data_source')}")
    print(f"Total PP Units: {pp_data.get('total_pp_units')}")
    print(f"Columns: {pp_data.get('columns', [])[:10]}")  # First 10 columns
    
    if 'pp_data' in pp_data and pp_data['pp_data']:
        print(f"\nSample PP Data (first entry):")
        first_entry = pp_data['pp_data'][0]
        for key, value in list(first_entry.items())[:5]:  # First 5 fields
            print(f"  {key}: {value}")
    
    # Test 2: Matchup Analysis
    print("\n\n[TEST 2] Matchup Analysis (Toronto)")
    print("-" * 80)
    matchup_data = await client.get_matchup_analysis(opponent="Toronto")
    print(f"Analysis Type: {matchup_data.get('analysis_type')}")
    print(f"Data Source: {matchup_data.get('data_source')}")
    print(f"Total Matchups: {matchup_data.get('total_matchups')}")
    print(f"Columns: {matchup_data.get('columns', [])[:10]}")
    
    if 'matchup_data' in matchup_data and matchup_data['matchup_data']:
        print(f"\nSample Matchup Data (first entry):")
        first_entry = matchup_data['matchup_data'][0]
        for key, value in list(first_entry.items())[:5]:
            print(f"  {key}: {value}")
    
    # Test 3: Season Results
    print("\n\n[TEST 3] Season Results")
    print("-" * 80)
    season_data = await client.get_season_results()
    print(f"Analysis Type: {season_data.get('analysis_type')}")
    print(f"Data Source: {season_data.get('data_source')}")
    print(f"Total Games: {season_data.get('total_games')}")
    print(f"Columns: {season_data.get('columns', [])[:10]}")
    
    if 'game_results' in season_data and season_data['game_results']:
        print(f"\nSample Game Result (first entry):")
        first_entry = season_data['game_results'][0]
        for key, value in list(first_entry.items())[:5]:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("✓ DATA LOADING TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_data_loading())

