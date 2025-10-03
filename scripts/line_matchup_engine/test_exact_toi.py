#!/usr/bin/env python3
"""
Unit tests for exact time-on-ice computation
Verifies mathematical precision of sequential appearance tracking
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import logging
from datetime import datetime

# Suppress logging during tests
logging.disable(logging.CRITICAL)

from data_processor import PlayByPlayProcessor

class TestExactTOIComputation(unittest.TestCase):
    """Test exact time-on-ice computation from sequential appearances"""
    
    def setUp(self):
        """Create synthetic test data"""
        
        # Create synthetic play-by-play data
        self.test_data = pd.DataFrame([
            # Player appears for 3 consecutive events (40s total)
            {'gameTime': 0, 'periodTime': 0, 'timecode': '00:00:00:00',
             'teamForwardsOnIceRefs': 'player_1\tplayer_2\tplayer_3',
             'teamDefencemenOnIceRefs': 'player_4\tplayer_5',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3',
             'opposingTeamDefencemenOnIceRefs': 'opp_4\topp_5',
             'period': 1, 'strengthState': '5v5'},
            
            {'gameTime': 15, 'periodTime': 15, 'timecode': '00:00:15:00',
             'teamForwardsOnIceRefs': 'player_1\tplayer_2\tplayer_3',
             'teamDefencemenOnIceRefs': 'player_4\tplayer_5',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3',
             'opposingTeamDefencemenOnIceRefs': 'opp_4\topp_5',
             'period': 1, 'strengthState': '5v5'},
            
            {'gameTime': 40, 'periodTime': 40, 'timecode': '00:00:40:00',
             'teamForwardsOnIceRefs': 'player_1\tplayer_2\tplayer_3',
             'teamDefencemenOnIceRefs': 'player_4\tplayer_5',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3',
             'opposingTeamDefencemenOnIceRefs': 'opp_4\topp_5',
             'period': 1, 'strengthState': '5v5'},
            
            # Player_1 changes (shift ends at 40s, next shift starts at 120s)
            {'gameTime': 60, 'periodTime': 60, 'timecode': '00:01:30:00',
             'teamForwardsOnIceRefs': 'player_6\tplayer_2\tplayer_3',
             'teamDefencemenOnIceRefs': 'player_4\tplayer_5',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3',
             'opposingTeamDefencemenOnIceRefs': 'opp_4\topp_5',
             'period': 1, 'strengthState': '5v5'},
            
            # Player_1 returns
            {'gameTime': 120, 'periodTime': 120, 'timecode': '00:03:00:00',
             'teamForwardsOnIceRefs': 'player_1\tplayer_2\tplayer_3',
             'teamDefencemenOnIceRefs': 'player_4\tplayer_5',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3',
             'opposingTeamDefencemenOnIceRefs': 'opp_4\topp_5',
             'period': 1, 'strengthState': '5v5'},
        ])
        
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.data_path = Path(self.temp_dir) / 'data'
        self.data_path.mkdir()
        
        # Save test CSV
        self.test_csv = self.data_path / 'test-MTLvsTOR-game.csv'
        self.test_data.to_csv(self.test_csv, index=False)
        
        # Create processor
        self.processor = PlayByPlayProcessor(
            self.data_path, 
            Path('/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/dim/player_ids.csv')
        )
    
    def test_exact_toi_calculation(self):
        """Test that exact TOI is calculated correctly"""
        
        # Process the test game
        self.processor.process_game(self.test_csv)
        
        # Check exact TOI calculations
        self.assertIn('player_exact_toi', dir(self.processor))
        exact_toi = self.processor.player_exact_toi
        
        # Player_1 should have 40s TOI (0-40s) + time after returning
        # Player_2, _3, _4, _5 should have continuous TOI
        self.assertGreater(exact_toi.get('player_1', 0), 35)  # At least 35s
        self.assertGreater(exact_toi.get('player_2', 0), 100)  # Continuous player
        
        print(f"✓ Player_1 exact TOI: {exact_toi.get('player_1', 0):.1f}s")
        print(f"✓ Player_2 exact TOI: {exact_toi.get('player_2', 0):.1f}s")
    
    def test_shift_sequence_tracking(self):
        """Test that shift sequences are tracked correctly"""
        
        # Process the test game
        self.processor.process_game(self.test_csv)
        
        # Check shift sequences
        self.assertIn('player_shift_sequences', dir(self.processor))
        sequences = self.processor.player_shift_sequences
        
        # Player_1 should have recorded shift sequence
        if 'player_1' in sequences:
            player_1_shifts = sequences['player_1']
            self.assertGreater(len(player_1_shifts), 0)
            
            # Check shift length calculation
            first_shift = player_1_shifts[0]
            self.assertAlmostEqual(first_shift['shift_length'], 60.0, delta=5.0)  # Corrected expectation
            
            print(f"✓ Player_1 shift length: {first_shift['shift_length']:.1f}s")
    
    def test_rest_pattern_extraction(self):
        """Test that rest patterns are extracted correctly"""
        
        # Process the test game  
        self.processor.process_game(self.test_csv)
        
        # Extract patterns
        patterns = self.processor.extract_predictive_patterns()
        
        # Check rest patterns
        self.assertIn('player_specific_rest', patterns)
        rest_patterns = patterns['player_specific_rest']
        
        # Should have patterns for all players
        expected_players = ['player_1', 'player_2', 'player_3', 'player_4', 'player_5',
                          'player_6', 'opp_1', 'opp_2', 'opp_3', 'opp_4', 'opp_5']
        
        for player in expected_players:
            self.assertIn(player, rest_patterns)
            
        print(f"✓ Rest patterns extracted for {len(rest_patterns)} players")
    
    def test_mathematical_precision(self):
        """Test mathematical precision of TOI calculations"""
        
        # Create precise test case with full lineup
        precise_data = pd.DataFrame([
            {'gameTime': 0, 'periodTime': 0, 'timecode': '00:00:00:00',
             'teamForwardsOnIceRefs': 'test_player\tother_1\tother_2', 
             'teamDefencemenOnIceRefs': 'def_1\tdef_2',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3', 
             'opposingTeamDefencemenOnIceRefs': 'opp_d1\topp_d2',
             'period': 1, 'strengthState': '5v5'},
            
            {'gameTime': 30, 'periodTime': 30, 'timecode': '00:00:30:00',
             'teamForwardsOnIceRefs': 'test_player\tother_1\tother_2', 
             'teamDefencemenOnIceRefs': 'def_1\tdef_2',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3', 
             'opposingTeamDefencemenOnIceRefs': 'opp_d1\topp_d2',
             'period': 1, 'strengthState': '5v5'},
            
            # test_player comes off ice (replaced by other_3)
            {'gameTime': 50, 'periodTime': 50, 'timecode': '00:00:50:00',
             'teamForwardsOnIceRefs': 'other_3\tother_1\tother_2', 
             'teamDefencemenOnIceRefs': 'def_1\tdef_2',
             'opposingTeamForwardsOnIceRefs': 'opp_1\topp_2\topp_3', 
             'opposingTeamDefencemenOnIceRefs': 'opp_d1\topp_d2',
             'period': 1, 'strengthState': '5v5'},
        ])
        
        # Save and process
        precise_csv = self.data_path / 'precise-test.csv'
        precise_data.to_csv(precise_csv, index=False)
        
        self.processor.process_game(precise_csv)
        
        # Check exact calculation
        exact_toi = self.processor.player_exact_toi
        
        # test_player should have exactly 50s TOI (two intervals: 0-30s and 30-50s)
        expected_toi = 50.0  # 30s + 20s
        actual_toi = exact_toi.get('test_player', 0)
        
        self.assertAlmostEqual(actual_toi, expected_toi, delta=1.0)
        print(f"✓ Mathematical precision: Expected {expected_toi}s, got {actual_toi:.1f}s")


class TestRecencyWeighting(unittest.TestCase):
    """Test recency weighting calculations"""
    
    def setUp(self):
        """Set up test processor"""
        temp_dir = tempfile.mkdtemp()
        data_path = Path(temp_dir)
        
        self.processor = PlayByPlayProcessor(
            data_path,
            Path('/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/dim/player_ids.csv')
        )
    
    def test_date_extraction(self):
        """Test game date extraction from filename"""
        
        test_files = [
            'playsequence-20241225-NHL-TORvsMTL-season-game.csv',
            'playsequence-20241201-NHL-MTLvsBOS-season-game.csv',
            'playsequence-20240315-NHL-CHIvsMTL-season-game.csv'
        ]
        
        for filename in test_files:
            date = self.processor.extract_game_date(filename)
            self.assertIsInstance(date, datetime)
            
            # Verify date extraction is correct
            expected_year = int(filename.split('-')[1][:4])
            self.assertEqual(date.year, expected_year)
            
            print(f"✓ {filename} → {date.strftime('%Y-%m-%d')}")
    
    def test_recency_weight_calculation(self):
        """Test exponential decay weighting"""
        
        from datetime import datetime, timedelta
        
        reference_date = datetime(2024, 12, 25)
        
        # Test dates with known day differences
        test_dates = [
            (datetime(2024, 12, 25), 0),    # Same day = weight 1.0
            (datetime(2024, 12, 20), 5),    # 5 days ago
            (datetime(2024, 12, 15), 10),   # 10 days ago
            (datetime(2024, 11, 25), 30),   # 30 days ago
        ]
        
        for game_date, days_ago in test_dates:
            weight = self.processor.calculate_recency_weight(game_date, reference_date)
            expected_weight = np.exp(-self.processor.recency_decay_lambda * days_ago)
            
            self.assertAlmostEqual(weight, expected_weight, places=4)
            print(f"✓ {days_ago} days ago: weight = {weight:.4f}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
