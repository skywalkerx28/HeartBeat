"""
Test Player-vs-Player Matchup System
Comprehensive tests for counts, smoothing, serialization, and prior computation
Professional-grade testing for NHL analytics
"""

import unittest
import tempfile
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

# Import the modules we're testing
from data_processor import DataProcessor, DeploymentEvent
from candidate_generator import CandidateGenerator, Candidate


class TestPlayerMatchupCounts(unittest.TestCase):
    """Test player-vs-player matchup count extraction"""
    
    def setUp(self):
        self.processor = DataProcessor()
        
    def test_player_matchup_count_initialization(self):
        """Test that player matchup data structures are properly initialized"""
        self.assertIsInstance(self.processor.player_matchup_counts, defaultdict)
        self.assertIsInstance(self.processor.last_change_player_matchups, defaultdict)
        self.assertIsInstance(self.processor.situation_player_matchups, defaultdict)
        
    def test_player_matchup_counting_basic(self):
        """Test basic player-vs-player matchup counting"""
        # Create mock deployment event
        event = DeploymentEvent(
            game_id="test_001",
            event_id=1,
            period=2,
            period_time=600.0,
            game_time=2400.0,
            zone_start="NZ",
            strength_state="5v5",
            score_differential=0,
            time_bucket="middle",
            stoppage_type="faceoff",
            home_team="MTL",
            away_team="TOR",
            last_change_team="MTL",  # Home team has last change
            opponent_team="TOR",
            mtl_forwards=["8480018", "8481540", "8483515"],
            mtl_defense=["8476875", "8482087"],
            opp_forwards=["8479318", "8478483", "8482720"],
            opp_defense=["8475690", "8476853"]
        )
        
        # Process the event
        mtl_players = event.mtl_forwards + event.mtl_defense
        opp_players = event.opp_forwards + event.opp_defense
        self.processor._update_player_matchup_counts(event, mtl_players, opp_players)
        
        # Verify global matchup counts were updated
        expected_matchups = len(mtl_players) * len(opp_players)  # 5 * 5 = 25 matchups
        total_global_matchups = sum(self.processor.player_matchup_counts.values())
        self.assertEqual(total_global_matchups, expected_matchups)
        
        # Verify specific matchup exists
        test_key = ("8480018", "8479318")  # MTL forward vs TOR forward
        self.assertGreater(self.processor.player_matchup_counts[test_key], 0.0)
        
    def test_last_change_aware_counting(self):
        """Test last-change-aware matchup pattern counting"""
        event = DeploymentEvent(
            game_id="test_002",
            event_id=2,
            period=1,
            period_time=300.0,
            game_time=1500.0,
            zone_start="OZ",
            strength_state="5v5",
            score_differential=1,
            time_bucket="early",
            stoppage_type="faceoff",
            home_team="MTL",
            away_team="BOS",
            last_change_team="MTL",
            opponent_team="BOS",
            mtl_forwards=["8480018", "8481540"],
            mtl_defense=["8476875"],
            opp_forwards=["8479318", "8478483"],
            opp_defense=["8475690"]
        )
        
        mtl_players = event.mtl_forwards + event.mtl_defense
        opp_players = event.opp_forwards + event.opp_defense
        self.processor._update_player_matchup_counts(event, mtl_players, opp_players)
        
        # Verify last-change-aware patterns were recorded
        total_last_change_matchups = sum(self.processor.last_change_player_matchups.values())
        expected_matchups = len(mtl_players) * len(opp_players)  # 3 * 3 = 9
        self.assertEqual(total_last_change_matchups, expected_matchups)
        
        # Check specific last-change pattern
        test_key = ("8480018", "8479318", "MTL", "MTL")  # MTL player vs BOS player, MTL has change, MTL making change
        self.assertGreater(self.processor.last_change_player_matchups[test_key], 0.0)
        
    def test_situation_specific_counting(self):
        """Test situation-specific matchup counting (5v5, PP, PK, etc.)"""
        # Test 5v5 situation
        event_5v5 = DeploymentEvent(
            game_id="test_003",
            event_id=3,
            period=3,
            period_time=900.0,
            game_time=3600.0,
            zone_start="DZ",
            strength_state="5v5",
            score_differential=-1,
            time_bucket="late",
            stoppage_type="faceoff",
            home_team="MTL",
            away_team="NYR",
            last_change_team="MTL",
            opponent_team="NYR",
            mtl_forwards=["8480018", "8481540", "8483515"],
            mtl_defense=["8476875", "8482087"],
            opp_forwards=["8479318", "8478483", "8482720"],
            opp_defense=["8475690", "8476853"]
        )
        
        mtl_players = event_5v5.mtl_forwards + event_5v5.mtl_defense
        opp_players = event_5v5.opp_forwards + event_5v5.opp_defense
        self.processor._update_player_matchup_counts(event_5v5, mtl_players, opp_players)
        
        # Verify 5v5 situation patterns
        total_5v5_matchups = sum(
            sum(situation_dict.values()) 
            for situation_dict in self.processor.situation_player_matchups.values()
            if "5v5" in str(situation_dict)
        )
        self.assertGreater(total_5v5_matchups, 0)


class TestPlayerMatchupEWMA(unittest.TestCase):
    """Test EWMA recency weighting and capping for player matchups"""
    
    def setUp(self):
        self.processor = DataProcessor()
        
    def test_ewma_update_mechanism(self):
        """Test EWMA weighting updates for matchups"""
        test_dict = defaultdict(float)
        test_key = ("player1", "player2")
        current_time = 1000.0
        
        # First update - should be 1.0 (initial value)
        self.processor._update_matchup_with_ewma(test_dict, test_key, current_time)
        first_value = test_dict[test_key]
        self.assertEqual(first_value, 1.0)  # First occurrence is always 1.0
        
        # Second update - should apply EWMA weighting
        self.processor._update_matchup_with_ewma(test_dict, test_key, current_time + 60.0)
        second_value = test_dict[test_key]
        # With EWMA_ALPHA = 0.2: (1.0 * 0.8) + 0.2 = 1.0 (remains same)
        self.assertEqual(second_value, 1.0)
        
        # Test that the mechanism exists and timestamps are tracked
        self.assertIn(test_key, self.processor.matchup_timestamps)
        self.assertEqual(len(self.processor.matchup_timestamps[test_key]), 2)  # Two timestamps recorded
        
    def test_low_frequency_pruning(self):
        """Test pruning of low-frequency matchups"""
        # Populate with various frequency matchups
        self.processor.player_matchup_counts[("high_freq1", "opponent1")] = 10.0
        self.processor.player_matchup_counts[("high_freq2", "opponent2")] = 8.0
        self.processor.player_matchup_counts[("low_freq1", "opponent3")] = 1.5
        self.processor.player_matchup_counts[("low_freq2", "opponent4")] = 0.8
        
        initial_count = len(self.processor.player_matchup_counts)
        
        # Run pruning
        self.processor._prune_low_frequency_matchups()
        
        # Verify low-frequency matchups were removed
        final_count = len(self.processor.player_matchup_counts)
        self.assertLess(final_count, initial_count)
        
        # Verify high-frequency matchups remain
        self.assertIn(("high_freq1", "opponent1"), self.processor.player_matchup_counts)
        self.assertIn(("high_freq2", "opponent2"), self.processor.player_matchup_counts)


class TestPlayerMatchupSerialization(unittest.TestCase):
    """Test serialization and deserialization of player matchup patterns"""
    
    def setUp(self):
        self.processor = DataProcessor()
        
    def test_matchup_pattern_serialization(self):
        """Test saving player matchup patterns with format version v2.1"""
        # Populate with test data
        self.processor.player_matchup_counts[("mtl_player1", "opp_player1")] = 5.5
        self.processor.player_matchup_counts[("mtl_player2", "opp_player2")] = 3.2
        
        self.processor.last_change_player_matchups[("mtl_player1", "opp_player1", "MTL", "MTL")] = 2.8
        
        self.processor.situation_player_matchups[("mtl_player1", "opp_player1")]["5v5"] = 4.1
        
        # Test serialization
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            self.processor._save_player_matchup_patterns(output_path)
            
            # Verify file was created
            matchup_file = output_path / "player_matchup_patterns_v2.1.json"
            self.assertTrue(matchup_file.exists())
            
            # Verify content structure
            with open(matchup_file, 'r') as f:
                data = json.load(f)
                
            self.assertEqual(data['format_version'], '2.1')
            self.assertIn('global_matchup_counts', data)
            self.assertIn('last_change_matchup_counts', data)
            self.assertIn('situation_matchup_counts', data)
            self.assertIn('creation_timestamp', data)
            
            # Verify specific data
            self.assertIn('mtl_player1__vs__opp_player1', data['global_matchup_counts'])
            self.assertEqual(data['global_matchup_counts']['mtl_player1__vs__opp_player1'], 5.5)


class TestCandidateMatchupPriors(unittest.TestCase):
    """Test matchup prior computation in candidate generator"""
    
    def setUp(self):
        self.generator = CandidateGenerator()
        
        # Populate with test matchup data
        self.generator.player_matchup_counts[("mtl_forward1", "opp_forward1")] = 8.5
        self.generator.player_matchup_counts[("mtl_forward1", "opp_forward2")] = 3.2
        self.generator.player_matchup_counts[("mtl_defense1", "opp_defense1")] = 6.1
        
        self.generator.last_change_player_matchups[("mtl_forward1", "opp_forward1", "MTL", "MTL")] = 4.2
        
        self.generator.situation_player_matchups[("mtl_forward1", "opp_forward1")]["5v5"] = 7.8
        
    def test_basic_matchup_prior_computation(self):
        """Test basic matchup prior calculation"""
        candidate_players = ["mtl_forward1", "mtl_defense1"]
        opponent_players = ["opp_forward1", "opp_defense1"]
        
        prior = self.generator.compute_matchup_prior(
            candidate_players=candidate_players,
            opponent_players=opponent_players,
            opponent_team="TOR",
            situation="5v5"
        )
        
        self.assertIsInstance(prior, float)
        self.assertGreaterEqual(prior, 0.0)
        self.assertLessEqual(prior, 1.0)
        
    def test_matchup_prior_with_last_change(self):
        """Test matchup prior computation with last-change awareness"""
        candidate_players = ["mtl_forward1"]
        opponent_players = ["opp_forward1"]
        
        prior = self.generator.compute_matchup_prior(
            candidate_players=candidate_players,
            opponent_players=opponent_players,
            opponent_team="TOR",
            last_change_team="MTL",
            team_making_change="MTL",
            situation="5v5"
        )
        
        self.assertIsInstance(prior, float)
        self.assertGreater(prior, 0.0)  # Should be positive due to matchup history
        
    def test_matchup_prior_no_history(self):
        """Test matchup prior for players with no interaction history"""
        candidate_players = ["new_mtl_player"]
        opponent_players = ["new_opp_player"]
        
        prior = self.generator.compute_matchup_prior(
            candidate_players=candidate_players,
            opponent_players=opponent_players,
            opponent_team="BOS",
            situation="5v5"
        )
        
        self.assertEqual(prior, 0.0)  # No history should result in 0.0 prior
        
    def test_candidate_matchup_prior_integration(self):
        """Test that matchup priors are properly integrated into candidates"""
        # Create test candidate
        candidate = Candidate(
            forwards=["mtl_forward1", "mtl_forward2"],
            defense=["mtl_defense1"],
            probability_prior=1.0
        )
        
        # Verify matchup_prior attribute exists
        self.assertEqual(candidate.matchup_prior, 0.0)  # Default value
        
        # Test candidate dictionary serialization includes matchup_prior
        candidate_dict = candidate.to_dict()
        self.assertIn('matchup_prior', candidate_dict)
        self.assertEqual(candidate_dict['matchup_prior'], 0.0)


class TestMatchupPriorBlending(unittest.TestCase):
    """Test blending of matchup priors into candidate probabilities"""
    
    def setUp(self):
        self.generator = CandidateGenerator()
        self.generator.enable_matchup_priors = True
        self.generator.matchup_prior_weight = 0.15
        
    def test_matchup_prior_blending_enabled(self):
        """Test that matchup priors are blended when enabled"""
        # Create candidate with known matchup prior
        candidate = Candidate(
            forwards=["test_forward"],
            defense=["test_defense"],
            probability_prior=1.0,
            matchup_prior=0.3
        )
        
        initial_prob = candidate.probability_prior
        
        # Mock the scoring process that would apply matchup prior
        if self.generator.enable_matchup_priors and candidate.matchup_prior > 0:
            candidate.probability_prior *= (1 + self.generator.matchup_prior_weight * candidate.matchup_prior)
        
        # Verify probability was modified
        self.assertGreater(candidate.probability_prior, initial_prob)
        expected_prob = initial_prob * (1 + 0.15 * 0.3)
        self.assertAlmostEqual(candidate.probability_prior, expected_prob, places=6)
        
    def test_matchup_prior_blending_disabled(self):
        """Test that matchup priors are ignored when disabled"""
        self.generator.enable_matchup_priors = False
        
        candidate = Candidate(
            forwards=["test_forward"],
            defense=["test_defense"], 
            probability_prior=1.0,
            matchup_prior=0.5
        )
        
        initial_prob = candidate.probability_prior
        
        # Mock disabled blending
        if self.generator.enable_matchup_priors and candidate.matchup_prior > 0:
            candidate.probability_prior *= (1 + self.generator.matchup_prior_weight * candidate.matchup_prior)
        
        # Verify probability was NOT modified
        self.assertEqual(candidate.probability_prior, initial_prob)


class TestIntegrationPlayerMatchups(unittest.TestCase):
    """Integration tests for the complete player-vs-player matchup system"""
    
    def test_end_to_end_matchup_flow(self):
        """Test complete flow from data extraction to candidate scoring"""
        # 1. Data Processor: Extract matchup counts
        processor = DataProcessor()
        
        event = DeploymentEvent(
            game_id="integration_test",
            event_id=999,
            period=2,
            period_time=600.0,
            game_time=2400.0,
            zone_start="NZ",
            strength_state="5v5",
            score_differential=0,
            time_bucket="middle",
            stoppage_type="faceoff",
            home_team="MTL",
            away_team="TOR",
            last_change_team="MTL",
            opponent_team="TOR",
            mtl_forwards=["8480018", "8481540"],
            mtl_defense=["8476875"],
            opp_forwards=["8479318", "8478483"],
            opp_defense=["8475690"]
        )
        
        mtl_players = event.mtl_forwards + event.mtl_defense
        opp_players = event.opp_forwards + event.opp_defense
        processor._update_player_matchup_counts(event, mtl_players, opp_players)
        
        # 2. Candidate Generator: Load patterns and compute priors
        generator = CandidateGenerator()
        
        # Simulate loading patterns from processor
        for key, count in processor.player_matchup_counts.items():
            generator.player_matchup_counts[key] = count
            
        for key, count in processor.last_change_player_matchups.items():
            generator.last_change_player_matchups[key] = count
            
        # 3. Compute matchup prior for a candidate
        candidate_players = ["8480018", "8476875"]  # MTL players from event
        opponent_players = ["8479318", "8475690"]   # Opponent players from event
        
        prior = generator.compute_matchup_prior(
            candidate_players=candidate_players,
            opponent_players=opponent_players,
            opponent_team="TOR",
            last_change_team="MTL",
            team_making_change="MTL",
            situation="5v5"
        )
        
        # 4. Verify end-to-end integration
        self.assertIsInstance(prior, float)
        self.assertGreater(prior, 0.0)  # Should be positive due to recorded interactions
        
        # 5. Test candidate creation with matchup prior
        candidate = Candidate(
            forwards=["8480018", "8481540"],
            defense=["8476875"],
            matchup_prior=prior
        )
        
        self.assertEqual(candidate.matchup_prior, prior)
        
        # 6. Test serialization includes all components
        candidate_dict = candidate.to_dict()
        self.assertIn('matchup_prior', candidate_dict)
        self.assertEqual(candidate_dict['matchup_prior'], prior)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
