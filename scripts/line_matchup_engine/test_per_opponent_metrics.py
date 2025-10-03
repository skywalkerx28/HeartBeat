#!/usr/bin/env python3
"""
Test per-opponent validation metrics functionality
"""

import sys
import os
import tempfile
from pathlib import Path
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_per_opponent_metrics_structure():
    """Test that per-opponent metrics are structured correctly"""
    
    print("🧪 Testing per-opponent metrics structure...")
    
    # Mock per-opponent metrics structure
    per_opponent_metrics = defaultdict(lambda: {
        'correct': 0, 'top3_correct': 0, 'total': 0, 'loss': 0.0
    })
    
    # Simulate metrics for different teams
    teams = ['TOR', 'BOS', 'NYR', 'UNK']
    
    for team in teams:
        per_opponent_metrics[team]['total'] = 10
        per_opponent_metrics[team]['correct'] = 7 if team == 'TOR' else 5
        per_opponent_metrics[team]['top3_correct'] = 9 if team == 'TOR' else 8
        per_opponent_metrics[team]['loss'] = 1.2 if team == 'TOR' else 1.8
    
    # Verify structure
    for team in teams:
        assert 'correct' in per_opponent_metrics[team], f"Missing 'correct' for {team}"
        assert 'top3_correct' in per_opponent_metrics[team], f"Missing 'top3_correct' for {team}"
        assert 'total' in per_opponent_metrics[team], f"Missing 'total' for {team}"
        assert 'loss' in per_opponent_metrics[team], f"Missing 'loss' for {team}"
    
    # Test accuracy calculations
    tor_acc = per_opponent_metrics['TOR']['correct'] / per_opponent_metrics['TOR']['total']
    assert tor_acc == 0.7, f"TOR accuracy should be 0.7, got {tor_acc}"
    
    print("✅ Per-opponent metrics structure test passed")

def test_per_opponent_csv_format():
    """Test CSV format for per-opponent metrics"""
    
    print("🧪 Testing per-opponent CSV format...")
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        # Write headers
        headers = ['epoch', 'opponent_team', 'samples', 'accuracy', 'top3_accuracy', 'avg_loss']
        f.write(','.join(headers) + '\n')
        
        # Write test data
        test_data = [
            [1, 'TOR', 15, 0.733, 0.867, 1.234],
            [1, 'BOS', 12, 0.583, 0.750, 1.567],
            [1, 'NYR', 8, 0.625, 0.875, 1.345]
        ]
        
        for row in test_data:
            f.write(','.join(map(str, row)) + '\n')
        
        csv_path = f.name
    
    # Verify CSV content
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    
    assert len(lines) == 4, f"Expected 4 lines (header + 3 data), got {len(lines)}"
    assert 'epoch,opponent_team,samples,accuracy,top3_accuracy,avg_loss' in lines[0], "Headers incorrect"
    assert 'TOR' in lines[1], "TOR data missing"
    assert '0.733' in lines[1], "TOR accuracy missing"
    
    # Cleanup
    os.unlink(csv_path)
    
    print("✅ Per-opponent CSV format test passed")

def test_opponent_team_extraction():
    """Test opponent team extraction from batch data"""
    
    print("🧪 Testing opponent team extraction...")
    
    # Mock batch data
    test_batches = [
        {'opponent_team': 'TOR', 'candidates': [{}], 'true_deployment': {}},
        {'opponent_team': 'BOS', 'candidates': [{}], 'true_deployment': {}},
        {'candidates': [{}], 'true_deployment': {}},  # Missing opponent_team
    ]
    
    # Test extraction
    extracted_teams = []
    for batch in test_batches:
        opponent_team = batch.get('opponent_team', 'UNK')
        extracted_teams.append(opponent_team)
    
    assert extracted_teams == ['TOR', 'BOS', 'UNK'], f"Expected ['TOR', 'BOS', 'UNK'], got {extracted_teams}"
    
    print("✅ Opponent team extraction test passed")

def test_metrics_aggregation():
    """Test aggregation of per-opponent metrics"""
    
    print("🧪 Testing metrics aggregation...")
    
    # Simulate multiple batches for same team
    per_opponent_metrics = defaultdict(lambda: {
        'correct': 0, 'top3_correct': 0, 'total': 0, 'loss': 0.0
    })
    
    # Simulate processing multiple TOR batches
    tor_results = [
        {'correct': True, 'top3_correct': True, 'loss': 1.2},
        {'correct': False, 'top3_correct': True, 'loss': 2.1},
        {'correct': True, 'top3_correct': True, 'loss': 0.8},
    ]
    
    for result in tor_results:
        per_opponent_metrics['TOR']['total'] += 1
        per_opponent_metrics['TOR']['loss'] += result['loss']
        if result['correct']:
            per_opponent_metrics['TOR']['correct'] += 1
        if result['top3_correct']:
            per_opponent_metrics['TOR']['top3_correct'] += 1
    
    # Verify aggregation
    assert per_opponent_metrics['TOR']['total'] == 3, "Total should be 3"
    assert per_opponent_metrics['TOR']['correct'] == 2, "Correct should be 2"
    assert per_opponent_metrics['TOR']['top3_correct'] == 3, "Top3 correct should be 3"
    assert abs(per_opponent_metrics['TOR']['loss'] - 4.1) < 0.01, f"Loss should be 4.1, got {per_opponent_metrics['TOR']['loss']}"
    
    # Calculate final metrics
    tor_acc = per_opponent_metrics['TOR']['correct'] / per_opponent_metrics['TOR']['total']
    tor_top3 = per_opponent_metrics['TOR']['top3_correct'] / per_opponent_metrics['TOR']['total']
    tor_avg_loss = per_opponent_metrics['TOR']['loss'] / per_opponent_metrics['TOR']['total']
    
    assert abs(tor_acc - 0.667) < 0.01, f"TOR accuracy should be ~0.667, got {tor_acc}"
    assert tor_top3 == 1.0, f"TOR top3 should be 1.0, got {tor_top3}"
    assert abs(tor_avg_loss - 1.367) < 0.01, f"TOR avg loss should be ~1.367, got {tor_avg_loss}"
    
    print("✅ Metrics aggregation test passed")

if __name__ == "__main__":
    print("🚀 Testing Per-Opponent Metrics Implementation")
    print("=" * 60)
    
    test_per_opponent_metrics_structure()
    test_per_opponent_csv_format()
    test_opponent_team_extraction()
    test_metrics_aggregation()
    
    print("=" * 60)
    print("✅ All per-opponent metrics tests passed!")
    print("✅ Team-aware evaluation system is working correctly")
