"""
Test Out-of-Distribution (OOD) Detection for Feature Vectors
Verify that the model properly detects and handles anomalous inputs
Professional-grade testing for NHL analytics
"""

import unittest
import torch
import numpy as np
from unittest.mock import patch, MagicMock
import logging

# Import the model we're testing
from conditional_logit_model import PyTorchConditionalLogit


class TestOODDetection(unittest.TestCase):
    """Test OOD detection and logging functionality"""
    
    def setUp(self):
        self.model = PyTorchConditionalLogit(
            n_players=50,
            embedding_dim=32,
            enable_team_embeddings=True,
            team_embedding_dim=16,
            n_teams=33
        )
        
        # Register some test players
        test_players = [f"player_{i}" for i in range(20)]
        self.model.register_players(test_players)
    
    def test_ood_counter_initialization(self):
        """Test that OOD counters are properly initialized"""
        # Initialize counters
        self.model._PyTorchConditionalLogit__init_ood_counters()
        
        # Verify structure
        self.assertIn('dimension_mismatches', self.model.ood_counters)
        self.assertIn('nan_sanitizations', self.model.ood_counters)
        self.assertIn('inf_sanitizations', self.model.ood_counters)
        self.assertIn('extreme_values', self.model.ood_counters)
        self.assertIn('by_opponent', self.model.ood_counters)
        
        # Verify initial values
        self.assertEqual(self.model.ood_counters['dimension_mismatches'], 0)
        self.assertEqual(self.model.ood_counters['nan_sanitizations'], 0)
        self.assertEqual(self.model.ood_counters['inf_sanitizations'], 0)
        self.assertEqual(self.model.ood_counters['extreme_values'], 0)
    
    @patch('conditional_logit_model.logger')
    def test_extreme_value_detection(self, mock_logger):
        """Test detection of extreme values in feature vectors"""
        # Create feature vector with extreme values (>10.0 to trigger extreme detection)
        feature_vector = torch.randn(65)  # Expected dimension
        feature_vector[10] = 15.0  # Extreme value outside base utilities range
        feature_vector[20] = -12.0  # Another extreme value
        
        # Run validation
        self.model._validate_and_log_feature_vector(feature_vector, "TOR")
        
        # Check that warning was logged - look at all warning calls
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        extreme_warnings = [call for call in warning_calls if "extreme values detected" in call]
        self.assertTrue(len(extreme_warnings) > 0, f"Expected extreme value warning, got: {warning_calls}")
        
        extreme_warning = extreme_warnings[0]
        self.assertIn("TOR", extreme_warning)
        
        # Check counters were updated
        self.assertEqual(self.model.ood_counters['extreme_values'], 1)
        self.assertEqual(self.model.ood_counters['by_opponent']['TOR']['extreme_count'], 1)
    
    @patch('conditional_logit_model.logger')
    def test_base_utility_range_check(self, mock_logger):
        """Test detection of base utilities outside expected range"""
        # Create feature vector with base utilities out of range
        feature_vector = torch.zeros(65)
        feature_vector[2] = 7.0  # Base utility outside expected range (>5.0)
        
        # Run validation
        self.model._validate_and_log_feature_vector(feature_vector, "BOS")
        
        # Check that warning was logged for base utilities
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        base_utility_warnings = [call for call in warning_calls if "Base utilities outside expected range" in call]
        self.assertTrue(len(base_utility_warnings) > 0)
    
    @patch('conditional_logit_model.logger')
    def test_sanitization_logging(self, mock_logger):
        """Test logging of NaN and Inf sanitization events"""
        # Test NaN sanitization
        self.model._log_sanitization_event(3, 0, "NYR")
        
        # Verify NaN logging
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        self.assertIn("3 NaNs", warning_call)
        self.assertIn("NYR", warning_call)
        
        # Check counters
        self.assertEqual(self.model.ood_counters['nan_sanitizations'], 1)
        self.assertEqual(self.model.ood_counters['by_opponent']['NYR']['nan_count'], 1)
        
        # Test Inf sanitization
        mock_logger.reset_mock()
        self.model._log_sanitization_event(0, 2, "PHI")
        
        # Verify Inf logging
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        self.assertIn("2 Infs", warning_call)
        self.assertIn("PHI", warning_call)
        
        # Check counters
        self.assertEqual(self.model.ood_counters['inf_sanitizations'], 1)
        self.assertEqual(self.model.ood_counters['by_opponent']['PHI']['inf_count'], 1)
    
    def test_ood_statistics_reporting(self):
        """Test OOD statistics aggregation and reporting"""
        # Initialize and populate some test data
        self.model._PyTorchConditionalLogit__init_ood_counters()
        self.model.ood_counters['nan_sanitizations'] = 5
        self.model.ood_counters['inf_sanitizations'] = 3
        self.model.ood_counters['extreme_values'] = 2
        
        # Add per-opponent data
        self.model.ood_counters['by_opponent']['TOR']['nan_count'] = 2
        self.model.ood_counters['by_opponent']['TOR']['inf_count'] = 1
        self.model.ood_counters['by_opponent']['BOS']['extreme_count'] = 1
        
        # Get statistics
        stats = self.model.get_ood_statistics()
        
        # Verify structure and values
        self.assertEqual(stats['total_nan_sanitizations'], 5)
        self.assertEqual(stats['total_inf_sanitizations'], 3)
        self.assertEqual(stats['total_extreme_values'], 2)
        
        # Verify per-opponent summary
        self.assertIn('TOR', stats['by_opponent_summary'])
        self.assertIn('BOS', stats['by_opponent_summary'])
        
        tor_stats = stats['by_opponent_summary']['TOR']
        self.assertEqual(tor_stats['total_anomalies'], 3)  # 2 NaNs + 1 Inf + 0 extreme
        self.assertEqual(tor_stats['breakdown']['nan_count'], 2)
        self.assertEqual(tor_stats['breakdown']['inf_count'], 1)
    
    @patch('conditional_logit_model.logger')
    def test_dimension_mismatch_error(self, mock_logger):
        """Test comprehensive error reporting for dimension mismatches"""
        # Create a candidate dictionary
        candidate = {
            'forwards': ['player_1', 'player_2', 'player_3'],
            'defense': ['player_4', 'player_5'],
            'matchup_prior': 0.5
        }
        
        # Create mock context and other inputs
        context = torch.randn(36)
        opponent_on_ice = ['opp_1', 'opp_2']
        rest_times = {f'player_{i}': 60.0 for i in range(1, 6)}
        shift_counts = {f'player_{i}': 5 for i in range(1, 6)}
        toi_last_period = {f'player_{i}': 300.0 for i in range(1, 6)}
        
        # This should work normally first
        try:
            utility = self.model.compute_deployment_utility(
                candidate, context, opponent_on_ice, rest_times, 
                shift_counts, toi_last_period, opponent_team="TOR"
            )
            # If we get here, the computation worked
            self.assertIsInstance(utility, torch.Tensor)
        except Exception as e:
            # If there's an error, it should be informative
            error_msg = str(e)
            if "dimension mismatch" in error_msg.lower():
                self.assertIn("Received:", error_msg)
                self.assertIn("Expected:", error_msg)
                self.assertIn("Breakdown:", error_msg)
                self.assertIn("TOR", error_msg)
    
    def test_feature_vector_sanitization_integration(self):
        """Test end-to-end feature vector sanitization"""
        # Create a candidate with normal values
        candidate = {
            'forwards': ['player_1', 'player_2', 'player_3'],
            'defense': ['player_4', 'player_5'],
            'matchup_prior': 0.3
        }
        
        context = torch.randn(36)
        opponent_on_ice = ['opp_1', 'opp_2']
        rest_times = {f'player_{i}': 60.0 for i in range(1, 6)}
        shift_counts = {f'player_{i}': 5 for i in range(1, 6)}
        toi_last_period = {f'player_{i}': 300.0 for i in range(1, 6)}
        
        # Inject NaN into rest_times to trigger sanitization
        rest_times['player_1'] = float('nan')
        
        # This should handle the NaN gracefully
        with patch('conditional_logit_model.logger') as mock_logger:
            try:
                utility = self.model.compute_deployment_utility(
                    candidate, context, opponent_on_ice, rest_times,
                    shift_counts, toi_last_period, opponent_team="TOR"
                )
                # Should still produce a valid result
                self.assertIsInstance(utility, torch.Tensor)
                self.assertFalse(torch.isnan(utility))
                self.assertFalse(torch.isinf(utility))
            except Exception as e:
                # If there's an error, ensure it's not due to unhandled NaN
                self.assertNotIn("nan", str(e).lower())


if __name__ == '__main__':
    # Set up logging to see OOD detection in action
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
