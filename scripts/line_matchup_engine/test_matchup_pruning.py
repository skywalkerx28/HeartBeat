"""
Test Player Matchup Pruning Performance Optimization
Verify that pruning keeps top-N matchups per player while managing memory
"""

import unittest
from collections import defaultdict

# Import the module we're testing
from data_processor import DataProcessor, TOP_N_MATCHUPS_PER_PLAYER, MIN_MATCHUP_FREQUENCY


class TestMatchupPruning(unittest.TestCase):
    """Test player matchup pruning optimization"""
    
    def setUp(self):
        self.processor = DataProcessor()
    
    def test_top_n_pruning_global_matchups(self):
        """Test that top-N pruning keeps only the most frequent matchups per MTL player"""
        # Set up test data with one MTL player having many opponent matchups
        mtl_player = "8480018"  # MTL player
        
        # Create 30 opponent matchups with varying frequencies
        for i in range(30):
            opp_player = f"opp_player_{i:03d}"
            frequency = 30 - i  # Descending frequency (30, 29, 28, ... 1)
            self.processor.player_matchup_counts[(mtl_player, opp_player)] = float(frequency)
        
        # Original count should be 30
        original_count = len(self.processor.player_matchup_counts)
        self.assertEqual(original_count, 30)
        
        # Apply top-N pruning
        self.processor._prune_to_top_n_per_player()
        
        # Should keep only TOP_N_MATCHUPS_PER_PLAYER (25) matchups
        pruned_count = len(self.processor.player_matchup_counts)
        self.assertEqual(pruned_count, TOP_N_MATCHUPS_PER_PLAYER)
        
        # Verify that the kept matchups are the highest frequency ones
        kept_matchups = list(self.processor.player_matchup_counts.items())
        kept_frequencies = [count for (_, _), count in kept_matchups]
        
        # Should be frequencies 30, 29, 28, ..., 6 (top 25)
        expected_frequencies = list(range(30, 30 - TOP_N_MATCHUPS_PER_PLAYER, -1))
        self.assertEqual(sorted(kept_frequencies, reverse=True), expected_frequencies)
    
    def test_top_n_pruning_multiple_players(self):
        """Test top-N pruning with multiple MTL players"""
        # Set up test data with multiple MTL players
        mtl_players = ["8480018", "8481540", "8483515"]
        
        for mtl_player in mtl_players:
            # Each MTL player has 20 opponent matchups
            for i in range(20):
                opp_player = f"opp_{mtl_player}_{i:02d}"
                frequency = 20 - i  # Descending frequency
                self.processor.player_matchup_counts[(mtl_player, opp_player)] = float(frequency)
        
        # Original count: 3 players × 20 matchups = 60
        original_count = len(self.processor.player_matchup_counts)
        self.assertEqual(original_count, 60)
        
        # Apply top-N pruning
        self.processor._prune_to_top_n_per_player()
        
        # Each player should keep all 20 matchups (since 20 < TOP_N_MATCHUPS_PER_PLAYER)
        pruned_count = len(self.processor.player_matchup_counts)
        self.assertEqual(pruned_count, 60)  # No pruning since each player has < 25 matchups
    
    def test_top_n_pruning_last_change_matchups(self):
        """Test top-N pruning for last-change-aware matchups"""
        mtl_player = "8480018"
        
        # Create 30 last-change matchups with complex keys
        for i in range(30):
            opp_player = f"opp_player_{i:03d}"
            frequency = 30 - i
            
            # Create last-change key: (mtl_player, opp_player, last_change_team, team_making_change)
            key = (mtl_player, opp_player, "MTL", "MTL")
            self.processor.last_change_player_matchups[key] = float(frequency)
        
        original_count = len(self.processor.last_change_player_matchups)
        self.assertEqual(original_count, 30)
        
        # Apply top-N pruning
        self.processor._prune_to_top_n_per_player()
        
        # Should keep only top 25 matchups
        pruned_count = len(self.processor.last_change_player_matchups)
        self.assertEqual(pruned_count, TOP_N_MATCHUPS_PER_PLAYER)
        
        # Verify that the highest frequency matchups were kept
        kept_frequencies = list(self.processor.last_change_player_matchups.values())
        expected_frequencies = list(range(30, 30 - TOP_N_MATCHUPS_PER_PLAYER, -1))
        self.assertEqual(sorted(kept_frequencies, reverse=True), expected_frequencies)
    
    def test_situation_specific_pruning(self):
        """Test pruning of situation-specific matchups"""
        player_pair = ("8480018", "8479318")
        
        # Create many situations for this player pair
        situations = ["5v5", "5v4", "4v5", "6v5", "5v6", "4v4", "3v3", "6v4", "4v6", "3v4", 
                     "4v3", "6v3", "3v6", "5v3", "3v5", "custom_1", "custom_2", "custom_3",
                     "custom_4", "custom_5", "custom_6", "custom_7", "custom_8", "custom_9",
                     "custom_10", "custom_11", "custom_12", "custom_13", "custom_14", "custom_15"]
        
        for i, situation in enumerate(situations):
            frequency = len(situations) - i  # Descending frequency
            self.processor.situation_player_matchups[player_pair][situation] = float(frequency)
        
        original_situation_count = len(self.processor.situation_player_matchups[player_pair])
        self.assertEqual(original_situation_count, len(situations))
        
        # Apply top-N pruning
        self.processor._prune_to_top_n_per_player()
        
        # Should keep only top 25 situations
        pruned_situation_count = len(self.processor.situation_player_matchups[player_pair])
        self.assertEqual(pruned_situation_count, TOP_N_MATCHUPS_PER_PLAYER)
        
        # Verify highest frequency situations were kept
        kept_frequencies = list(self.processor.situation_player_matchups[player_pair].values())
        expected_frequencies = list(range(len(situations), len(situations) - TOP_N_MATCHUPS_PER_PLAYER, -1))
        self.assertEqual(sorted(kept_frequencies, reverse=True), expected_frequencies)
    
    def test_low_frequency_pruning_integration(self):
        """Test that low-frequency pruning works alongside top-N pruning"""
        mtl_player = "8480018"
        
        # Create matchups with some below MIN_MATCHUP_FREQUENCY threshold
        test_data = [
            ("opp_high_1", 10.0),    # Above threshold
            ("opp_high_2", 8.0),     # Above threshold  
            ("opp_high_3", 5.0),     # Above threshold
            ("opp_low_1", 2.0),      # Below threshold (MIN_MATCHUP_FREQUENCY = 3)
            ("opp_low_2", 1.0),      # Below threshold
            ("opp_low_3", 0.5),      # Below threshold
        ]
        
        for opp_player, frequency in test_data:
            self.processor.player_matchup_counts[(mtl_player, opp_player)] = frequency
        
        original_count = len(self.processor.player_matchup_counts)
        self.assertEqual(original_count, 6)
        
        # Apply low-frequency pruning first
        self.processor._prune_low_frequency_matchups()
        
        # Should remove the 3 low-frequency matchups
        after_low_freq_pruning = len(self.processor.player_matchup_counts)
        self.assertEqual(after_low_freq_pruning, 3)
        
        # Verify only high-frequency matchups remain
        remaining_frequencies = list(self.processor.player_matchup_counts.values())
        expected_remaining = [10.0, 8.0, 5.0]
        self.assertEqual(sorted(remaining_frequencies, reverse=True), expected_remaining)
        
        # Apply top-N pruning (should not remove anything since only 3 matchups remain)
        self.processor._prune_to_top_n_per_player()
        final_count = len(self.processor.player_matchup_counts)
        self.assertEqual(final_count, 3)
    
    def test_pruning_statistics_logging(self):
        """Test that pruning statistics are correctly calculated"""
        import logging
        
        # Set up a large dataset to ensure pruning occurs
        mtl_players = ["8480018", "8481540"]
        
        for mtl_player in mtl_players:
            # Each player gets 40 matchups (will be pruned to 25)
            for i in range(40):
                opp_player = f"opp_{mtl_player}_{i:03d}"
                frequency = 40 - i
                self.processor.player_matchup_counts[(mtl_player, opp_player)] = float(frequency)
                
                # Also add last-change matchups
                key = (mtl_player, opp_player, "MTL", "MTL")
                self.processor.last_change_player_matchups[key] = float(frequency)
        
        original_global = len(self.processor.player_matchup_counts)
        original_last_change = len(self.processor.last_change_player_matchups)
        
        # Apply pruning (this will log statistics)
        with self.assertLogs('data_processor', level='INFO') as log_context:
            self.processor._prune_to_top_n_per_player()
        
        # Verify counts after pruning
        final_global = len(self.processor.player_matchup_counts)
        final_last_change = len(self.processor.last_change_player_matchups)
        
        # Each player should have 25 matchups (2 players × 25 = 50 total)
        self.assertEqual(final_global, 2 * TOP_N_MATCHUPS_PER_PLAYER)
        self.assertEqual(final_last_change, 2 * TOP_N_MATCHUPS_PER_PLAYER)
        
        # Verify logging occurred
        log_messages = [record.getMessage() for record in log_context.records]
        pruning_logs = [msg for msg in log_messages if "Top-N pruning complete" in msg]
        self.assertTrue(len(pruning_logs) > 0, "Expected pruning completion log message")


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    unittest.main()
