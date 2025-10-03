"""
Test MTL Matrices Serialization (v2.1)
Comprehensive roundtrip tests for MTL last-change matrices save/load
Professional-grade testing for NHL analytics
"""

import unittest
import tempfile
import json
from pathlib import Path
from collections import defaultdict

# Import the modules we're testing
from data_processor import DataProcessor, DeploymentEvent
from candidate_generator import CandidateGenerator


class TestMTLMatricesSerialization(unittest.TestCase):
    """Test MTL matrices serialization and loading"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.processor = DataProcessor()
        self.generator = CandidateGenerator()
        
        # Set up test MTL matrices data
        self._setup_test_mtl_matrices()
        
    def _setup_test_mtl_matrices(self):
        """Set up test data for MTL matrices"""
        # MTL response matrix: opponent lineup -> MTL response -> weight
        self.processor.mtl_response_matrix = defaultdict(lambda: defaultdict(float))
        self.processor.mtl_response_matrix["F:opp1|opp2|opp3_D:opp4|opp5"]["F:mtl1|mtl2|mtl3_D:mtl4|mtl5"] = 2.5
        self.processor.mtl_response_matrix["F:opp6|opp7|opp8_D:opp9|opp10"]["F:mtl6|mtl7|mtl8_D:mtl9|mtl10"] = 1.8
        
        # MTL forwards vs opponent forwards
        self.processor.mtl_vs_opp_forwards = defaultdict(lambda: defaultdict(float))
        self.processor.mtl_vs_opp_forwards["mtl_fwd_1"]["opp_fwd_1"] = 3.2
        self.processor.mtl_vs_opp_forwards["mtl_fwd_1"]["opp_fwd_2"] = 1.9
        self.processor.mtl_vs_opp_forwards["mtl_fwd_2"]["opp_fwd_1"] = 2.1
        
        # MTL defense vs opponent forwards
        self.processor.mtl_defense_vs_opp_forwards = defaultdict(lambda: defaultdict(float))
        self.processor.mtl_defense_vs_opp_forwards["mtl_def_1"]["opp_fwd_1"] = 2.7
        self.processor.mtl_defense_vs_opp_forwards["mtl_def_1"]["opp_fwd_3"] = 1.4
        self.processor.mtl_defense_vs_opp_forwards["mtl_def_2"]["opp_fwd_2"] = 2.0
    
    def test_mtl_matrices_save_format(self):
        """Test that MTL matrices are properly saved in v2.1 format"""
        # Save the patterns
        self.processor._save_player_matchup_patterns(self.temp_dir)
        
        # Check that the file was created
        patterns_file = self.temp_dir / 'player_matchup_patterns_v2.1.json'
        self.assertTrue(patterns_file.exists(), "Patterns file should be created")
        
        # Load and verify the saved data
        with open(patterns_file, 'r') as f:
            saved_data = json.load(f)
        
        # Verify format version
        self.assertEqual(saved_data['format_version'], '2.1')
        
        # Verify MTL matrices are present
        self.assertIn('mtl_response_matrix', saved_data)
        self.assertIn('mtl_vs_opp_forwards', saved_data)
        self.assertIn('mtl_defense_vs_opp_forwards', saved_data)
        
        # Verify data integrity
        mtl_response = saved_data['mtl_response_matrix']
        self.assertEqual(len(mtl_response), 2)  # 2 opponent lineups
        
        mtl_vs_opp = saved_data['mtl_vs_opp_forwards']
        self.assertEqual(len(mtl_vs_opp), 2)  # 2 MTL forwards
        
        mtl_def_vs_opp = saved_data['mtl_defense_vs_opp_forwards']
        self.assertEqual(len(mtl_def_vs_opp), 2)  # 2 MTL defensemen
    
    def test_mtl_matrices_load_roundtrip(self):
        """Test complete save/load roundtrip for MTL matrices"""
        # Save the patterns
        self.processor._save_player_matchup_patterns(self.temp_dir)
        
        # Load patterns into candidate generator
        patterns_file = self.temp_dir / 'player_matchup_patterns_v2.1.json'
        
        # Simulate loading the patterns (as would happen in candidate_generator.load_patterns)
        with open(patterns_file, 'r') as f:
            patterns_data = json.load(f)
        
        # Load MTL matrices into candidate generator
        if 'mtl_response_matrix' in patterns_data:
            self.generator.mtl_response_matrix = defaultdict(lambda: defaultdict(float))
            for opp_lineup, inner in patterns_data['mtl_response_matrix'].items():
                for mtl_resp, w in inner.items():
                    self.generator.mtl_response_matrix[opp_lineup][mtl_resp] = float(w)
        
        if 'mtl_vs_opp_forwards' in patterns_data:
            self.generator.mtl_vs_opp_forwards = defaultdict(lambda: defaultdict(float))
            for mtl_fwd, inner in patterns_data['mtl_vs_opp_forwards'].items():
                for opp_fwd, w in inner.items():
                    self.generator.mtl_vs_opp_forwards[mtl_fwd][opp_fwd] = float(w)
        
        if 'mtl_defense_vs_opp_forwards' in patterns_data:
            self.generator.mtl_defense_vs_opp_forwards = defaultdict(lambda: defaultdict(float))
            for mtl_def, inner in patterns_data['mtl_defense_vs_opp_forwards'].items():
                for opp_fwd, w in inner.items():
                    self.generator.mtl_defense_vs_opp_forwards[mtl_def][opp_fwd] = float(w)
        
        # Verify loaded data matches original
        # MTL response matrix
        self.assertEqual(
            self.generator.mtl_response_matrix["F:opp1|opp2|opp3_D:opp4|opp5"]["F:mtl1|mtl2|mtl3_D:mtl4|mtl5"],
            2.5
        )
        
        # MTL forwards vs opponent forwards
        self.assertEqual(self.generator.mtl_vs_opp_forwards["mtl_fwd_1"]["opp_fwd_1"], 3.2)
        self.assertEqual(self.generator.mtl_vs_opp_forwards["mtl_fwd_2"]["opp_fwd_1"], 2.1)
        
        # MTL defense vs opponent forwards
        self.assertEqual(self.generator.mtl_defense_vs_opp_forwards["mtl_def_1"]["opp_fwd_1"], 2.7)
        self.assertEqual(self.generator.mtl_defense_vs_opp_forwards["mtl_def_2"]["opp_fwd_2"], 2.0)
    
    def test_mtl_matrices_empty_handling(self):
        """Test that empty MTL matrices are handled gracefully"""
        # Create processor with no MTL matrices
        empty_processor = DataProcessor()
        
        # Save patterns (should handle missing matrices gracefully)
        empty_processor._save_player_matchup_patterns(self.temp_dir)
        
        # Load and verify empty matrices are saved as empty dicts
        patterns_file = self.temp_dir / 'player_matchup_patterns_v2.1.json'
        with open(patterns_file, 'r') as f:
            saved_data = json.load(f)
        
        # Verify empty matrices are present but empty
        self.assertEqual(saved_data['mtl_response_matrix'], {})
        self.assertEqual(saved_data['mtl_vs_opp_forwards'], {})
        self.assertEqual(saved_data['mtl_defense_vs_opp_forwards'], {})
    
    def test_mtl_matrices_integration_with_matchup_prior(self):
        """Test that loaded MTL matrices integrate correctly with matchup prior computation"""
        # Save and load the patterns
        self.processor._save_player_matchup_patterns(self.temp_dir)
        
        # Load patterns into candidate generator using the actual load method
        patterns_file = self.temp_dir / 'player_matchup_patterns_v2.1.json'
        
        # Simulate the full loading process
        with open(patterns_file, 'r') as f:
            patterns_data = json.load(f)
        
        # Create full patterns dict as expected by load_patterns
        full_patterns = {
            'forward_combinations': {},
            'defense_pairs': {},
            'full_deployments': {},
            'powerplay_units': {},
            'penalty_kill_units': {},
            'player_chemistry': {},
            'coach_patterns': {'defensive_zone_starts': {}, 'offensive_zone_starts': {}},
            'forwards_pool': [],
            'defense_pool': [],
            'rotation_transitions': {},
            'rotation_counts': {},
            'line_frequencies': {},
            'pp_second_units': {},
            'pk_second_units': {},
            'last_change_rotation_transitions': {},
            'last_change_rotation_counts': {},
            'patterns_format_version': '2.0',
            'player_matchup_patterns': patterns_data
        }
        
        # Use a mock file to test the loading
        import pickle
        temp_patterns_file = self.temp_dir / 'test_patterns.pkl'
        with open(temp_patterns_file, 'wb') as f:
            pickle.dump(full_patterns, f)
        
        # Load patterns using the actual method
        self.generator.load_patterns(temp_patterns_file)
        
        # Verify MTL matrices are loaded correctly
        self.assertGreater(len(self.generator.mtl_response_matrix), 0)
        self.assertGreater(len(self.generator.mtl_vs_opp_forwards), 0)
        self.assertGreater(len(self.generator.mtl_defense_vs_opp_forwards), 0)
        
        # Test matchup prior computation with MTL matrices
        # This should use the MTL-side priors when MTL has last change
        matchup_prior = self.generator.compute_matchup_prior(
            candidate_players=['mtl_fwd_1', 'mtl_def_1'],
            opponent_players=['opp_fwd_1'],
            opponent_team='TOR',
            last_change_team='MTL',
            team_making_change='MTL',
            situation='5v5'
        )
        
        # Should be non-zero due to MTL-side priors
        self.assertGreater(matchup_prior, 0.0, "Matchup prior should include MTL-side contributions")


if __name__ == '__main__':
    unittest.main()
