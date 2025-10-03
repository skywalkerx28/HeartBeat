"""
Test Matchup Prior Logging Integration
Verify that matchup priors are properly logged and analyzed
"""

import unittest
import tempfile
from pathlib import Path
from collections import defaultdict

# Import the modules we're testing
from candidate_generator import CandidateGenerator, Candidate
from evaluation_metrics import EvaluationMetricsHelper, MatchupPriorMetrics


class TestMatchupPriorLogging(unittest.TestCase):
    """Test matchup prior logging and analysis"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.generator = CandidateGenerator()
        self.eval_metrics = EvaluationMetricsHelper(self.temp_dir)
        
        # Set up some mock matchup data
        self.generator.player_matchup_counts = defaultdict(float)
        self.generator.player_matchup_counts[('8480018', '8479318')] = 2.5  # High familiarity
        self.generator.player_matchup_counts[('8481540', '8478483')] = 1.2  # Medium familiarity
        self.generator.enable_matchup_priors = True
        self.generator.matchup_prior_weight = 0.15
    
    def test_matchup_metrics_initialization(self):
        """Test that matchup metrics are properly initialized"""
        self.assertIsInstance(self.eval_metrics.matchup_metrics, MatchupPriorMetrics)
        self.assertEqual(len(self.eval_metrics.matchup_metrics.matchup_stats), 0)
    
    def test_matchup_prior_update(self):
        """Test updating matchup prior statistics"""
        # Update some matchup priors
        self.eval_metrics.update_matchup_prior("TOR", "5v5", 0.25, "candidate_1")
        self.eval_metrics.update_matchup_prior("TOR", "5v5", 0.15, "candidate_2")
        self.eval_metrics.update_matchup_prior("BOS", "5v4", 0.0, "candidate_3")  # Zero prior
        
        # Check that stats were updated
        summary = self.eval_metrics.matchup_metrics.get_summary()
        
        # Overall stats
        self.assertEqual(summary['overall']['total_evaluations'], 3)
        self.assertAlmostEqual(summary['overall']['non_zero_rate'], 2/3, places=2)
        
        # By opponent stats
        self.assertIn("TOR", summary['by_opponent'])
        self.assertEqual(summary['by_opponent']['TOR']['total_count'], 2)
        self.assertAlmostEqual(summary['by_opponent']['TOR']['avg_prior'], 0.2, places=2)
        
        # By strength stats
        self.assertIn("5v5", summary['by_strength'])
        self.assertEqual(summary['by_strength']['5v5']['count'], 2)
    
    def test_candidate_generator_logging_integration(self):
        """Test that candidate generator can log matchup priors"""
        # Create mock candidates with matchup priors
        candidates = [
            Candidate(
                forwards=["8480018", "8481540", "8483515"],
                defense=["8476875", "8482087"],
                probability_prior=1.0,
                matchup_prior=0.25
            ),
            Candidate(
                forwards=["8479318", "8478483", "8482720"],
                defense=["8475690", "8476853"],
                probability_prior=0.8,
                matchup_prior=0.15
            ),
            Candidate(
                forwards=["8477934", "8478402", "8479344"],
                defense=["8476312", "8477949"],
                probability_prior=0.6,
                matchup_prior=0.0  # No matchup familiarity
            )
        ]
        
        # Log matchup priors through candidate generator
        self.generator.log_matchup_priors_to_metrics(
            candidates=candidates,
            opponent_team="TOR",
            strength="5v5",
            eval_metrics_helper=self.eval_metrics
        )
        
        # Verify that priors were logged
        summary = self.eval_metrics.matchup_metrics.get_summary()
        self.assertEqual(summary['overall']['total_evaluations'], 3)
        self.assertAlmostEqual(summary['overall']['non_zero_rate'], 2/3, places=2)
        
        # Check candidate influence tracking
        influence_data = self.eval_metrics.matchup_metrics.candidate_matchup_influence
        self.assertEqual(len(influence_data), 3)
        
        # Verify specific candidate data
        candidate_priors = [data['prior'] for data in influence_data]
        self.assertIn(0.25, candidate_priors)
        self.assertIn(0.15, candidate_priors)
        self.assertIn(0.0, candidate_priors)
    
    def test_comprehensive_analysis_logging(self):
        """Test comprehensive matchup prior analysis across multiple scenarios"""
        # Simulate various matchup scenarios
        test_data = [
            ("TOR", "5v5", 0.25), ("TOR", "5v5", 0.30), ("TOR", "5v5", 0.0),
            ("TOR", "5v4", 0.15), ("TOR", "5v4", 0.20),
            ("BOS", "5v5", 0.10), ("BOS", "5v5", 0.35), ("BOS", "5v5", 0.0),
            ("BOS", "4v5", 0.0), ("BOS", "4v5", 0.05),
            ("NYR", "5v5", 0.40), ("NYR", "5v5", 0.0)
        ]
        
        for opponent, strength, prior in test_data:
            candidate_id = f"test_candidate_{opponent}_{strength}_{prior}"
            self.eval_metrics.update_matchup_prior(opponent, strength, prior, candidate_id)
        
        # Get comprehensive analysis
        summary = self.eval_metrics.matchup_metrics.get_summary()
        
        # Verify overall statistics
        self.assertEqual(summary['overall']['total_evaluations'], 12)
        non_zero_count = sum(1 for _, _, prior in test_data if abs(prior) > 0.001)
        expected_non_zero_rate = non_zero_count / 12
        self.assertAlmostEqual(summary['overall']['non_zero_rate'], expected_non_zero_rate, places=2)
        
        # Verify by-opponent breakdown
        self.assertEqual(len(summary['by_opponent']), 3)  # TOR, BOS, NYR
        self.assertIn("TOR", summary['by_opponent'])
        self.assertIn("BOS", summary['by_opponent'])
        self.assertIn("NYR", summary['by_opponent'])
        
        # Verify by-strength breakdown
        expected_strengths = {"5v5", "5v4", "4v5"}
        for strength in expected_strengths:
            self.assertIn(strength, summary['by_strength'])
        
        # Verify TOR has the most evaluations (5 total)
        self.assertEqual(summary['by_opponent']['TOR']['total_count'], 5)
        
        # Verify 5v5 has the most evaluations across all opponents
        self.assertEqual(summary['by_strength']['5v5']['count'], 8)  # TOR:3 + BOS:3 + NYR:2 = 8
    
    def test_csv_export_functionality(self):
        """Test CSV export of matchup prior analysis"""
        # Add some test data
        test_data = [
            ("TOR", "5v5", 0.25, "candidate_A"),
            ("TOR", "5v5", 0.15, "candidate_B"),
            ("BOS", "5v4", 0.30, "candidate_C")
        ]
        
        for opponent, strength, prior, candidate_id in test_data:
            self.eval_metrics.update_matchup_prior(opponent, strength, prior, candidate_id)
        
        # Export to CSV
        self.eval_metrics.matchup_metrics.save_detailed_csv(self.temp_dir, "test")
        
        # Verify files were created
        detail_csv = self.temp_dir / "matchup_prior_analysis_test.csv"
        summary_csv = self.temp_dir / "matchup_prior_summary_test.csv"
        
        self.assertTrue(detail_csv.exists())
        self.assertTrue(summary_csv.exists())
        
        # Verify CSV contents
        import pandas as pd
        detail_df = pd.read_csv(detail_csv)
        self.assertEqual(len(detail_df), 3)
        self.assertIn('opponent', detail_df.columns)
        self.assertIn('strength', detail_df.columns)
        self.assertIn('prior', detail_df.columns)
        self.assertIn('candidate', detail_df.columns)
        
        summary_df = pd.read_csv(summary_csv)
        self.assertEqual(len(summary_df), 4)  # 4 summary metrics
        self.assertIn('metric', summary_df.columns)
        self.assertIn('value', summary_df.columns)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    unittest.main()
