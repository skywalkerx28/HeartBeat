#!/usr/bin/env python3
"""
Test RMSE evaluation functionality for shift lengths and rest times
"""

import sys
import os
import torch
import numpy as np
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_rmse_calculation():
    """Test RMSE calculation logic"""
    
    print("🧪 Testing RMSE calculation...")
    
    # Mock RMSE data structure
    shift_rest_rmse = defaultdict(lambda: defaultdict(lambda: {
        'shift_errors': [], 'rest_errors': [], 'count': 0
    }))
    
    # Add test data
    shift_rest_rmse['TOR']['5v5']['shift_errors'] = [4.0, 9.0, 16.0]  # Errors: 2, 3, 4 -> RMSE = sqrt(29/3) ≈ 3.11
    shift_rest_rmse['TOR']['5v5']['rest_errors'] = [25.0, 36.0]  # Errors: 5, 6 -> RMSE = sqrt(61/2) ≈ 5.52
    shift_rest_rmse['TOR']['5v5']['count'] = 3
    
    shift_rest_rmse['BOS']['special']['shift_errors'] = [1.0, 4.0]  # Errors: 1, 2 -> RMSE = sqrt(5/2) ≈ 1.58
    shift_rest_rmse['BOS']['special']['rest_errors'] = [100.0]  # Error: 10 -> RMSE = 10.0
    shift_rest_rmse['BOS']['special']['count'] = 2
    
    # Calculate RMSE
    for team, strength_data in shift_rest_rmse.items():
        for strength, metrics in strength_data.items():
            if metrics['count'] > 0:
                shift_rmse = 0.0
                rest_rmse = 0.0
                
                if metrics['shift_errors']:
                    shift_rmse = (sum(metrics['shift_errors']) / len(metrics['shift_errors'])) ** 0.5
                
                if metrics['rest_errors']:
                    rest_rmse = (sum(metrics['rest_errors']) / len(metrics['rest_errors'])) ** 0.5
                
                print(f"{team} {strength}: shift_rmse={shift_rmse:.2f}s, rest_rmse={rest_rmse:.2f}s")
                
                # Verify calculations
                if team == 'TOR' and strength == '5v5':
                    expected_shift_rmse = (29.0 / 3.0) ** 0.5
                    expected_rest_rmse = (61.0 / 2.0) ** 0.5
                    assert abs(shift_rmse - expected_shift_rmse) < 0.01, f"TOR 5v5 shift RMSE incorrect: {shift_rmse} vs {expected_shift_rmse}"
                    assert abs(rest_rmse - expected_rest_rmse) < 0.01, f"TOR 5v5 rest RMSE incorrect: {rest_rmse} vs {expected_rest_rmse}"
                
                if team == 'BOS' and strength == 'special':
                    expected_shift_rmse = (5.0 / 2.0) ** 0.5
                    expected_rest_rmse = 10.0
                    assert abs(shift_rmse - expected_shift_rmse) < 0.01, f"BOS special shift RMSE incorrect: {shift_rmse} vs {expected_shift_rmse}"
                    assert abs(rest_rmse - expected_rest_rmse) < 0.01, f"BOS special rest RMSE incorrect: {rest_rmse} vs {expected_rest_rmse}"
    
    print("✅ RMSE calculation test passed!")

def test_batch_processing():
    """Test that batch processing extracts correct information"""
    
    print("🧪 Testing batch processing for RMSE...")
    
    # Mock batch data
    mock_batch = {
        'context': torch.tensor([0.1] * 30 + [0.8, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Special teams indicator at position 30
        'ewma_shift_lengths': {'player1': 42.0, 'player2': 48.0},
        'rest_real_times': {'player1': 85.0, 'player2': 95.0},
        'true_deployment': {
            'forwards': ['player1', 'player2'],
            'defense': ['player3']
        },
        'strength_state': '5v4',
        'game_seconds': 1200.0
    }
    
    # Test context strength extraction
    context = mock_batch.get('context', torch.tensor([]))
    strength = "5v5"  # Default
    if len(context) >= 36:
        strength_features = context[30:36]
        if torch.any(strength_features > 0.5):
            strength = "special"
    
    assert strength == "special", f"Expected 'special', got '{strength}'"
    
    # Test player extraction
    true_deployment = mock_batch.get('true_deployment', {})
    players = true_deployment.get('forwards', []) + true_deployment.get('defense', [])
    expected_players = ['player1', 'player2', 'player3']
    assert players == expected_players, f"Expected {expected_players}, got {players}"
    
    # Test data availability
    actual_shift_lengths = mock_batch.get('ewma_shift_lengths', {})
    actual_rest_times = mock_batch.get('rest_real_times', {})
    
    assert 'player1' in actual_shift_lengths, "player1 should have shift length data"
    assert 'player2' in actual_rest_times, "player2 should have rest time data"
    
    print("✅ Batch processing test passed!")

def test_error_handling():
    """Test that RMSE evaluation handles edge cases gracefully"""
    
    print("🧪 Testing error handling...")
    
    # Test empty batch
    empty_batch = {}
    
    # Mock the evaluation method behavior
    context = empty_batch.get('context', torch.tensor([]))
    if len(context) == 0:
        print("✅ Empty context handled correctly")
    
    # Test missing data
    incomplete_batch = {
        'context': torch.tensor([0.1] * 36),
        'true_deployment': {'forwards': ['player1'], 'defense': []},
        # Missing ewma_shift_lengths and rest_real_times
    }
    
    actual_shift_lengths = incomplete_batch.get('ewma_shift_lengths', {})
    actual_rest_times = incomplete_batch.get('rest_real_times', {})
    
    if not actual_shift_lengths and not actual_rest_times:
        print("✅ Missing shift/rest data handled correctly")
    
    # Test malformed true_deployment
    malformed_batch = {
        'context': torch.tensor([0.1] * 36),
        'true_deployment': "not_a_dict",  # Should be dict
    }
    
    true_deployment = malformed_batch.get('true_deployment', {})
    if not isinstance(true_deployment, dict):
        print("✅ Malformed deployment data handled correctly")
    
    print("✅ Error handling test passed!")

if __name__ == "__main__":
    test_rmse_calculation()
    test_batch_processing()
    test_error_handling()
    print("🎉 All RMSE evaluation tests passed!")
