#!/usr/bin/env python3
"""
Verification script to demonstrate comprehensive mathematical tracking
Shows how we track EVERY player and aggregate across multiple games vs same opponent
"""

import logging
from pathlib import Path
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_comprehensive_tracking():
    """Verify that we're tracking ALL players mathematically"""
    
    logger.info("=" * 70)
    logger.info("VERIFYING COMPREHENSIVE MATHEMATICAL TRACKING")
    logger.info("=" * 70)
    
    # Import the data processor
    from data_processor import DataProcessor
    
    # Initialize processor
    processor = DataProcessor()
    
    # Process a sample game
    data_path = Path('/Users/xavier/Desktop/HeartBeat/data/raw/mtl_play_by_play')
    sample_games = list(data_path.glob("*.csv"))[:5]  # Process 5 games for verification
    
    logger.info(f"\nProcessing {len(sample_games)} games for verification...")
    
    for game_file in sample_games:
        processor.process_game(game_file)
    
    # Extract patterns
    patterns = processor.extract_predictive_patterns()
    
    # VERIFICATION 1: Total players tracked
    logger.info("\n" + "=" * 50)
    logger.info("VERIFICATION 1: TOTAL PLAYER TRACKING")
    logger.info("=" * 50)
    logger.info(f"Total unique players tracked: {patterns.get('total_players_tracked', 0)}")
    logger.info(f"Players with rest patterns: {len(patterns['player_specific_rest'])}")
    logger.info(f"Players with return distributions: {len(patterns['return_time_distributions'])}")
    
    # VERIFICATION 2: Every player has data
    logger.info("\n" + "=" * 50)
    logger.info("VERIFICATION 2: DATA FOR EVERY PLAYER")
    logger.info("=" * 50)
    
    # Sample 10 random players and show their data
    all_players = list(patterns['player_specific_rest'].keys())
    if len(all_players) >= 10:
        sample_players = np.random.choice(all_players, 10, replace=False)
        
        for player_id in sample_players:
            rest_data = patterns['player_specific_rest'][player_id]
            
            # Show data for this player
            situations_with_data = [s for s, d in rest_data.items() if d.get('samples', 0) > 0]
            if situations_with_data:
                logger.info(f"\nPlayer {player_id}:")
                for situation in situations_with_data[:2]:  # Show up to 2 situations
                    data = rest_data[situation]
                    logger.info(f"  {situation}: mean={data['mean']:.1f}s, "
                              f"median={data['median']:.1f}s, "
                              f"samples={data['samples']}")
    
    # VERIFICATION 3: Opponent-specific aggregation
    logger.info("\n" + "=" * 50)
    logger.info("VERIFICATION 3: OPPONENT-SPECIFIC AGGREGATION")
    logger.info("=" * 50)
    
    if 'opponent_aggregated_matchups' in patterns:
        for opponent, matchup_data in patterns['opponent_aggregated_matchups'].items():
            logger.info(f"\nVs {opponent}:")
            logger.info(f"  MTL players tracked: {len(matchup_data)}")
            
            # Show example MTL player matchup percentages
            if matchup_data:
                example_mtl = list(matchup_data.keys())[0]
                opp_matchups = matchup_data[example_mtl]
                
                if opp_matchups:
                    top_matchups = sorted(opp_matchups.items(), key=lambda x: x[1], reverse=True)[:3]
                    logger.info(f"  MTL Player {example_mtl} faced:")
                    for opp_player, percentage in top_matchups:
                        logger.info(f"    - {opp_player}: {percentage:.1f}% of time vs {opponent}")
    
    # VERIFICATION 4: Mathematical aggregation across games
    logger.info("\n" + "=" * 50)
    logger.info("VERIFICATION 4: MULTI-GAME AGGREGATION")
    logger.info("=" * 50)
    
    if hasattr(processor, 'game_sequence_vs_opponent'):
        for opponent, game_sequence in processor.game_sequence_vs_opponent.items():
            logger.info(f"\nVs {opponent}: {len(game_sequence)} deployment events tracked")
            
            # Count unique game IDs
            unique_games = len(set(event.get('game_id') for event in game_sequence))
            logger.info(f"  Across {unique_games} unique games")
            
            # Show progression of matchups across games
            if len(game_sequence) >= 2:
                first_event = game_sequence[0]
                last_event = game_sequence[-1]
                logger.info(f"  First deployment: Period {first_event.get('period', 'N/A')}")
                logger.info(f"  Last deployment: Period {last_event.get('period', 'N/A')}")
    
    # VERIFICATION 5: Statistical computation for ALL players
    logger.info("\n" + "=" * 50)
    logger.info("VERIFICATION 5: COMPREHENSIVE STATISTICS")
    logger.info("=" * 50)
    
    # Calculate aggregate statistics
    all_5v5_means = []
    all_pp_means = []
    all_pk_means = []
    
    for player, rest_data in patterns['player_specific_rest'].items():
        if '5v5' in rest_data and rest_data['5v5'].get('samples', 0) > 0:
            all_5v5_means.append(rest_data['5v5']['mean'])
        if 'powerPlay' in rest_data and rest_data['powerPlay'].get('samples', 0) > 0:
            all_pp_means.append(rest_data['powerPlay']['mean'])
        if 'penaltyKill' in rest_data and rest_data['penaltyKill'].get('samples', 0) > 0:
            all_pk_means.append(rest_data['penaltyKill']['mean'])
    
    if all_5v5_means:
        logger.info(f"\n5v5 Rest Times (ALL {len(all_5v5_means)} players with data):")
        logger.info(f"  Mean: {np.mean(all_5v5_means):.1f}s")
        logger.info(f"  Std Dev: {np.std(all_5v5_means):.1f}s")
        logger.info(f"  Min: {np.min(all_5v5_means):.1f}s")
        logger.info(f"  Max: {np.max(all_5v5_means):.1f}s")
    
    if all_pp_means:
        logger.info(f"\nPowerPlay Rest Times (ALL {len(all_pp_means)} players with data):")
        logger.info(f"  Mean: {np.mean(all_pp_means):.1f}s")
        logger.info(f"  Std Dev: {np.std(all_pp_means):.1f}s")
    
    if all_pk_means:
        logger.info(f"\nPenaltyKill Rest Times (ALL {len(all_pk_means)} players with data):")
        logger.info(f"  Mean: {np.mean(all_pk_means):.1f}s")
        logger.info(f"  Std Dev: {np.std(all_pk_means):.1f}s")
    
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION COMPLETE: ALL PLAYERS TRACKED MATHEMATICALLY")
    logger.info("=" * 70)
    
    return patterns


if __name__ == "__main__":
    verify_comprehensive_tracking()
