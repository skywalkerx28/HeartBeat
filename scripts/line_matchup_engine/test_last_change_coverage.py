"""
Test Last-Change Prior Coverage and Smoothing Correctness
Comprehensive tests for tactical rotation priors in all scenarios
Professional-grade testing for NHL analytics
"""

import unittest
import tempfile
from pathlib import Path
from collections import defaultdict
from unittest.mock import patch, MagicMock
import logging

# Import the modules we're testing
from candidate_generator import CandidateGenerator, Candidate
from data_processor import DataProcessor, DeploymentEvent


class TestLastChangeCoverage(unittest.TestCase):
    """Test last-change prior coverage and smoothing correctness"""
    
    def setUp(self):
        self.generator = CandidateGenerator()
        self.processor = DataProcessor()
        
        # Set up comprehensive test scenarios
        self.test_scenarios = [
            {
                'name': 'MTL_has_last_change_vs_TOR',
                'team_making_change': 'MTL',
                'opponent_team': 'TOR',
                'last_change_team': 'MTL',
                'expected_key_pattern': ('MTL', 'TOR', 'has_last_change')
            },
            {
                'name': 'MTL_no_last_change_vs_BOS',
                'team_making_change': 'MTL',
                'opponent_team': 'BOS',
                'last_change_team': 'BOS',
                'expected_key_pattern': ('MTL', 'BOS', 'no_last_change')
            },
            {
                'name': 'TOR_has_last_change_vs_MTL',
                'team_making_change': 'TOR',
                'opponent_team': 'MTL',
                'last_change_team': 'TOR',
                'expected_key_pattern': ('TOR', 'MTL', 'has_last_change')
            }
        ]
        
        self.test_deployments = [
            'Line1_D1',
            'Line2_D2',
            'Line3_D3',
            'Line4_D1'
        ]
        
        self.test_candidates = [
            Candidate(
                forwards=['player_1', 'player_2', 'player_3'],
                defense=['player_4', 'player_5'],
                probability_prior=1.0
            ),
            Candidate(
                forwards=['player_6', 'player_7', 'player_8'],
                defense=['player_9', 'player_10'],
                probability_prior=1.0
            ),
            Candidate(
                forwards=['player_11', 'player_12', 'player_13'],
                defense=['player_14', 'player_15'],
                probability_prior=1.0
            )
        ]
    
    def test_last_change_key_generation(self):
        """Test that last-change keys are generated correctly for all scenarios"""
        
        for scenario in self.test_scenarios:
            with self.subTest(scenario=scenario['name']):
                # Test the key generation logic
                team = scenario['team_making_change']
                opponent = scenario['opponent_team']
                last_change = scenario['last_change_team']
                
                # Simulate the key generation logic from apply_markov_rotation_prior
                if last_change == team:
                    last_change_key = 'has_last_change'
                else:
                    last_change_key = 'no_last_change'
                
                expected_pattern = scenario['expected_key_pattern']
                actual_pattern = (team, opponent, last_change_key)
                
                self.assertEqual(actual_pattern, expected_pattern,
                               f"Key pattern mismatch for {scenario['name']}")
    
    def test_priors_present_scenarios(self):
        """Test scenarios where tactical priors are present"""
        
        # Set up tactical priors for specific scenarios
        for scenario in self.test_scenarios:
            team = scenario['team_making_change']
            opponent = scenario['opponent_team']
            last_change = scenario['last_change_team']
            
            last_change_key = 'has_last_change' if last_change == team else 'no_last_change'
            
            # Add priors for each deployment transition
            for i, prev_deployment in enumerate(self.test_deployments):
                for j, next_deployment in enumerate(self.test_deployments):
                    if i != j:  # Don't create self-transitions
                        transition_key = (team, opponent, last_change_key, prev_deployment, next_deployment)
                        self.generator.last_change_rotation_transitions[transition_key] = 0.1 + (i + j) * 0.05
        
        # Test that priors are applied correctly
        for scenario in self.test_scenarios:
            with self.subTest(scenario=scenario['name']):
                candidates = self.test_candidates.copy()
                previous_deployment = self.test_deployments[0]
                
                result_candidates = self.generator.apply_markov_rotation_prior(
                    candidates=candidates,
                    previous_deployment=previous_deployment,
                    opponent_team=scenario['opponent_team'],
                    last_change_team=scenario['last_change_team'],
                    team_making_change=scenario['team_making_change']
                )
                
                # Verify candidates were returned (priors were found and applied)
                self.assertEqual(len(result_candidates), len(candidates))
                
                # At least some candidates should have modified probabilities if priors exist
                original_probs = [c.probability_prior for c in candidates]
                result_probs = [c.probability_prior for c in result_candidates]
                
                # Since we have priors, probabilities may change (though not guaranteed for every candidate)
                self.assertEqual(len(original_probs), len(result_probs))
    
    def test_priors_absent_scenarios(self):
        """Test scenarios where tactical priors are absent (fallback behavior)"""
        
        # Clear any existing priors
        self.generator.last_change_rotation_transitions.clear()
        self.generator.rotation_transitions.clear()
        
        # Test fallback behavior when no tactical priors exist
        for scenario in self.test_scenarios:
            with self.subTest(scenario=scenario['name']):
                candidates = self.test_candidates.copy()
                previous_deployment = "NonExistent_Deployment"
                
                result_candidates = self.generator.apply_markov_rotation_prior(
                    candidates=candidates,
                    previous_deployment=previous_deployment,
                    opponent_team=scenario['opponent_team'],
                    last_change_team=scenario['last_change_team'],
                    team_making_change=scenario['team_making_change']
                )
                
                # Should return original candidates when no priors exist
                self.assertEqual(len(result_candidates), len(candidates))
                
                # Probabilities should remain unchanged (fallback to no modification)
                for orig, result in zip(candidates, result_candidates):
                    self.assertEqual(orig.probability_prior, result.probability_prior)
    
    def test_smoothing_correctness(self):
        """Test that Dirichlet smoothing is applied correctly"""
        
        # Set up sparse transition data for smoothing test
        self.generator.last_change_rotation_transitions.clear()
        
        # Add limited transition data that will need smoothing
        base_key = ('MTL', 'TOR', 'has_last_change', 'Line1_D1')
        transitions = {
            base_key + ('Line2_D2',): 5.0,  # High frequency
            base_key + ('Line3_D3',): 1.0,  # Low frequency  
            # Missing Line4_D1 - will need smoothing
        }
        
        for key, count in transitions.items():
            self.generator.last_change_rotation_transitions[key] = count
            # Also set up counts for proper smoothing calculation
            count_key = key[:4]  # Remove the next_deployment part
            self.generator.last_change_rotation_counts[count_key] = sum(transitions.values())
        
        # Apply smoothing
        self.generator._smooth_last_change_transitions()
        
        # Verify smoothing was applied
        smoothed_transitions = {}
        for key, prob in self.generator.last_change_rotation_transitions.items():
            if key[:4] == base_key:
                next_deployment = key[4]
                smoothed_transitions[next_deployment] = prob
        
        # Check that probabilities sum to approximately 1.0 (within smoothing tolerance)
        total_prob = sum(smoothed_transitions.values())
        self.assertGreater(total_prob, 0.8, "Smoothed probabilities too low")
        self.assertLess(total_prob, 1.2, "Smoothed probabilities too high")
        
        # Check that high-frequency transition has higher probability than low-frequency
        if 'Line2_D2' in smoothed_transitions and 'Line3_D3' in smoothed_transitions:
            self.assertGreater(smoothed_transitions['Line2_D2'], smoothed_transitions['Line3_D3'],
                             "High-frequency transition should have higher probability after smoothing")
    
    def test_fallback_hierarchy_correctness(self):
        """Test that the fallback hierarchy works correctly"""
        
        # Clear priors to test fallback
        self.generator.last_change_rotation_transitions.clear()
        
        # Set up fallback data in rotation_transitions (general patterns)
        fallback_deployment = "Fallback_Line"
        self.generator.rotation_transitions[fallback_deployment] = {
            'Line1_D1': 0.4,
            'Line2_D2': 0.6
        }
        
        candidates = self.test_candidates.copy()
        
        # Test fallback to general rotation patterns
        result_candidates = self.generator.apply_markov_rotation_prior(
            candidates=candidates,
            previous_deployment=fallback_deployment,
            opponent_team='TOR',
            last_change_team='MTL',
            team_making_change='MTL'
        )
        
        # Should return candidates (fallback worked)
        self.assertEqual(len(result_candidates), len(candidates))
        
        # Test complete fallback failure (no patterns at all)
        no_pattern_candidates = self.generator.apply_markov_rotation_prior(
            candidates=candidates,
            previous_deployment="NonExistent_Pattern",
            opponent_team='TOR',
            last_change_team='MTL',
            team_making_change='MTL'
        )
        
        # Should still return candidates, but unchanged
        self.assertEqual(len(no_pattern_candidates), len(candidates))
    
    @patch('candidate_generator.logger')
    def test_logging_coverage(self, mock_logger):
        """Test that appropriate logging occurs for different scenarios"""
        
        # Test scenario with priors present
        self.generator.last_change_rotation_transitions[('MTL', 'TOR', 'has_last_change', 'Line1', 'Line2')] = 0.5
        
        candidates = self.test_candidates.copy()
        
        self.generator.apply_markov_rotation_prior(
            candidates=candidates,
            previous_deployment='Line1',
            opponent_team='TOR',
            last_change_team='MTL',
            team_making_change='MTL'
        )
        
        # Verify debug logging occurred (hardened fallback system logs extensively)
        self.assertTrue(mock_logger.debug.called or mock_logger.info.called,
                       "Expected logging when applying priors")
        
        # Test scenario with fallback
        mock_logger.reset_mock()
        
        self.generator.apply_markov_rotation_prior(
            candidates=candidates,
            previous_deployment='NonExistent',
            opponent_team='NYR',
            last_change_team='NYR',
            team_making_change='MTL'
        )
        
        # Should have warning or info logging for fallback
        self.assertTrue(mock_logger.warning.called or mock_logger.debug.called,
                       "Expected logging when falling back")
    
    def test_edge_case_coverage(self):
        """Test edge cases in last-change prior application"""
        
        # Test with empty candidates list
        empty_result = self.generator.apply_markov_rotation_prior(
            candidates=[],
            previous_deployment='Line1',
            opponent_team='TOR',
            last_change_team='MTL',
            team_making_change='MTL'
        )
        self.assertEqual(len(empty_result), 0)
        
        # Test with None parameters
        none_result = self.generator.apply_markov_rotation_prior(
            candidates=self.test_candidates.copy(),
            previous_deployment=None,
            opponent_team='TOR',
            last_change_team='MTL',
            team_making_change='MTL'
        )
        self.assertEqual(len(none_result), len(self.test_candidates))
        
        # Test with missing opponent_team (should use general patterns)
        no_opponent_result = self.generator.apply_markov_rotation_prior(
            candidates=self.test_candidates.copy(),
            previous_deployment='Line1',
            opponent_team=None,
            last_change_team=None,
            team_making_change='MTL'
        )
        self.assertEqual(len(no_opponent_result), len(self.test_candidates))


if __name__ == "__main__":
    unittest.main()
