"""
Test Hardened Fallback Policy for Rotation Priors
Verify that the multi-level fallback system works correctly and provides clear logging
Professional-grade testing for NHL analytics
"""

import unittest
import logging
from unittest.mock import patch, MagicMock
from collections import defaultdict

# Import the module we're testing
from candidate_generator import CandidateGenerator, Candidate


class TestFallbackPolicy(unittest.TestCase):
    """Test hardened fallback policy for rotation priors"""
    
    def setUp(self):
        self.generator = CandidateGenerator()
        
        # Set up some test data for fallback scenarios
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
            )
        ]
        
        self.prev_deployment = "player_1|player_2|player_3_player_4|player_5"
        self.next_deployment_1 = "player_1|player_2|player_3_player_4|player_5"
        self.next_deployment_2 = "player_6|player_7|player_8_player_9|player_10"
    
    def test_level_1_exact_tactical_context(self):
        """Test Level 1 fallback: exact tactical context"""
        # Set up exact tactical context
        context_key = ('MTL', 'TOR', 'has_last_change', self.prev_deployment)
        transition_key = ('MTL', 'TOR', 'has_last_change', self.prev_deployment, self.next_deployment_1)
        
        self.generator.last_change_rotation_transitions[transition_key] = 0.8
        
        # Test fallback
        result = self.generator._get_fallback_transition_probs(
            context_key, self.prev_deployment, 'TOR'
        )
        
        # Should find exact match
        self.assertIn(self.next_deployment_1, result)
        self.assertEqual(result[self.next_deployment_1], 0.8)
    
    @patch('candidate_generator.logger')
    def test_level_2_alternate_last_change(self, mock_logger):
        """Test Level 2 fallback: same opponent, different last_change status"""
        # Set up alternate last_change pattern
        context_key = ('MTL', 'TOR', 'has_last_change', self.prev_deployment)
        alternate_key = ('MTL', 'TOR', 'no_last_change', self.prev_deployment, self.next_deployment_1)
        
        self.generator.last_change_rotation_transitions[alternate_key] = 0.6
        
        # Test fallback (no exact match available)
        result = self.generator._get_fallback_transition_probs(
            context_key, self.prev_deployment, 'TOR'
        )
        
        # Should find alternate pattern with reduced confidence
        self.assertIn(self.next_deployment_1, result)
        self.assertEqual(result[self.next_deployment_1], 0.6 * 0.7)  # Reduced confidence
        
        # Should log the fallback
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        self.assertIn("Level 2", log_call)
        self.assertIn("no_last_change", log_call)
    
    @patch('candidate_generator.logger')
    def test_level_3_generalized_team_behavior(self, mock_logger):
        """Test Level 3 fallback: same team, different opponent"""
        # Set up patterns for different opponents
        context_key = ('MTL', 'TOR', 'has_last_change', self.prev_deployment)
        
        # Patterns vs BOS and NYR (not TOR)
        bos_key = ('MTL', 'BOS', 'has_last_change', self.prev_deployment, self.next_deployment_1)
        nyr_key = ('MTL', 'NYR', 'has_last_change', self.prev_deployment, self.next_deployment_1)
        
        self.generator.last_change_rotation_transitions[bos_key] = 0.8
        self.generator.last_change_rotation_transitions[nyr_key] = 0.6
        
        # Test fallback (no exact or alternate match)
        result = self.generator._get_fallback_transition_probs(
            context_key, self.prev_deployment, 'TOR'
        )
        
        # Should average patterns from other opponents
        expected_prob = (0.8 * 0.5 + 0.6 * 0.5) / ((0.8 * 0.5 + 0.6 * 0.5))  # Normalized
        self.assertIn(self.next_deployment_1, result)
        self.assertAlmostEqual(result[self.next_deployment_1], expected_prob, places=3)
        
        # Should log the fallback
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        self.assertIn("Level 3", log_call)
        self.assertIn("Generalized MTL behavior", log_call)
    
    @patch('candidate_generator.logger')
    def test_level_4_general_rotation_patterns(self, mock_logger):
        """Test Level 4 fallback: general rotation patterns"""
        # Set up general rotation patterns
        context_key = ('MTL', 'TOR', 'has_last_change', self.prev_deployment)
        
        self.generator.rotation_transitions[self.prev_deployment] = {
            self.next_deployment_1: 0.7,
            self.next_deployment_2: 0.3
        }
        
        # Test fallback (no tactical patterns available)
        result = self.generator._get_fallback_transition_probs(
            context_key, self.prev_deployment, 'TOR'
        )
        
        # Should use general patterns
        self.assertEqual(result[self.next_deployment_1], 0.7)
        self.assertEqual(result[self.next_deployment_2], 0.3)
        
        # Should log the fallback
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        self.assertIn("Level 4", log_call)
        self.assertIn("General rotation patterns", log_call)
    
    @patch('candidate_generator.logger')
    def test_level_5_no_patterns_available(self, mock_logger):
        """Test Level 5 fallback: no patterns available"""
        # No patterns set up
        context_key = ('MTL', 'TOR', 'has_last_change', self.prev_deployment)
        
        # Test fallback (no patterns available)
        result = self.generator._get_fallback_transition_probs(
            context_key, self.prev_deployment, 'TOR'
        )
        
        # Should return empty dict
        self.assertEqual(result, {})
        
        # Should log warning
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        self.assertIn("Level 5", warning_call)
        self.assertIn("no patterns available", warning_call)
    
    @patch('candidate_generator.logger')
    def test_prior_application_stats_logging(self, mock_logger):
        """Test detailed logging of prior application statistics"""
        # Set up transition probabilities
        transition_probs = {
            self.next_deployment_1: 0.8,
            "nonexistent_deployment": 0.2
        }
        
        # Apply stats logging
        self.generator._log_prior_application_stats(
            self.test_candidates, transition_probs, "test_context"
        )
        
        # Should log debug info about coverage and boosts
        mock_logger.debug.assert_called()
        debug_call = mock_logger.debug.call_args[0][0]
        self.assertIn("Prior stats test_context", debug_call)
        self.assertIn("coverage", debug_call)
        self.assertIn("avg_boost", debug_call)
    
    @patch('candidate_generator.logger')
    def test_prior_application_no_matches(self, mock_logger):
        """Test logging when no candidates match available patterns"""
        # Set up transition probabilities that don't match any candidates
        transition_probs = {
            "nonexistent_deployment_1": 0.5,
            "nonexistent_deployment_2": 0.5
        }
        
        # Apply stats logging
        self.generator._log_prior_application_stats(
            self.test_candidates, transition_probs, "test_context"
        )
        
        # Should log warning about no matches
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        self.assertIn("No candidates matched available patterns", warning_call)
    
    @patch('candidate_generator.logger')
    def test_integration_apply_markov_rotation_prior_with_fallback(self, mock_logger):
        """Test integration of fallback policy in apply_markov_rotation_prior"""
        # Set up Level 2 fallback scenario (alternate last_change)
        alternate_key = ('MTL', 'TOR', 'no_last_change', self.prev_deployment, self.next_deployment_1)
        self.generator.last_change_rotation_transitions[alternate_key] = 0.6
        
        # Apply rotation prior (should trigger Level 2 fallback)
        result_candidates = self.generator.apply_markov_rotation_prior(
            self.test_candidates.copy(),
            previous_deployment=self.prev_deployment,
            opponent_team='TOR',
            last_change_team='MTL',  # MTL has last change, but no pattern for this scenario
            team_making_change='MTL'
        )
        
        # Should have applied fallback and modified probabilities
        self.assertEqual(len(result_candidates), 2)
        
        # Check that fallback was logged
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        fallback_logs = [call for call in info_calls if "Level 2" in call]
        self.assertTrue(len(fallback_logs) > 0, "Expected Level 2 fallback to be logged")
    
    @patch('candidate_generator.logger')
    def test_no_patterns_warning_integration(self, mock_logger):
        """Test warning when no patterns are available at all"""
        # Apply rotation prior with no patterns available
        result_candidates = self.generator.apply_markov_rotation_prior(
            self.test_candidates.copy(),
            previous_deployment=self.prev_deployment,
            opponent_team='TOR',
            last_change_team='MTL',
            team_making_change='MTL'
        )
        
        # Should return unchanged candidates
        self.assertEqual(len(result_candidates), 2)
        for candidate in result_candidates:
            self.assertEqual(candidate.probability_prior, 1.0)  # Unchanged
        
        # Should log warning about no patterns
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        pattern_warnings = [call for call in warning_calls if "No rotation patterns available" in call]
        self.assertTrue(len(pattern_warnings) > 0, "Expected warning about missing patterns")


if __name__ == '__main__':
    # Set up logging to see fallback policy in action
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
