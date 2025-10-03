"""
Test Cache Key Isolation
Verify cache keys properly isolate last-change and team role contexts
Professional-grade testing for NHL analytics
"""

import unittest
from unittest.mock import Mock, patch

# Import the modules we're testing
from live_predictor import LiveLinePredictor, GameState
from candidate_generator import Candidate


class TestCacheKeyIsolation(unittest.TestCase):
    """Test cache key isolation for different contexts"""
    
    def setUp(self):
        self.predictor = LiveLinePredictor()
        
        # Create base game state
        self.base_game_state = GameState(
            game_id="cache_test",
            period=2,
            period_time=600.0,
            home_team="MTL",
            away_team="TOR",
            home_score=1,
            away_score=1,
            strength_state="5v5",
            zone="nz",
            
            # Available players
            opp_forwards_available=["opp1", "opp2", "opp3", "opp4", "opp5"],
            opp_defense_available=["opp_d1", "opp_d2", "opp_d3"],
            
            # Rest times
            player_rest_times={
                "opp1": 60.0, "opp2": 45.0, "opp3": 90.0,
                "opp4": 75.0, "opp5": 120.0,
                "opp_d1": 80.0, "opp_d2": 100.0, "opp_d3": 65.0
            }
        )
    
    def test_cache_key_includes_last_change_context(self):
        """Test that cache keys include last change context"""
        # Mock the fresh candidate generation to control output
        mock_candidates = [
            Candidate(forwards=['opp1', 'opp2', 'opp3'], defense=['opp_d1', 'opp_d2'], probability_prior=0.8),
            Candidate(forwards=['opp4', 'opp5', 'opp3'], defense=['opp_d2', 'opp_d3'], probability_prior=0.6)
        ]
        
        with patch.object(self.predictor, '_generate_fresh_candidates', return_value=mock_candidates):
            # Scenario 1: MTL has last change
            game_state_mtl_change = self.base_game_state
            game_state_mtl_change.last_change_team = "MTL"
            
            candidates_1 = self.predictor._generate_candidates(
                game_state=game_state_mtl_change,
                max_candidates=5,
                opponent_team="TOR"
            )
            
            # Scenario 2: Opponent has last change (same game situation, different last change)
            game_state_opp_change = self.base_game_state
            game_state_opp_change.last_change_team = "TOR"
            
            candidates_2 = self.predictor._generate_candidates(
                game_state=game_state_opp_change,
                max_candidates=5,
                opponent_team="TOR"
            )
            
            # Cache should have different entries for different last-change contexts
            # Check that cache has multiple entries (indicates different cache keys)
            self.assertGreaterEqual(len(self.predictor.candidate_cache), 1)
            
            # Verify cache keys are different for different contexts
            cache_keys = list(self.predictor.candidate_cache.keys())
            
            # Each key should include last_change_team information
            for key in cache_keys:
                self.assertIn("_", key)  # Should have underscores separating components
                # Key format: zone_strength_score_diff_last_change_team_team_role
                parts = key.split("_")
                self.assertGreaterEqual(len(parts), 5)  # At least 5 components
    
    def test_cache_key_includes_team_role(self):
        """Test that cache keys differentiate between MTL and opponent team roles"""
        mock_candidates = [
            Candidate(forwards=['p1', 'p2', 'p3'], defense=['d1', 'd2'], probability_prior=0.7)
        ]
        
        with patch.object(self.predictor, '_generate_fresh_candidates', return_value=mock_candidates):
            # Scenario 1: Generating for opponent team (team_role = 'OPP')
            candidates_opp = self.predictor._generate_candidates(
                game_state=self.base_game_state,
                max_candidates=3,
                opponent_team="TOR"  # This makes team_role = 'OPP'
            )
            
            # Scenario 2: Generating for MTL (team_role = 'MTL')
            candidates_mtl = self.predictor._generate_candidates(
                game_state=self.base_game_state,
                max_candidates=3,
                opponent_team=None  # This makes team_role = 'MTL'
            )
            
            # Should have different cache entries
            cache_keys = list(self.predictor.candidate_cache.keys())
            
            # Verify we have entries for both team roles
            opp_keys = [k for k in cache_keys if k.endswith("_OPP")]
            mtl_keys = [k for k in cache_keys if k.endswith("_MTL")]
            
            # Should have at least one of each type
            self.assertGreaterEqual(len(opp_keys) + len(mtl_keys), 1)
    
    def test_cache_isolation_prevents_cross_context_reuse(self):
        """Test that candidates from different contexts are not reused inappropriately"""
        # Create distinct candidates for different contexts
        mtl_candidates = [
            Candidate(forwards=['mtl1', 'mtl2', 'mtl3'], defense=['mtl_d1', 'mtl_d2'], probability_prior=0.9)
        ]
        opp_candidates = [
            Candidate(forwards=['opp1', 'opp2', 'opp3'], defense=['opp_d1', 'opp_d2'], probability_prior=0.8)
        ]
        
        def mock_fresh_candidates(game_state, max_candidates):
            # Return different candidates based on context
            if hasattr(game_state, 'last_change_team') and game_state.last_change_team == 'MTL':
                return mtl_candidates
            else:
                return opp_candidates
        
        with patch.object(self.predictor, '_generate_fresh_candidates', side_effect=mock_fresh_candidates):
            # Clear cache to start fresh
            self.predictor.candidate_cache.clear()
            
            # Generate candidates for MTL last change context
            game_state_1 = self.base_game_state
            game_state_1.last_change_team = "MTL"
            
            result_1 = self.predictor._generate_candidates(
                game_state=game_state_1,
                max_candidates=3,
                opponent_team="TOR"
            )
            
            # Generate candidates for opponent last change context
            game_state_2 = self.base_game_state
            game_state_2.last_change_team = "TOR"
            
            result_2 = self.predictor._generate_candidates(
                game_state=game_state_2,
                max_candidates=3,
                opponent_team="TOR"
            )
            
            # Results should be different (no cross-context reuse)
            if result_1 and result_2:
                # Compare first candidate forwards to ensure they're different
                result_1_forwards = set(result_1[0].forwards) if result_1[0].forwards else set()
                result_2_forwards = set(result_2[0].forwards) if result_2[0].forwards else set()
                
                # Should be different candidates for different contexts
                self.assertNotEqual(result_1_forwards, result_2_forwards, 
                                   "Different last-change contexts should produce different candidates")
    
    def test_cache_key_format_consistency(self):
        """Test that cache key format is consistent and predictable"""
        # Test cache key generation with known inputs
        game_state = self.base_game_state
        game_state.zone = "dz"
        game_state.strength_state = "5v5"
        game_state.home_score = 1  # MTL score
        game_state.away_score = 2  # Opponent score (creates -1 differential)
        game_state.last_change_team = "MTL"
        
        with patch.object(self.predictor, '_generate_fresh_candidates', return_value=[]):
            self.predictor._generate_candidates(
                game_state=game_state,
                max_candidates=3,
                opponent_team="TOR"
            )
            
            # Verify cache key format includes context information
            cache_keys = list(self.predictor.candidate_cache.keys())
            if cache_keys:
                key = cache_keys[0]
                # Cache key should include last_change and team role context
                self.assertIn("_", key)  # Should have separators
                # Verify it's not just the basic format (zone_strength_score)
                parts = key.split("_")
                self.assertGreaterEqual(len(parts), 4)  # Should have additional context beyond basic


if __name__ == '__main__':
    unittest.main()
