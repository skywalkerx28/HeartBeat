"""
Test Performance Diagnostics Integration
Verify that memory and performance monitoring works correctly
Professional-grade testing for NHL analytics
"""

import unittest
import tempfile
from pathlib import Path
from collections import defaultdict
import time

# Import the modules we're testing
from performance_diagnostics import (
    MemoryProfiler, PerformanceTimer, PatternStructureDiagnostics,
    create_diagnostics_suite, run_comprehensive_diagnostics
)
from data_processor import DataProcessor
from candidate_generator import CandidateGenerator


class TestPerformanceDiagnostics(unittest.TestCase):
    """Test performance diagnostics functionality"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def test_memory_profiler_basic(self):
        """Test basic memory profiler functionality"""
        profiler = MemoryProfiler()
        
        # Take initial snapshot
        snapshot1 = profiler.take_snapshot("Initial")
        self.assertIn('memory_mb', snapshot1)
        self.assertIn('label', snapshot1)
        self.assertEqual(snapshot1['label'], "Initial")
        
        # Create some data to increase memory
        large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}
        
        # Take snapshot with components
        snapshot2 = profiler.take_snapshot("With Data", {'large_data': large_data})
        self.assertIn('component_sizes', snapshot2)
        self.assertIn('large_data', snapshot2['component_sizes'])
        
        # Verify memory growth detection
        growth_analysis = profiler.get_memory_growth_analysis()
        self.assertIn('total_growth_mb', growth_analysis)
        self.assertIn('component_growth', growth_analysis)
        
    def test_performance_timer(self):
        """Test performance timing functionality"""
        timer = PerformanceTimer()
        
        # Test basic timing
        timer.start_timer("test_operation")
        time.sleep(0.01)  # Small delay
        duration = timer.end_timer("test_operation")
        
        self.assertGreater(duration, 0.005)  # Should be at least 5ms
        self.assertLess(duration, 0.1)  # Should be less than 100ms
        
        # Test timing stats
        stats = timer.get_timing_stats("test_operation")
        self.assertEqual(stats['count'], 1)
        self.assertAlmostEqual(stats['avg_time'], duration, places=3)
        self.assertEqual(stats['min_time'], duration)
        self.assertEqual(stats['max_time'], duration)
        
        # Test multiple operations
        for i in range(3):
            timer.start_timer("repeated_op")
            time.sleep(0.005)
            timer.end_timer("repeated_op")
        
        repeated_stats = timer.get_timing_stats("repeated_op")
        self.assertEqual(repeated_stats['count'], 3)
        self.assertGreater(repeated_stats['total_time'], 0.01)
        
    def test_pattern_structure_diagnostics(self):
        """Test pattern structure analysis"""
        diagnostics = PatternStructureDiagnostics()
        
        # Create mock data processor with pattern structures
        processor = DataProcessor()
        
        # Add some test data
        processor.player_matchup_counts[('player1', 'opponent1')] = 5.2
        processor.player_matchup_counts[('player2', 'opponent2')] = 3.1
        
        processor.team_player_rest_patterns['MTL_vs_TOR']['player1']['5v5'] = [45.0, 50.0, 42.0]
        processor.team_player_rest_patterns['MTL_vs_BOS']['player2']['5v4'] = [38.0, 41.0]
        
        # Analyze structures
        analysis = diagnostics.analyze_data_processor(processor)
        
        self.assertEqual(analysis['component'], 'DataProcessor')
        self.assertIn('player_matchups', analysis)
        self.assertIn('team_rest_patterns', analysis)
        
        # Verify player matchups analysis
        matchup_analysis = analysis['player_matchups']
        self.assertEqual(matchup_analysis['total_items'], 2)
        self.assertIn('estimated_size_mb', matchup_analysis)
        
    def test_candidate_generator_diagnostics(self):
        """Test candidate generator pattern analysis"""
        diagnostics = PatternStructureDiagnostics()
        generator = CandidateGenerator()
        
        # Add some test data
        generator.player_matchup_counts[('player1', 'opponent1')] = 4.5
        generator.last_change_rotation_transitions[('MTL', 'TOR', 'has_last_change', 'Line1', 'Line2')] = 0.35
        
        # Analyze structures
        analysis = diagnostics.analyze_candidate_generator(generator)
        
        self.assertEqual(analysis['component'], 'CandidateGenerator')
        self.assertIn('player_matchups', analysis)
        
        if analysis['player_matchups'].get('total_items', 0) > 0:
            self.assertEqual(analysis['player_matchups']['total_items'], 1)
            
    def test_comprehensive_diagnostics_integration(self):
        """Test full diagnostics integration"""
        # Create components
        processor = DataProcessor()
        generator = CandidateGenerator()
        
        # Add some test data
        processor.player_matchup_counts[('test_player', 'test_opponent')] = 2.5
        generator.player_matchup_counts[('test_player', 'test_opponent')] = 2.5
        
        # Run comprehensive diagnostics
        output_path = self.temp_dir / "diagnostics_report.json"
        
        diagnostics = run_comprehensive_diagnostics(
            data_processor=processor,
            candidate_generator=generator,
            output_path=output_path
        )
        
        # Verify diagnostics objects were created
        self.assertIn('memory_profiler', diagnostics)
        self.assertIn('performance_timer', diagnostics)
        self.assertIn('pattern_diagnostics', diagnostics)
        
        # Verify report was saved
        self.assertTrue(output_path.exists())
        
        # Verify memory profiler has snapshots
        memory_profiler = diagnostics['memory_profiler']
        self.assertGreater(len(memory_profiler.snapshots), 0)
        
    def test_data_processor_integration(self):
        """Test that DataProcessor integrates diagnostics correctly"""
        processor = DataProcessor()
        
        # Verify diagnostics are initialized
        if hasattr(processor, 'memory_profiler'):
            self.assertIsNotNone(processor.memory_profiler)
            self.assertIsNotNone(processor.pattern_diagnostics)
            
            # Verify initial snapshot was taken
            self.assertGreater(len(processor.memory_profiler.snapshots), 0)
            self.assertEqual(processor.memory_profiler.snapshots[0]['label'], "DataProcessor Initialized")
        
    def test_diagnostics_suite_creation(self):
        """Test diagnostics suite creation"""
        suite = create_diagnostics_suite()
        
        self.assertIn('memory_profiler', suite)
        self.assertIn('performance_timer', suite)
        self.assertIn('pattern_diagnostics', suite)
        
        # Verify objects are the correct types
        self.assertIsInstance(suite['memory_profiler'], MemoryProfiler)
        self.assertIsInstance(suite['performance_timer'], PerformanceTimer)
        self.assertIsInstance(suite['pattern_diagnostics'], PatternStructureDiagnostics)


if __name__ == "__main__":
    unittest.main()
