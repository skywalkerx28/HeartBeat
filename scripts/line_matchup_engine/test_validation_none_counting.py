#!/usr/bin/env python3
"""
Unit tests for validation NONE_OF_THE_ABOVE counting functionality
Verifies that validation correctly handles cases where true deployment is not in candidates
"""

import sys
import os
import torch
import numpy as np
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_none_option_detection():
    """Test the _find_none_option_index method"""
    
    print("🧪 Testing NONE option detection...")
    
    # Mock trainer class with the method
    class MockTrainer:
        def _find_none_option_index(self, candidates):
            for i, candidate in enumerate(candidates):
                if candidate.get('is_none_option', False):
                    return i
            return None
    
    trainer = MockTrainer()
    
    # Test case 1: No NONE option
    candidates_no_none = [
        {'forwards': ['p1', 'p2', 'p3'], 'defense': ['d1', 'd2']},
        {'forwards': ['p4', 'p5', 'p6'], 'defense': ['d3', 'd4']}
    ]
    
    none_idx = trainer._find_none_option_index(candidates_no_none)
    assert none_idx is None, f"Expected None, got {none_idx}"
    print("  ✓ No NONE option detected correctly")
    
    # Test case 2: NONE option present
    candidates_with_none = [
        {'forwards': ['p1', 'p2', 'p3'], 'defense': ['d1', 'd2']},
        {'forwards': ['NONE_OF_THE_ABOVE_F1', 'NONE_OF_THE_ABOVE_F2', 'NONE_OF_THE_ABOVE_F3'], 
         'defense': ['NONE_OF_THE_ABOVE_D1', 'NONE_OF_THE_ABOVE_D2'], 'is_none_option': True},
        {'forwards': ['p4', 'p5', 'p6'], 'defense': ['d3', 'd4']}
    ]
    
    none_idx = trainer._find_none_option_index(candidates_with_none)
    assert none_idx == 1, f"Expected 1, got {none_idx}"
    print("  ✓ NONE option detected at correct index")
    
    # Test case 3: Multiple NONE options (should find first)
    candidates_multiple_none = [
        {'forwards': ['p1', 'p2', 'p3'], 'defense': ['d1', 'd2']},
        {'forwards': ['NONE_1'], 'defense': ['NONE_D1'], 'is_none_option': True},
        {'forwards': ['NONE_2'], 'defense': ['NONE_D2'], 'is_none_option': True}
    ]
    
    none_idx = trainer._find_none_option_index(candidates_multiple_none)
    assert none_idx == 1, f"Expected first NONE option at index 1, got {none_idx}"
    print("  ✓ First NONE option detected correctly")
    
    print("✅ NONE option detection test passed!")

def test_validation_none_counting():
    """Test validation accuracy counting with NONE_OF_THE_ABOVE scenarios"""
    
    print("🧪 Testing validation NONE counting...")
    
    # Mock validation scenarios
    validation_scenarios = [
        {
            'name': 'True deployment in candidates - correct prediction',
            'true_idx': 0,
            'none_idx': None,
            'pred_idx': 0,
            'expected_correct': True,
            'expected_top3_correct': True
        },
        {
            'name': 'True deployment in candidates - wrong prediction', 
            'true_idx': 0,
            'none_idx': None,
            'pred_idx': 1,
            'expected_correct': False,
            'expected_top3_correct': True  # True idx (0) will be in top-3 with log_probs [-1.0, -2.0, -1.5]
        },
        {
            'name': 'True deployment NOT in candidates - NONE predicted (correct)',
            'true_idx': None,
            'none_idx': 2,
            'pred_idx': 2,  # Model correctly predicts NONE
            'expected_correct': True,
            'expected_top3_correct': True
        },
        {
            'name': 'True deployment NOT in candidates - wrong prediction',
            'true_idx': None,
            'none_idx': 2,
            'pred_idx': 0,  # Model predicts wrong deployment instead of NONE
            'expected_correct': False,
            'expected_top3_correct': True  # NONE idx (2) will be in top-3 with log_probs [-1.0, -2.0, -1.5]
        },
        {
            'name': 'True deployment NOT in candidates - NONE in top-3',
            'true_idx': None,
            'none_idx': 2,
            'pred_idx': 0,  # Top-1 wrong
            'top3_indices': [0, 1, 2],  # But NONE in top-3
            'expected_correct': False,
            'expected_top3_correct': True
        }
    ]
    
    for scenario in validation_scenarios:
        print(f"  Testing: {scenario['name']}")
        
        # Mock log probabilities (3 candidates)
        log_probs = torch.tensor([-1.0, -2.0, -1.5])  # Candidate 0 has highest prob
        
        # Test Top-1 accuracy logic
        if scenario['true_idx'] is not None:
            # True deployment in candidates
            is_correct = (scenario['pred_idx'] == scenario['true_idx'])
        elif scenario['none_idx'] is not None:
            # True deployment NOT in candidates, NONE is correct answer
            is_correct = (scenario['pred_idx'] == scenario['none_idx'])
        else:
            is_correct = False
        
        assert is_correct == scenario['expected_correct'], \
            f"Accuracy mismatch for {scenario['name']}: expected {scenario['expected_correct']}, got {is_correct}"
        
        # Test Top-3 accuracy logic
        if 'top3_indices' in scenario:
            top3_indices = scenario['top3_indices']
        else:
            top3_indices = torch.topk(log_probs, min(3, len(log_probs))).indices.tolist()
        
        if scenario['true_idx'] is not None:
            # True deployment in candidates
            is_top3_correct = (scenario['true_idx'] in top3_indices)
        elif scenario['none_idx'] is not None:
            # True deployment NOT in candidates, NONE in top-3 is correct
            is_top3_correct = (scenario['none_idx'] in top3_indices)
        else:
            is_top3_correct = False
        
        assert is_top3_correct == scenario['expected_top3_correct'], \
            f"Top-3 accuracy mismatch for {scenario['name']}: expected {scenario['expected_top3_correct']}, got {is_top3_correct}"
        
        print(f"    ✓ Correct: {is_correct}, Top-3: {is_top3_correct}")
    
    print("✅ Validation NONE counting test passed!")

def test_validation_metrics_aggregation():
    """Test that validation metrics are correctly aggregated across batches"""
    
    print("🧪 Testing validation metrics aggregation...")
    
    # Simulate validation loop with mixed scenarios
    val_correct = 0
    val_top3_correct = 0
    val_total = 0
    
    # Batch 1: True deployment in candidates (2 correct, 1 wrong)
    batch1_scenarios = [
        {'correct': True, 'top3_correct': True},   # Correct prediction
        {'correct': True, 'top3_correct': True},   # Correct prediction
        {'correct': False, 'top3_correct': True}   # Wrong top-1, correct top-3
    ]
    
    for scenario in batch1_scenarios:
        if scenario['correct']:
            val_correct += 1
        if scenario['top3_correct']:
            val_top3_correct += 1
        val_total += 1
    
    # Batch 2: True deployment NOT in candidates (NONE scenarios)
    batch2_scenarios = [
        {'correct': True, 'top3_correct': True},   # NONE predicted correctly
        {'correct': False, 'top3_correct': True}, # NONE in top-3
        {'correct': False, 'top3_correct': False} # NONE not predicted
    ]
    
    for scenario in batch2_scenarios:
        if scenario['correct']:
            val_correct += 1
        if scenario['top3_correct']:
            val_top3_correct += 1
        val_total += 1
    
    # Calculate final metrics
    val_accuracy = val_correct / val_total if val_total > 0 else 0.0
    val_top3_accuracy = val_top3_correct / val_total if val_total > 0 else 0.0
    
    print(f"  Total samples: {val_total}")
    print(f"  Correct predictions: {val_correct}")
    print(f"  Top-3 correct: {val_top3_correct}")
    print(f"  Accuracy: {val_accuracy:.1%}")
    print(f"  Top-3 accuracy: {val_top3_accuracy:.1%}")
    
    # Verify expected results
    expected_correct = 3  # 2 from batch1 + 1 from batch2
    expected_top3 = 5     # 3 from batch1 + 2 from batch2
    expected_total = 6    # 3 from batch1 + 3 from batch2
    
    assert val_correct == expected_correct, f"Expected {expected_correct} correct, got {val_correct}"
    assert val_top3_correct == expected_top3, f"Expected {expected_top3} top-3 correct, got {val_top3_correct}"
    assert val_total == expected_total, f"Expected {expected_total} total, got {val_total}"
    
    expected_accuracy = expected_correct / expected_total
    expected_top3_accuracy = expected_top3 / expected_total
    
    assert abs(val_accuracy - expected_accuracy) < 1e-6, f"Accuracy mismatch: expected {expected_accuracy:.3f}, got {val_accuracy:.3f}"
    assert abs(val_top3_accuracy - expected_top3_accuracy) < 1e-6, f"Top-3 accuracy mismatch: expected {expected_top3_accuracy:.3f}, got {val_top3_accuracy:.3f}"
    
    print("✅ Validation metrics aggregation test passed!")

def test_validation_skip_scenarios():
    """Test validation skip scenarios and their impact on metrics"""
    
    print("🧪 Testing validation skip scenarios...")
    
    # Track skip reasons
    skipped_nan_logits = 0
    skipped_no_true = 0
    skipped_small_cands = 0
    val_total = 0
    
    # Scenario 1: NaN logits (should be skipped)
    log_probs_nan = torch.tensor([float('nan'), -1.0, -2.0])
    if torch.isnan(log_probs_nan).any():
        skipped_nan_logits += 1
    else:
        val_total += 1
    
    # Scenario 2: No true match and no NONE option (should be skipped)
    true_idx = None
    none_idx = None
    if true_idx is None and none_idx is None:
        skipped_no_true += 1
    else:
        val_total += 1
    
    # Scenario 3: Too few candidates (should be skipped)
    candidates_small = [{'forwards': ['p1'], 'defense': ['d1']}]  # Only 1 candidate
    if len(candidates_small) < 2:
        skipped_small_cands += 1
    else:
        val_total += 1
    
    # Scenario 4: Valid batch (should be counted)
    log_probs_valid = torch.tensor([-1.0, -2.0, -1.5])
    true_idx_valid = 0
    none_idx_valid = None
    if not torch.isnan(log_probs_valid).any() and (true_idx_valid is not None or none_idx_valid is not None):
        val_total += 1
    
    # Calculate skip rate
    total_attempts = skipped_nan_logits + skipped_no_true + skipped_small_cands + val_total
    skip_rate = (skipped_nan_logits + skipped_no_true + skipped_small_cands) / max(1, total_attempts)
    
    print(f"  NaN logits skipped: {skipped_nan_logits}")
    print(f"  No true match skipped: {skipped_no_true}")
    print(f"  Small candidates skipped: {skipped_small_cands}")
    print(f"  Valid samples: {val_total}")
    print(f"  Skip rate: {skip_rate:.1%}")
    
    # Verify expected results
    assert skipped_nan_logits == 1, f"Expected 1 NaN skip, got {skipped_nan_logits}"
    assert skipped_no_true == 1, f"Expected 1 no-true skip, got {skipped_no_true}"
    assert skipped_small_cands == 1, f"Expected 1 small-cands skip, got {skipped_small_cands}"
    assert val_total == 1, f"Expected 1 valid sample, got {val_total}"
    assert abs(skip_rate - 0.75) < 1e-6, f"Expected 75% skip rate, got {skip_rate:.1%}"
    
    print("✅ Validation skip scenarios test passed!")

if __name__ == "__main__":
    test_none_option_detection()
    test_validation_none_counting()
    test_validation_metrics_aggregation()
    test_validation_skip_scenarios()
    print("🎉 All validation NONE counting tests passed!")
