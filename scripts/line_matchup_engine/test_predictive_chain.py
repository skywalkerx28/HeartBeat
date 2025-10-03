"""
Test script for predictive chain functionality
Verifies temporal pattern extraction and chain predictions
"""

import torch
import numpy as np
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_predictive_chain():
    """Test the predictive chain capabilities"""
    
    logger.info("Testing predictive chain functionality...")
    
    # Import modules
    from conditional_logit_model import PyTorchConditionalLogit, device
    from data_processor import DataProcessor
    
    # Initialize model
    model = PyTorchConditionalLogit(
        n_context_features=20,
        embedding_dim=32
    ).to(device)
    
    logger.info(f"Model initialized on {device}")
    
    # Test predictive chain
    current_state = {
        'current_deployment': ['player_1', 'player_2', 'player_3', 'player_4', 'player_5'],
        'game_clock': 600,  # 10 minutes into period
        'period': 2,
        'period_time': 600,
        'strength': '5v5',
        'score_diff': 0,
        'context': torch.zeros(20),
        'opponent_on_ice': ['mtl_1', 'mtl_2', 'mtl_3', 'mtl_4', 'mtl_5'],
        'player_last_shift_end': {
            'player_6': 500,  # Rested 100 seconds
            'player_7': 450,  # Rested 150 seconds
            'player_8': 480,
            'player_9': 520,
            'player_10': 400
        }
    }
    
    # Mock rest patterns
    rest_patterns = {
        'player_1': {'mean': 90, 'std': 15},
        'player_2': {'mean': 85, 'std': 12},
        'player_3': {'mean': 95, 'std': 18},
        'player_4': {'mean': 100, 'std': 20},
        'player_5': {'mean': 88, 'std': 14},
        'player_6': {'mean': 92, 'std': 16},
        'player_7': {'mean': 87, 'std': 13},
        'player_8': {'mean': 90, 'std': 15},
        'player_9': {'mean': 85, 'std': 12},
        'player_10': {'mean': 95, 'std': 17}
    }
    
    # Register test players
    test_players = [f'player_{i}' for i in range(1, 21)]
    test_players.extend([f'mtl_{i}' for i in range(1, 21)])
    model.register_players(test_players)
    
    # Set model to eval mode for testing (avoids BatchNorm issues)
    model.eval()
    
    # Test prediction chain
    predictions = model.predict_deployment_chain(
        current_state,
        rest_patterns,
        n_future=3
    )
    
    logger.info("\n=== PREDICTIVE CHAIN RESULTS ===")
    
    for i, pred in enumerate(predictions, 1):
        logger.info(f"\nPrediction {i} (+{pred['time_offset']:.0f} seconds):")
        logger.info(f"  Deployment: {pred['deployment']}")
        logger.info(f"  Probability: {pred['probability']:.3f}")
        logger.info(f"  Confidence: {pred['confidence']:.3f}")
        
        if 'top_3_alternatives' in pred:
            logger.info("  Top alternatives:")
            for j, alt in enumerate(pred['top_3_alternatives'][:3], 1):
                logger.info(f"    {j}. {alt['deployment']} ({alt['probability']:.3f})")
    
    # Test shift length estimation
    logger.info("\n=== SHIFT LENGTH ESTIMATES ===")
    
    test_situations = [
        {'strength': '5v5', 'period': 1, 'score_diff': 0},
        {'strength': 'powerPlay', 'period': 2, 'score_diff': 1},
        {'strength': 'penaltyKill', 'period': 2, 'score_diff': -1},
        {'strength': '3v3', 'period': 4, 'score_diff': 0},  # OT
        {'strength': '5v5', 'period': 3, 'score_diff': -2},  # Trailing late
        {'strength': '5v5', 'period': 3, 'score_diff': 2},   # Leading late
    ]
    
    for situation in test_situations:
        est_length = model._estimate_shift_length(situation)
        logger.info(f"  {situation}: {est_length:.1f} seconds")
    
    logger.info("\n=== TEST COMPLETE ===")
    return True


def test_data_processor():
    """Test the enhanced data processor with temporal tracking"""
    
    logger.info("\nTesting DataProcessor temporal extraction...")
    
    from data_processor import DataProcessor
    
    # Initialize processor
    processor = DataProcessor()
    
    # Test temporal parsing
    test_timecodes = [
        "00:00:30:00",  # 30 seconds
        "00:02:15:00",  # 2 min 15 sec
        "00:10:45:15",  # 10 min 45.5 sec
        "01:05:00:00",  # 1 hour 5 min
    ]
    
    logger.info("\nTimecode parsing tests:")
    for tc in test_timecodes:
        seconds = processor._parse_timecode_to_seconds(tc)
        logger.info(f"  {tc} → {seconds:.1f} seconds")
    
    # Test predictive pattern extraction
    # Mock some rest patterns
    processor.player_rest_patterns = {
        'matthews': {
            '5v5': [
                {'real_rest_seconds': 85, 'game_clock_rest': 80},
                {'real_rest_seconds': 92, 'game_clock_rest': 85},
                {'real_rest_seconds': 78, 'game_clock_rest': 75}
            ],
            'powerPlay': [
                {'real_rest_seconds': 125, 'game_clock_rest': 115},
                {'real_rest_seconds': 135, 'game_clock_rest': 125}
            ]
        },
        'marner': {
            '5v5': [
                {'real_rest_seconds': 80, 'game_clock_rest': 75},
                {'real_rest_seconds': 88, 'game_clock_rest': 82}
            ]
        }
    }
    
    patterns = processor.extract_predictive_patterns()
    
    logger.info("\nExtracted patterns:")
    if 'player_specific_rest' in patterns:
        for player, situations in patterns['player_specific_rest'].items():
            logger.info(f"  {player}:")
            for situation, stats in situations.items():
                logger.info(f"    {situation}: avg={stats['mean']:.1f}s, std={stats['std']:.1f}s")
    
    logger.info("\n✓ DataProcessor test complete")
    return True


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("HEARTBEAT PREDICTIVE CHAIN TEST SUITE")
    logger.info("=" * 60)
    
    # Run tests
    test_predictive_chain()
    test_data_processor()
    
    logger.info("\n" + "=" * 60)
    logger.info("ALL TESTS COMPLETE")
    logger.info("=" * 60)
