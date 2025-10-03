"""
Test Team Consistency: UTA Present, ARI Absent
Verify that all team mappings and references are updated for the Arizona → Utah transition
Professional-grade testing for NHL analytics
"""

import unittest
from collections import defaultdict

# Import modules to test
from conditional_logit_model import PyTorchConditionalLogit
from candidate_generator import CandidateGenerator
from data_processor import DataProcessor


class TestTeamConsistency(unittest.TestCase):
    """Test that UTA is present and ARI is absent across all components"""
    
    def setUp(self):
        self.model = PyTorchConditionalLogit(
            n_players=50,
            embedding_dim=32,
            enable_team_embeddings=True,
            team_embedding_dim=16,
            n_teams=33
        )
        self.generator = CandidateGenerator()
        self.processor = DataProcessor()
    
    def test_model_team_mapping_uta_present(self):
        """Test that UTA is present in model team mapping"""
        self.assertIn('UTA', self.model.team_to_idx, "UTA should be in model team mapping")
        
        # Verify UTA has a valid index
        uta_idx = self.model.team_to_idx['UTA']
        self.assertIsInstance(uta_idx, int)
        self.assertGreaterEqual(uta_idx, 0)
        self.assertLess(uta_idx, len(self.model.team_to_idx))
    
    def test_model_team_mapping_ari_absent(self):
        """Test that ARI is absent from model team mapping"""
        self.assertNotIn('ARI', self.model.team_to_idx, "ARI should not be in model team mapping (moved to UTA)")
    
    def test_nhl_teams_list_complete(self):
        """Test that the NHL teams list is complete with UTA and without ARI"""
        # Get the team mapping
        team_mapping = self.model.team_to_idx
        
        # Expected 32 NHL teams (UTA replaces ARI) + UNK = 33 total
        expected_teams = {
            'ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL',
            'DET', 'EDM', 'FLA', 'LAK', 'MIN', 'MTL', 'NJD', 'NSH', 'NYI', 'NYR',
            'OTT', 'PHI', 'PIT', 'SEA', 'SJS', 'STL', 'TBL', 'TOR', 'UTA', 'VAN', 'VGK',
            'WPG', 'WSH', 'UNK'  # UNK for unknown teams
        }
        
        # Verify all expected teams are present
        for team in expected_teams:
            self.assertIn(team, team_mapping, f"Team {team} should be in mapping")
        
        # Verify no unexpected teams (especially ARI)
        for team in team_mapping:
            self.assertIn(team, expected_teams, f"Unexpected team {team} in mapping")
        
        # Verify exact count
        self.assertEqual(len(team_mapping), 33, f"Expected 33 teams (32 NHL + UNK), got {len(team_mapping)}")
    
    def test_team_embedding_dimensions(self):
        """Test that team embeddings accommodate all teams including UTA"""
        if self.model.team_embeddings is not None:
            # Should have embeddings for 33 teams (32 NHL + UNK)
            num_embeddings = self.model.team_embeddings.num_embeddings
            self.assertEqual(num_embeddings, 33, f"Expected 33 team embeddings, got {num_embeddings}")
            
            # Verify UTA can be embedded
            uta_idx = self.model.team_to_idx['UTA']
            self.assertLess(uta_idx, num_embeddings, "UTA index should be within embedding range")
    
    def test_team_utility_head_compatibility(self):
        """Test that team utility head works with UTA embeddings"""
        if self.model.team_utility_head is not None and self.model.team_embeddings is not None:
            # Test UTA vs MTL interaction
            import torch
            
            uta_idx = self.model.team_to_idx['UTA']
            mtl_idx = self.model.team_to_idx['MTL']
            
            uta_emb = self.model.team_embeddings(torch.tensor(uta_idx))
            mtl_emb = self.model.team_embeddings(torch.tensor(mtl_idx))
            
            # Test bidirectional interaction
            interaction = torch.cat([mtl_emb, uta_emb], dim=0)  # 32D
            self.assertEqual(interaction.shape[0], 32, "Team interaction should be 32D")
            
            # Test utility head
            utility = self.model.team_utility_head(interaction)
            self.assertEqual(utility.shape[0], 1, "Team utility should be scalar")
            self.assertFalse(torch.isnan(utility), "Team utility should not be NaN")
    
    def test_no_ari_references_in_patterns(self):
        """Test that no ARI references exist in rotation patterns"""
        # Check candidate generator patterns
        for team_key in self.generator.last_change_rotation_transitions.keys():
            if isinstance(team_key, tuple):
                for team in team_key:
                    if isinstance(team, str):
                        self.assertNotEqual(team, 'ARI', f"Found ARI reference in rotation transitions: {team_key}")
        
        # Check data processor patterns  
        for pattern_key in self.processor.team_player_rest_patterns.keys():
            self.assertNotIn('ARI', pattern_key, f"Found ARI reference in rest patterns: {pattern_key}")
    
    def test_uta_pattern_compatibility(self):
        """Test that UTA can be used in all pattern structures"""
        # Test that UTA works in rotation patterns
        test_key = ('MTL', 'UTA', 'has_last_change', 'Line1_D1', 'Line2_D2')
        self.generator.last_change_rotation_transitions[test_key] = 0.5
        
        # Verify it was stored correctly
        self.assertEqual(self.generator.last_change_rotation_transitions[test_key], 0.5)
        
        # Test that UTA works in rest patterns
        uta_rest_key = "UTA_vs_MTL"
        self.processor.team_player_rest_patterns[uta_rest_key]['test_player']['5v5'] = [45.0, 60.0, 30.0]
        
        # Verify it was stored correctly
        self.assertEqual(len(self.processor.team_player_rest_patterns[uta_rest_key]['test_player']['5v5']), 3)
    
    def test_team_count_consistency(self):
        """Test that team counts are consistent across all components"""
        # Model should have 33 teams (32 NHL + UNK)
        model_teams = len(self.model.team_to_idx)
        self.assertEqual(model_teams, 33, f"Model should have 33 teams, got {model_teams}")
        
        # Verify UTA is counted as one of the 32 NHL teams
        nhl_teams = [team for team in self.model.team_to_idx.keys() if team != 'UNK']
        self.assertEqual(len(nhl_teams), 32, f"Should have 32 NHL teams, got {len(nhl_teams)}")
        self.assertIn('UTA', nhl_teams, "UTA should be counted as NHL team")
        self.assertNotIn('ARI', nhl_teams, "ARI should not be counted as NHL team")
    
    def test_alphabetical_ordering_with_uta(self):
        """Test that teams are properly ordered alphabetically with UTA"""
        nhl_teams = [team for team in self.model.team_to_idx.keys() if team != 'UNK']
        sorted_teams = sorted(nhl_teams)
        
        # Verify UTA comes after TOR and before VAN
        uta_index = sorted_teams.index('UTA')
        tor_index = sorted_teams.index('TOR') 
        van_index = sorted_teams.index('VAN')
        
        self.assertLess(tor_index, uta_index, "TOR should come before UTA alphabetically")
        self.assertLess(uta_index, van_index, "UTA should come before VAN alphabetically")
    
    def test_ood_detection_with_uta(self):
        """Test that OOD detection works correctly with UTA"""
        import torch
        
        # Create a feature vector and test OOD detection with UTA
        feature_vector = torch.randn(65)  # Expected dimension
        
        # This should not raise any errors
        self.model._validate_and_log_feature_vector(feature_vector, "UTA")
        
        # Verify UTA is tracked in OOD counters
        if hasattr(self.model, 'ood_counters'):
            # OOD counters should accept UTA as a valid opponent
            self.assertIsInstance(self.model.ood_counters['by_opponent']['UTA'], dict)


if __name__ == '__main__':
    unittest.main()
