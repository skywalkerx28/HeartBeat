#!/usr/bin/env python3
"""
Test script for comprehensive hockey extraction
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.comprehensive_hockey_extraction import ComprehensiveHockeyExtractor

def test_extraction():
    """Test extraction on sample data"""
    
    # Use absolute path
    pbp_file = Path(__file__).parent.parent / "data/processed/analytics/nhl_play_by_play/BOS/2024-2025/playsequence-20241008-NHL-BOSvsFLA-20242025-20004.csv"
    
    if not pbp_file.exists():
        print(f"Error: File not found at {pbp_file}")
        return
    
    print(f"Testing extraction on: {pbp_file}")
    
    # Initialize extractor
    extractor = ComprehensiveHockeyExtractor(str(pbp_file))
    
    # Test individual components
    print("\n1. Loading data...")
    extractor.load_data()
    print(f"   Loaded {len(extractor.data)} events")
    
    print("\n2. Extracting game info...")
    game_info = extractor.extract_game_info()
    print(f"   Game: {game_info['away_team']} @ {game_info['home_team']}")
    
    print("\n3. Testing individual matchup extraction (shift-based)...")
    matchups = extractor.extract_individual_matchups()
    total_matchups = sum(len(m) for m in matchups.values())
    print(f"   Found {total_matchups} unique matchup combinations")
    print(f"   Sample matchups: {list(matchups.get('F_vs_F', {}).items())[:3]}")
    
    print("\n3b. Testing matchup duration tracking...")
    durations = extractor.extract_matchup_durations()
    sample_matchup = list(durations.items())[0] if durations else None
    if sample_matchup:
        key, data = sample_matchup
        print(f"   Sample matchup {key}:")
        print(f"     Appearances: {data.get('appearances', 0)}")
        print(f"     Total time: {data.get('total_time', 0):.1f} seconds")
        print(f"     Avg shift: {data.get('avg_shift_length', 0):.1f} seconds")
    
    print("\n4. Testing whistle deployment extraction...")
    deployments = extractor.extract_whistle_deployments()
    print(f"   Analyzed {deployments['total_whistles']} whistles")
    print(f"   Found {len(deployments['deployments'])} deployment patterns")
    
    print("\n5. Testing puck touch chain extraction...")
    chains = extractor.extract_puck_touch_chains()
    print(f"   Found {len(chains.get('chains', []))} puck touch chains")
    print(f"   Average chain length: {chains.get('avg_chain_length', 0):.2f}")
    
    print("\n6. Testing pressure cascade extraction...")
    cascades = extractor.extract_pressure_cascades()
    print(f"   Found {cascades.get('total_pressure_events', 0)} pressure events")
    print(f"   Turnover rate: {cascades.get('turnover_rate', 0):.2%}")
    
    print("\n7. Testing entry-to-shot time extraction...")
    entry_shot = extractor.extract_entry_to_shot_time()
    print(f"   Entries with shots: {entry_shot.get('entries_with_shots', 0)}")
    print(f"   Average time to shot: {entry_shot.get('avg_time_to_shot', 0):.2f} seconds")
    
    print("\n8. Testing player tendency extraction...")
    tendencies = extractor.extract_player_tendencies()
    print(f"   Analyzed {len(tendencies)} players")
    
    # Show sample player
    if tendencies:
        sample_player = list(tendencies.keys())[0]
        sample_data = tendencies[sample_player]
        print(f"   Sample player {sample_player}:")
        print(f"     Total events: {sample_data.get('total_events', 0)}")
        if sample_data.get('top_zones'):
            print(f"     Top zone: {sample_data['top_zones'][0]}")
        if sample_data.get('top_actions'):
            print(f"     Top action: {sample_data['top_actions'][0]}")
    
    print("\n✅ All extraction tests passed successfully!")
    
    # Test save functionality
    print("\n9. Testing save functionality...")
    output_dir = Path(__file__).parent.parent / "data/processed/extracted_metrics/test"
    extractor.results = {
        'game_info': game_info,
        'individual_matchups': matchups,
        'whistle_deployments': deployments
    }
    extractor.save_results(str(output_dir))
    print(f"   Results saved to {output_dir}")
    
    print("\n✨ Test complete!")
    
if __name__ == "__main__":
    test_extraction()
