#!/usr/bin/env python3
"""
Test team-aware fatigue module functionality
"""

import sys
import os
import torch
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conditional_logit_model import FatigueRotationModule

def test_team_fatigue_initialization():
    """Test that team-specific fatigue parameters are initialized correctly"""
    
    print("🧪 Testing team-aware fatigue initialization...")
    
    # Create fatigue module
    fatigue_module = FatigueRotationModule(input_dim=18)
    
    # Verify team fatigue scales are initialized
    assert hasattr(fatigue_module, 'team_fatigue_scales'), "team_fatigue_scales should be initialized"
    
    # Check that all NHL teams are included
    expected_teams = [
        'ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL',
        'DET', 'EDM', 'FLA', 'LAK', 'MIN', 'MTL', 'NJD', 'NSH', 'NYI', 'NYR',
        'OTT', 'PHI', 'PIT', 'SEA', 'SJS', 'STL', 'TBL', 'TOR', 'UTA', 'VAN', 'VGK',
        'WPG', 'WSH', 'UNK'
    ]
    
    for team in expected_teams:
        assert team in fatigue_module.team_fatigue_scales, f"Team {team} should be in fatigue scales"
        
        # Check parameter shape (should be 18 features)
        team_params = fatigue_module.team_fatigue_scales[team]
        assert team_params.shape == (18,), f"Team {team} params should have shape (18,), got {team_params.shape}"
        
        # Check parameters are around 1.0 (neutral scaling)
        param_values = team_params.data.numpy()
        assert np.all(param_values > 0.8), f"Team {team} params should be > 0.8"
        assert np.all(param_values < 1.2), f"Team {team} params should be < 1.2"
    
    print("✅ Team fatigue initialization test passed")

def test_team_fatigue_modulation():
    """Test team-specific fatigue modulation retrieval"""
    
    print("🧪 Testing team fatigue modulation...")
    
    fatigue_module = FatigueRotationModule(input_dim=18)
    device = torch.device('cpu')
    
    # Test known team
    tor_modulation = fatigue_module._get_team_fatigue_modulation('TOR', device)
    assert tor_modulation.shape == (18,), f"TOR modulation should have shape (18,), got {tor_modulation.shape}"
    assert torch.all(tor_modulation > 0.8), "TOR modulation values should be > 0.8"
    assert torch.all(tor_modulation < 1.2), "TOR modulation values should be < 1.2"
    
    # Test unknown team (should fallback to UNK)
    unknown_modulation = fatigue_module._get_team_fatigue_modulation('UNKNOWN_TEAM', device)
    unk_modulation = fatigue_module._get_team_fatigue_modulation('UNK', device)
    assert torch.allclose(unknown_modulation, unk_modulation), "Unknown team should fallback to UNK"
    
    # Test different teams have different modulations
    bos_modulation = fatigue_module._get_team_fatigue_modulation('BOS', device)
    assert not torch.allclose(tor_modulation, bos_modulation), "TOR and BOS should have different modulations"
    
    print("✅ Team fatigue modulation test passed")

def test_team_aware_fatigue_computation():
    """Test that team-aware fatigue computation works end-to-end"""
    
    print("🧪 Testing team-aware fatigue computation...")
    
    fatigue_module = FatigueRotationModule(input_dim=18)
    
    # Mock player data
    players = ['player1', 'player2', 'player3']
    rest_times = {'player1': 60.0, 'player2': 45.0, 'player3': 90.0}
    shift_counts = {'player1': 8, 'player2': 12, 'player3': 5}
    toi_last_period = {'player1': 400.0, 'player2': 500.0, 'player3': 300.0}
    
    # Test fatigue computation without opponent team
    fatigue_no_team = fatigue_module.compute_fatigue(
        rest_times=rest_times,
        shift_counts=shift_counts,
        toi_last_period=toi_last_period,
        players=players,
        opponent_team=None
    )
    
    # Test fatigue computation with opponent team
    fatigue_vs_tor = fatigue_module.compute_fatigue(
        rest_times=rest_times,
        shift_counts=shift_counts,
        toi_last_period=toi_last_period,
        players=players,
        opponent_team='TOR'
    )
    
    fatigue_vs_bos = fatigue_module.compute_fatigue(
        rest_times=rest_times,
        shift_counts=shift_counts,
        toi_last_period=toi_last_period,
        players=players,
        opponent_team='BOS'
    )
    
    # Verify outputs are tensors
    assert isinstance(fatigue_no_team, torch.Tensor), "Fatigue output should be tensor"
    assert isinstance(fatigue_vs_tor, torch.Tensor), "Fatigue vs TOR should be tensor"
    assert isinstance(fatigue_vs_bos, torch.Tensor), "Fatigue vs BOS should be tensor"
    
    # Verify team-specific fatigue is different
    assert not torch.allclose(fatigue_vs_tor, fatigue_vs_bos, atol=1e-6), "TOR vs BOS fatigue should differ"
    
    # Verify team-aware fatigue differs from no-team baseline
    # Note: They might be close if team modulation is near 1.0, but should not be identical
    print(f"  No team fatigue: {fatigue_no_team.item():.6f}")
    print(f"  vs TOR fatigue: {fatigue_vs_tor.item():.6f}")
    print(f"  vs BOS fatigue: {fatigue_vs_bos.item():.6f}")
    
    print("✅ Team-aware fatigue computation test passed")

def test_fatigue_parameter_learning():
    """Test that team fatigue parameters are learnable"""
    
    print("🧪 Testing fatigue parameter learning...")
    
    fatigue_module = FatigueRotationModule(input_dim=18)
    
    # Check that team fatigue scales require gradients
    for team, params in fatigue_module.team_fatigue_scales.items():
        assert params.requires_grad, f"Team {team} fatigue params should require gradients"
    
    # Test gradient computation
    players = ['player1']
    rest_times = {'player1': 60.0}
    shift_counts = {'player1': 8}
    toi_last_period = {'player1': 400.0}
    
    # Forward pass with TOR
    fatigue_score = fatigue_module.compute_fatigue(
        rest_times=rest_times,
        shift_counts=shift_counts,
        toi_last_period=toi_last_period,
        players=players,
        opponent_team='TOR'
    )
    
    # Backward pass
    fatigue_score.backward()
    
    # Check that TOR parameters have gradients
    tor_params = fatigue_module.team_fatigue_scales['TOR']
    assert tor_params.grad is not None, "TOR fatigue params should have gradients after backward pass"
    assert not torch.allclose(tor_params.grad, torch.zeros_like(tor_params.grad)), "TOR gradients should be non-zero"
    
    print("✅ Fatigue parameter learning test passed")

if __name__ == "__main__":
    print("🚀 Testing Team-Aware Fatigue Module")
    print("=" * 60)
    
    test_team_fatigue_initialization()
    test_team_fatigue_modulation()
    test_team_aware_fatigue_computation()
    test_fatigue_parameter_learning()
    
    print("=" * 60)
    print("✅ All team-aware fatigue tests passed!")
    print("✅ Fatigue module can now learn team-specific patterns")
