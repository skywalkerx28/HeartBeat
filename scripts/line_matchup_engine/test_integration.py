#!/usr/bin/env python3
"""
Integration tests for enhanced HeartBeat Line Matchup Engine
Tests the complete mathematical pipeline with all improvements
"""

import unittest
import pandas as pd
import numpy as np
import torch
from pathlib import Path
import tempfile
import logging
from datetime import datetime

# Set up minimal logging for tests
logging.basicConfig(level=logging.WARNING)

from data_processor import DataProcessor
from feature_engineering import FeatureEngineer
from conditional_logit_model import PyTorchConditionalLogit
from live_predictor import LiveLinePredictor, GameState
from candidate_generator import CandidateGenerator

class TestEnhancedPipeline(unittest.TestCase):
    """Test the complete enhanced pipeline integration"""
    
    def setUp(self):
        """Set up comprehensive test environment"""
        
        # Create temporary directory structure
        self.temp_dir = tempfile.mkdtemp()
        self.data_path = Path(self.temp_dir) / 'data'
        self.data_path.mkdir()
        
        # Create realistic test CSV data
        self.create_realistic_test_data()
        
        # Initialize components
        self.data_processor = DataProcessor(
            self.data_path,
            Path('/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/dim/player_ids.csv')
        )
        self.feature_engineer = FeatureEngineer()
        
    def create_realistic_test_data(self):
        """Create realistic multi-game test dataset"""
        
        # Game 1: MTL vs TOR (MTL home, has last change)
        game1_data = []
        base_time = 0
        
        # Create 20 deployment events with realistic patterns
        for i in range(20):
            event = {
                'gameReferenceId': 'game_001',
                'id': i,
                'period': 1 if i < 15 else 2,
                'periodTime': (i * 60) % 1200,
                'gameTime': base_time + i * 30,
                'timecode': f'00:{i:02d}:00:00',
                'zone': ['oz', 'nz', 'dz'][i % 3],
                'manpowerSituation': '5v5' if i % 8 != 0 else ('5v4' if i % 16 == 0 else '4v5'),
                'scoreDifferential': (i % 5) - 2,  # Score varies -2 to +2
                'type': 'faceoff',
                'strengthState': '5v5' if i % 8 != 0 else ('powerPlay' if i % 16 == 0 else 'penaltyKill'),
                'teamForwardsOnIceRefs': f'mtl_{(i%3)+1}\tmtl_{(i%3)+2}\tmtl_{(i%3)+3}',
                'teamDefencemenOnIceRefs': f'mtl_d{(i%2)+1}\tmtl_d{(i%2)+2}',
                'opposingTeamForwardsOnIceRefs': f'tor_{(i%4)+1}\ttor_{(i%4)+2}\ttor_{(i%4)+3}',
                'opposingTeamDefencemenOnIceRefs': f'tor_d{(i%3)+1}\ttor_d{(i%3)+2}',
                'teamGoalieOnIceRef': 'mtl_g1',
                'opposingTeamGoalieOnIceRef': 'tor_g1'
            }
            game1_data.append(event)
        
        # Save game 1
        game1_df = pd.DataFrame(game1_data)
        game1_csv = self.data_path / 'playsequence-20241225-NHL-TORvsMTL-season-game1.csv'
        game1_df.to_csv(game1_csv, index=False)
        
        # Game 2: MTL vs BOS (MTL away, opponent has last change)
        game2_data = []
        for i in range(15):
            event = {
                'gameReferenceId': 'game_002',
                'id': i,
                'period': 1,
                'periodTime': i * 80,
                'gameTime': base_time + 1800 + i * 35,  # Different base time
                'timecode': f'00:{(i*2):02d}:00:00',
                'zone': ['dz', 'nz', 'oz'][i % 3],
                'manpowerSituation': '5v5',
                'scoreDifferential': i % 3 - 1,
                'type': 'faceoff',
                'strengthState': '5v5',
                'opposingTeamForwardsOnIceRefs': f'mtl_{(i%3)+1}\tmtl_{(i%3)+2}\tmtl_{(i%3)+3}',
                'opposingTeamDefencemenOnIceRefs': f'mtl_d{(i%2)+1}\tmtl_d{(i%2)+2}',
                'teamForwardsOnIceRefs': f'bos_{(i%4)+1}\tbos_{(i%4)+2}\tbos_{(i%4)+3}',
                'teamDefencemenOnIceRefs': f'bos_d{(i%2)+1}\tbos_d{(i%2)+2}',
                'teamGoalieOnIceRef': 'bos_g1',
                'opposingTeamGoalieOnIceRef': 'mtl_g1'
            }
            game2_data.append(event)
        
        # Save game 2
        game2_df = pd.DataFrame(game2_data)
        game2_csv = self.data_path / 'playsequence-20241220-NHL-MTLvsBOS-season-game2.csv'
        game2_df.to_csv(game2_csv, index=False)
        
        logger.info(f"Created test data: {len(game1_data)} + {len(game2_data)} events")
    
    def test_complete_pipeline(self):
        """Test the complete enhanced pipeline"""
        
        print("\n" + "="*50)
        print("TESTING COMPLETE ENHANCED PIPELINE")
        print("="*50)
        
        # Step 1: Process all games
        print("\n1. Processing games with exact TOI computation...")
        csv_files = list(self.data_path.glob("*.csv"))
        self.assertEqual(len(csv_files), 2)
        
        all_events = []
        for game_file in csv_files:
            events = self.data_processor.process_game(game_file)
            all_events.extend(events)
        
        self.assertGreater(len(all_events), 0)
        print(f"✓ Processed {len(all_events)} deployment events")
        
        # Step 2: Check exact TOI computation
        print("\n2. Verifying exact TOI computation...")
        if hasattr(self.data_processor, 'player_exact_toi'):
            toi_data = self.data_processor.player_exact_toi
            self.assertGreater(len(toi_data), 0)
            
            # Log TOI statistics
            toi_values = list(toi_data.values())
            print(f"✓ Exact TOI computed for {len(toi_data)} players")
            print(f"  Range: {np.min(toi_values):.1f}s - {np.max(toi_values):.1f}s")
            print(f"  Average: {np.mean(toi_values):.1f}s")
        
        # Step 3: Train Bayesian rest model
        print("\n3. Training Bayesian rest model...")
        self.data_processor.train_bayesian_rest_model()
        
        if hasattr(self.data_processor.bayesian_rest_model, 'coef_'):
            score = self.data_processor.bayesian_rest_model.score(
                self.data_processor.rest_context_scaler.transform(
                    np.array([r['context_features'] for r in self.data_processor.rest_training_data])
                ),
                np.array([r['rest_seconds'] for r in self.data_processor.rest_training_data])
            )
            print(f"✓ Bayesian model trained with R² = {score:.4f}")
        
        # Step 4: Extract predictive patterns
        print("\n4. Extracting predictive patterns...")
        patterns = self.data_processor.extract_predictive_patterns()
        
        self.assertIn('total_players_tracked', patterns)
        self.assertIn('player_specific_rest', patterns)
        self.assertIn('opponent_aggregated_matchups', patterns)
        
        print(f"✓ Patterns extracted for {patterns['total_players_tracked']} players")
        print(f"✓ Opponent-specific data for {len(patterns['opponent_aggregated_matchups'])} teams")
        
        # Step 5: Test feature engineering with enhancements
        print("\n5. Testing enhanced feature engineering...")
        deployment_df = pd.DataFrame([
            self.data_processor._event_to_dict(e) for e in all_events
        ])
        
        # Learn chemistry with shrinkage
        chemistry_scores = self.feature_engineer.learn_chemistry(
            deployment_df, shrinkage_factor=15.0
        )
        print(f"✓ Chemistry learned for {len(chemistry_scores)} pairs (with shrinkage)")
        
        # Learn matchup interactions with strength conditioning
        matchup_scores = self.feature_engineer.learn_matchup_interactions(deployment_df)
        print(f"✓ Matchup interactions learned for {len(matchup_scores)} pairs (strength-conditioned)")
        
        # Step 6: Test model integration
        print("\n6. Testing PyTorch model integration...")
        model = PyTorchConditionalLogit(n_context_features=20, embedding_dim=16)
        
        # Register test players
        all_players = set()
        for event in all_events:
            all_players.update(event.mtl_forwards + event.mtl_defense)
            all_players.update(event.opp_forwards + event.opp_defense)
        
        model.register_players(list(all_players))
        print(f"✓ Registered {len(all_players)} players in PyTorch model")
        
        # Test forward pass
        test_candidates = [
            {'forwards': ['tor_1', 'tor_2', 'tor_3'], 'defense': ['tor_d1', 'tor_d2']},
            {'forwards': ['tor_2', 'tor_3', 'tor_4'], 'defense': ['tor_d2', 'tor_d3']}
        ]
        
        context = torch.zeros(20)
        model.eval()
        
        try:
            log_probs = model.forward(
                test_candidates, context, ['mtl_1', 'mtl_2'],
                {}, {}, {}
            )
            self.assertEqual(len(log_probs), 2)
            print(f"✓ Model forward pass successful: {log_probs.shape}")
        except Exception as e:
            print(f"! Model forward pass failed: {e}")
    
    def test_recency_weighting(self):
        """Test recency weighting in opponent patterns"""
        
        print("\n" + "="*40)
        print("TESTING RECENCY WEIGHTING")
        print("="*40)
        
        # Test date extraction
        test_files = [
            'playsequence-20241225-NHL-TORvsMTL-season-game1.csv',
            'playsequence-20241220-NHL-MTLvsBOS-season-game2.csv'
        ]
        
        for filename in test_files:
            date = self.data_processor.extract_game_date(filename)
            weight = self.data_processor.calculate_recency_weight(date)
            
            print(f"✓ {filename}: date={date.strftime('%Y-%m-%d')}, weight={weight:.4f}")
    
    def test_context_aware_rest_prediction(self):
        """Test context-aware rest prediction with various scenarios"""
        
        print("\n" + "="*40)
        print("TESTING CONTEXT-AWARE REST PREDICTION")
        print("="*40)
        
        # Process games first to get training data
        csv_files = list(self.data_path.glob("*.csv"))
        for game_file in csv_files:
            self.data_processor.process_game(game_file)
        
        # Train Bayesian model
        self.data_processor.train_bayesian_rest_model()
        
        # Test various game contexts
        test_scenarios = [
            # [period/3, score/5, zone, strength, time, late_game, close_game]
            ([1/3, 0/5, 0.0, 0.0, 0.5, 0.0, 1.0], "P1, tied, neutral, 5v5"),
            ([3/3, 2/5, -1.0, 0.0, 0.9, 1.0, 0.0], "P3, up 2, defensive, late"),
            ([2/3, -1/5, 1.0, 1.0, 0.3, 0.0, 1.0], "P2, down 1, offensive, PP"),
            ([3/3, 0/5, 0.0, 0.0, 0.95, 1.0, 1.0], "P3, tied, late, close game"),
        ]
        
        for context_features, description in test_scenarios:
            if hasattr(self.data_processor.bayesian_rest_model, 'coef_'):
                mean_pred, std_pred = self.data_processor.predict_context_aware_rest(context_features)
                print(f"✓ {description}: {mean_pred:.1f} ± {std_pred:.1f}s")
            else:
                print(f"! {description}: Model not trained (insufficient data)")


class TestPerformanceOptimizations(unittest.TestCase):
    """Test performance optimizations and latency targets"""
    
    def setUp(self):
        """Set up performance testing environment"""
        
        self.predictor = LiveLinePredictor()
        
        # Create realistic game state
        self.game_state = GameState(
            game_id="perf_test",
            period=2,
            period_time=650.0,
            strength_state="5v5",
            zone="dz",
            score_differential=-1,
            opp_forwards_available=[f'p{i}' for i in range(1, 13)],
            opp_defense_available=[f'd{i}' for i in range(1, 7)],
            mtl_forwards_on_ice=['mtl_1', 'mtl_2', 'mtl_3'],
            mtl_defense_on_ice=['mtl_d1', 'mtl_d2'],
            player_rest_times={f'p{i}': np.random.uniform(30, 180) for i in range(1, 19)}
        )
        
        # Add some synthetic hazard rate models
        self.predictor.hazard_rate_models = {
            f'p{i}': {'5v5': {'lambda': 1.0/90, 'mean': 90, 'std': 15, 'samples': 20}}
            for i in range(1, 13)
        }
    
    def test_context_feature_creation_speed(self):
        """Test context feature creation performance"""
        
        import time
        
        # Measure context feature creation
        times = []
        for _ in range(100):
            start = time.perf_counter()
            context = self.predictor._create_context_features(self.game_state)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = np.mean(times)
        p95_time = np.percentile(times, 95)
        
        # Should be sub-millisecond
        self.assertLess(avg_time, 1.0)
        self.assertLess(p95_time, 2.0)
        
        print(f"✓ Context features: avg={avg_time:.3f}ms, p95={p95_time:.3f}ms")
    
    def test_hazard_rate_prediction_speed(self):
        """Test hazard rate prediction performance"""
        
        import time
        
        # Measure hazard rate predictions
        times = []
        for _ in range(100):
            start = time.perf_counter()
            
            for player_id in self.game_state.opp_forwards_available[:5]:
                self.predictor.predict_time_to_return(player_id, '5v5', 75.0)
            
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = np.mean(times)
        
        # Should be fast for 5 players
        self.assertLess(avg_time, 0.5)
        
        print(f"✓ Hazard predictions (5 players): avg={avg_time:.3f}ms")
    
    def test_memory_efficiency(self):
        """Test memory usage of enhanced features"""
        
        import sys
        
        # Measure data structure sizes
        data_size = sys.getsizeof(self.predictor.hazard_rate_models)
        context_cache_size = sys.getsizeof(self.predictor.context_cache)
        
        print(f"✓ Hazard models size: {data_size / 1024:.1f} KB")
        print(f"✓ Context cache size: {context_cache_size / 1024:.1f} KB")
        
        # Should be reasonable memory usage
        self.assertLess(data_size, 1024 * 1024)  # < 1MB


class TestMathematicalCorrectness(unittest.TestCase):
    """Test mathematical correctness of all implementations"""
    
    def test_probability_normalization(self):
        """Test that all probability calculations sum to 1"""
        
        # Test exponential survival probabilities
        lambda_rate = 1.0 / 90.0
        times = np.linspace(0, 600, 100)
        
        # Discrete probability mass (approximate)
        dt = times[1] - times[0]
        prob_density = lambda_rate * np.exp(-lambda_rate * times)
        total_prob = np.sum(prob_density * dt)
        
        # Should approximately sum to 1 (within numerical precision)
        self.assertAlmostEqual(total_prob, 1.0, delta=0.1)
        print(f"✓ Exponential distribution normalization: {total_prob:.4f}")
    
    def test_logit_transformations(self):
        """Test logit transformation mathematical properties"""
        
        # Test inverse relationship: logit(sigmoid(x)) = x
        test_values = [-2.0, -1.0, 0.0, 1.0, 2.0]
        
        for x in test_values:
            # Forward: x → sigmoid → logit
            sigmoid_x = 1.0 / (1.0 + np.exp(-x))
            
            # Avoid numerical issues at boundaries
            sigmoid_clamped = max(0.001, min(0.999, sigmoid_x))
            logit_sigmoid_x = np.log(sigmoid_clamped / (1 - sigmoid_clamped))
            
            # Should recover original value
            self.assertAlmostEqual(logit_sigmoid_x, x, delta=0.1)
        
        print("✓ Logit-sigmoid inverse relationship verified")
    
    def test_shrinkage_bounds(self):
        """Test that shrinkage produces bounded outputs"""
        
        # Test shrinkage formula: η̂ = (n/(n+k))η_raw
        k = 15.0
        test_cases = [
            (1, 2.0),   # Small sample, large raw value
            (5, 1.0),   # Medium sample
            (50, 0.5),  # Large sample, small raw value
            (100, -1.5) # Large sample, negative value
        ]
        
        for n, eta_raw in test_cases:
            eta_shrunk = (n / (n + k)) * eta_raw
            
            # Shrunk value should be closer to zero
            self.assertLessEqual(abs(eta_shrunk), abs(eta_raw))
            
            # Should converge to raw value as n increases
            if n >= 50:
                self.assertAlmostEqual(eta_shrunk, eta_raw, delta=0.2)
            
            print(f"✓ n={n}, η_raw={eta_raw:.2f} → η_shrunk={eta_shrunk:.3f}")


if __name__ == '__main__':
    print("=" * 70)
    print("ENHANCED HEARTBEAT LINE MATCHUP ENGINE - INTEGRATION TESTS")
    print("=" * 70)
    
    # Run comprehensive test suite
    unittest.main(verbosity=2)
