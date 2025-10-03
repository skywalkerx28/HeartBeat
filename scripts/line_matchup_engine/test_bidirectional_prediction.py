"""
Test Bidirectional Prediction System
Comprehensive tests for both-team prediction with proper last-change context
Professional-grade testing for NHL analytics
"""

import unittest
import tempfile
from pathlib import Path
from collections import defaultdict
from unittest.mock import Mock, patch

# Import the modules we're testing
from live_predictor import LiveLinePredictor, GameState
from candidate_generator import CandidateGenerator, Candidate

class TestBidirectionalPrediction(unittest.TestCase):
    """Test bidirectional prediction with proper last-change awareness"""
    
    def setUp(self):
        self.predictor = LiveLinePredictor()
        
        # Set up mock patterns for testing
        self.predictor.candidate_generator.player_matchup_counts = defaultdict(float)
        self.predictor.candidate_generator.last_change_rotation_transitions = defaultdict(float)
        
        # Add some test matchup data
        test_matchups = [
            (('mtl_player_1', 'tor_player_1'), 2.5),
            (('mtl_player_2', 'tor_player_2'), 1.8),
            (('mtl_player_3', 'tor_player_3'), 3.2)
        ]
        
        for (mtl_p, opp_p), weight in test_matchups:
            self.predictor.candidate_generator.player_matchup_counts[(mtl_p, opp_p)] = weight
        
        # Add rotation patterns
        rotation_patterns = [
            (('MTL', 'TOR', 'has_last_change', 'Line1_D1', 'Line2_D2'), 0.35),
            (('MTL', 'TOR', 'no_last_change', 'Line1_D1', 'Line3_D3'), 0.28),
            (('TOR', 'MTL', 'has_last_change', 'TOR_Line1_D1', 'TOR_Line2_D2'), 0.42),
            (('TOR', 'MTL', 'no_last_change', 'TOR_Line1_D1', 'TOR_Line3_D3'), 0.31)
        ]
        
        for pattern, prob in rotation_patterns:
            self.predictor.candidate_generator.last_change_rotation_transitions[pattern] = prob
    
    def test_predict_deployment_for_mtl(self):
        """Test predicting MTL deployment with proper context"""
        game_state = GameState(
            game_id="test_mtl_prediction",
            period=2,
            period_time=600.0,
            home_team="MTL",
            away_team="TOR",
            home_score=1,
            away_score=1,
            strength_state="5v5",
            mtl_forwards_available=["mtl_player_1", "mtl_player_2", "mtl_player_3", "mtl_player_4"],
            mtl_defense_available=["mtl_def_1", "mtl_def_2"],
            opp_forwards_on_ice=["tor_player_1", "tor_player_2", "tor_player_3"],
            opp_defense_on_ice=["tor_def_1", "tor_def_2"],
            player_rest_times={
                "mtl_player_1": 45.0, "mtl_player_2": 60.0, "mtl_player_3": 30.0,
                "mtl_def_1": 90.0, "mtl_def_2": 75.0
            }
        )
        
        # Test MTL prediction (MTL has last change as home team)
        result = self.predictor.predict_deployment_for_team(game_state, 'MTL', 'TOR')
        
        # Verify structure
        self.assertIn('candidates', result)
        self.assertIn('team', result)
        self.assertIn('opponent_team', result)
        self.assertIn('last_change_team', result)
        self.assertIn('has_last_change', result)
        self.assertIn('tactical_context', result)
        
        # Verify context is correct
        self.assertEqual(result['team'], 'MTL')
        self.assertEqual(result['opponent_team'], 'TOR')
        self.assertEqual(result['last_change_team'], 'MTL')  # Home team has last change
        self.assertTrue(result['has_last_change'])  # MTL is home team
        self.assertEqual(result['tactical_context'], 'has_last_change')
    
    def test_predict_deployment_for_opponent(self):
        """Test predicting opponent deployment with proper context"""
        game_state = GameState(
            game_id="test_opponent_prediction",
            period=2,
            period_time=600.0,
            home_team="TOR",  # TOR is home, so TOR has last change
            away_team="MTL",
            home_score=1,
            away_score=1,
            strength_state="5v5",
            opp_forwards_available=["tor_player_1", "tor_player_2", "tor_player_3", "tor_player_4"],
            opp_defense_available=["tor_def_1", "tor_def_2"],
            mtl_forwards_on_ice=["mtl_player_1", "mtl_player_2", "mtl_player_3"],
            mtl_defense_on_ice=["mtl_def_1", "mtl_def_2"],
            player_rest_times={
                "tor_player_1": 45.0, "tor_player_2": 60.0, "tor_player_3": 30.0,
                "tor_def_1": 90.0, "tor_def_2": 75.0
            }
        )
        
        # Test opponent prediction (TOR has last change as home team)
        result = self.predictor.predict_deployment_for_team(game_state, 'TOR', 'MTL')
        
        # Verify structure
        self.assertIn('candidates', result)
        self.assertIn('team', result)
        self.assertIn('opponent_team', result)
        self.assertIn('last_change_team', result)
        self.assertIn('has_last_change', result)
        self.assertIn('tactical_context', result)
        
        # Verify context is correct
        self.assertEqual(result['team'], 'TOR')
        self.assertEqual(result['opponent_team'], 'MTL')
        self.assertEqual(result['last_change_team'], 'TOR')  # Home team has last change
        self.assertTrue(result['has_last_change'])  # TOR is home team
        self.assertEqual(result['tactical_context'], 'has_last_change')
    
    def test_last_change_context_switching(self):
        """Test that last-change context switches correctly based on home team"""
        # Test 1: MTL at home (MTL has last change)
        game_state_mtl_home = GameState(
            game_id="test_mtl_home",
            period=2,
            period_time=600.0,
            home_team="MTL",
            away_team="BOS",
            home_score=1,
            away_score=1,
            strength_state="5v5",
            mtl_forwards_available=["mtl_f1", "mtl_f2", "mtl_f3"],
            mtl_defense_available=["mtl_d1", "mtl_d2"]
        )
        
        mtl_result = self.predictor.predict_deployment_for_team(game_state_mtl_home, 'MTL', 'BOS')
        self.assertTrue(mtl_result['has_last_change'])  # MTL has advantage
        
        bos_result = self.predictor.predict_deployment_for_team(game_state_mtl_home, 'BOS', 'MTL')
        self.assertFalse(bos_result['has_last_change'])  # BOS doesn't have advantage
        
        # Test 2: MTL away (opponent has last change)
        game_state_mtl_away = GameState(
            game_id="test_mtl_away",
            period=2,
            period_time=600.0,
            home_team="BOS",
            away_team="MTL",
            home_score=1,
            away_score=1,
            strength_state="5v5",
            mtl_forwards_available=["mtl_f1", "mtl_f2", "mtl_f3"],
            mtl_defense_available=["mtl_d1", "mtl_d2"]
        )
        
        mtl_result_away = self.predictor.predict_deployment_for_team(game_state_mtl_away, 'MTL', 'BOS')
        self.assertFalse(mtl_result_away['has_last_change'])  # MTL doesn't have advantage
        
        bos_result_away = self.predictor.predict_deployment_for_team(game_state_mtl_away, 'BOS', 'MTL')
        self.assertTrue(bos_result_away['has_last_change'])  # BOS has advantage
    
    def test_strategic_deployment_integration(self):
        """Test that strategic deployment uses the new bidirectional API"""
        game_state = GameState(
            game_id="test_strategic",
            period=3,
            period_time=300.0,
            home_team="MTL",
            away_team="NYR",
            home_score=2,
            away_score=1,
            strength_state="5v5",
            mtl_forwards_available=["mtl_f1", "mtl_f2", "mtl_f3", "mtl_f4"],
            mtl_defense_available=["mtl_d1", "mtl_d2"],
            opp_forwards_available=["nyr_f1", "nyr_f2", "nyr_f3", "nyr_f4"],
            opp_defense_available=["nyr_d1", "nyr_d2"]
        )
        
        # Test MTL has last change scenario
        result = self.predictor.predict_strategic_deployment(
            game_state, 'mtl_has_last_change', 'NYR'
        )
        
        # Verify structure
        self.assertIn('scenario', result)
        self.assertIn('strategic_advantage', result)
        self.assertIn('opponent_predictions', result)
        self.assertIn('mtl_optimal_responses', result)
        
        # Verify strategic advantage is correctly assigned
        self.assertEqual(result['strategic_advantage'], 'MTL')
        self.assertEqual(result['scenario'], 'mtl_has_last_change')
    
    def test_matchup_prior_integration(self):
        """Test that player-vs-player matchup priors are properly integrated"""
        game_state = GameState(
            game_id="test_matchup_priors",
            period=2,
            period_time=800.0,
            home_team="MTL",
            away_team="TOR",
            home_score=0,
            away_score=0,
            strength_state="5v5",
            mtl_forwards_available=["mtl_player_1", "mtl_player_2", "mtl_player_3"],
            mtl_defense_available=["mtl_def_1", "mtl_def_2"],
            opp_forwards_on_ice=["tor_player_1", "tor_player_2", "tor_player_3"],
            opp_defense_on_ice=["tor_def_1", "tor_def_2"]
        )
        
        result = self.predictor.predict_deployment_for_team(game_state, 'MTL', 'TOR')
        
        # Verify that candidates have matchup priors
        if result['candidates']:
            for candidate in result['candidates']:
                self.assertTrue(hasattr(candidate, 'matchup_prior'))
                # Should have non-zero matchup prior due to our test data
                matchup_prior = getattr(candidate, 'matchup_prior', 0.0)
                self.assertIsInstance(matchup_prior, (int, float))


if __name__ == '__main__':
    unittest.main()
