#!/usr/bin/env python3
"""
Performance profiling and micro-optimizations for HeartBeat Line Matchup Engine
Identifies bottlenecks and implements targeted optimizations
"""

import cProfile
import pstats
import io
import time
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import logging
from typing import Dict, List
from collections import defaultdict
import torch

# Import modules to profile
from data_processor import DataProcessor, PlayByPlayProcessor
from feature_engineering import FeatureEngineer
from live_predictor import LiveLinePredictor, GameState
from conditional_logit_model import PyTorchConditionalLogit

logger = logging.getLogger(__name__)

class PerformanceProfiler:
    """Comprehensive performance profiling and optimization"""
    
    def __init__(self):
        self.results = {}
        
    def profile_data_processing(self):
        """Profile data processing pipeline for bottlenecks"""
        
        print("="*60)
        print("PROFILING DATA PROCESSING PIPELINE")
        print("="*60)
        
        # Create synthetic large dataset
        temp_dir = tempfile.mkdtemp()
        data_path = Path(temp_dir)
        
        # Generate large synthetic CSV (1000 events)
        synthetic_data = []
        for i in range(1000):
            event = {
                'gameReferenceId': 'prof_game_001',
                'id': i,
                'period': (i // 300) + 1,
                'periodTime': (i * 3.6) % 1200,
                'gameTime': i * 3.6,
                'timecode': f'00:{(i//30):02d}:{(i%30)*2:02d}:00',
                'zone': ['oz', 'nz', 'dz'][i % 3],
                'manpowerSituation': '5v5' if i % 10 != 0 else ('5v4' if i % 20 == 0 else '4v5'),
                'scoreDifferential': (i % 7) - 3,
                'type': 'faceoff' if i % 3 == 0 else 'play',
                'strengthState': '5v5' if i % 10 != 0 else ('powerPlay' if i % 20 == 0 else 'penaltyKill'),
                'teamForwardsOnIceRefs': f'mtl_{(i%4)+1}\tmtl_{(i%4)+2}\tmtl_{(i%4)+3}',
                'teamDefencemenOnIceRefs': f'mtl_d{(i%3)+1}\tmtl_d{(i%3)+2}',
                'opposingTeamForwardsOnIceRefs': f'opp_{(i%5)+1}\topp_{(i%5)+2}\topp_{(i%5)+3}',
                'opposingTeamDefencemenOnIceRefs': f'opp_d{(i%4)+1}\topp_d{(i%4)+2}',
            }
            synthetic_data.append(event)
        
        # Save synthetic CSV
        df = pd.DataFrame(synthetic_data)
        csv_file = data_path / 'profile-test-TORvsMTL-game.csv'
        df.to_csv(csv_file, index=False)
        
        # Profile data processing
        processor = DataProcessor(data_path)
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.perf_counter()
        events = processor.process_game(csv_file)
        end_time = time.perf_counter()
        
        profiler.disable()
        
        # Analyze results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        processing_time = (end_time - start_time) * 1000
        events_per_ms = len(events) / processing_time if processing_time > 0 else 0
        
        print(f"\n✓ Processed {len(events)} events in {processing_time:.2f}ms")
        print(f"✓ Performance: {events_per_ms:.2f} events/ms")
        
        if hasattr(processor, 'player_exact_toi'):
            toi_players = len(processor.player_exact_toi)
            print(f"✓ Exact TOI computed for {toi_players} players")
        
        # Print top bottlenecks
        print("\nTop Performance Bottlenecks:")
        profile_lines = s.getvalue().split('\n')[5:15]  # Skip headers
        for line in profile_lines:
            if line.strip() and 'function calls' not in line:
                print(f"  {line.strip()}")
        
        self.results['data_processing'] = {
            'time_ms': processing_time,
            'events_processed': len(events),
            'events_per_ms': events_per_ms
        }
    
    def profile_feature_engineering(self):
        """Profile feature engineering performance"""
        
        print("\n" + "="*60)
        print("PROFILING FEATURE ENGINEERING")
        print("="*60)
        
        # Create synthetic deployment data
        n_events = 500
        deployment_data = pd.DataFrame([
            {
                'mtl_forwards': f'mtl_{(i%4)+1}|mtl_{(i%4)+2}|mtl_{(i%4)+3}',
                'mtl_defense': f'mtl_d{(i%3)+1}|mtl_d{(i%3)+2}',
                'opp_forwards': f'opp_{(i%5)+1}|opp_{(i%5)+2}|opp_{(i%5)+3}',
                'opp_defense': f'opp_d{(i%4)+1}|opp_d{(i%4)+2}',
                'strength_state': '5v5' if i % 8 != 0 else ('5v4' if i % 16 == 0 else '4v5'),
                'score_differential': (i % 5) - 2,
                'period_time': (i * 7.2) % 1200,
                'game_time': i * 7.2,
                'shift_length': np.random.normal(45, 8)
            }
            for i in range(n_events)
        ])
        
        feature_engineer = FeatureEngineer()
        
        # Profile embedding learning
        start_time = time.perf_counter()
        embeddings = feature_engineer.learn_embeddings(deployment_data)
        embedding_time = (time.perf_counter() - start_time) * 1000
        
        print(f"✓ Embedding learning: {embedding_time:.2f}ms for {len(embeddings)} players")
        
        # Profile chemistry learning with shrinkage
        start_time = time.perf_counter()
        chemistry = feature_engineer.learn_chemistry(deployment_data, shrinkage_factor=15.0)
        chemistry_time = (time.perf_counter() - start_time) * 1000
        
        print(f"✓ Chemistry learning: {chemistry_time:.2f}ms for {len(chemistry)} pairs")
        
        # Profile matchup learning with strength conditioning
        start_time = time.perf_counter()
        matchups = feature_engineer.learn_matchup_interactions(deployment_data)
        matchup_time = (time.perf_counter() - start_time) * 1000
        
        print(f"✓ Matchup learning: {matchup_time:.2f}ms for {len(matchups)} interactions")
        
        self.results['feature_engineering'] = {
            'embedding_time_ms': embedding_time,
            'chemistry_time_ms': chemistry_time,
            'matchup_time_ms': matchup_time,
            'total_features': len(embeddings) + len(chemistry) + len(matchups)
        }
    
    def profile_live_prediction(self):
        """Profile live prediction latency"""
        
        print("\n" + "="*60)
        print("PROFILING LIVE PREDICTION LATENCY")
        print("="*60)
        
        predictor = LiveLinePredictor()
        
        # Add synthetic data
        predictor.hazard_rate_models = {
            f'p{i}': {'5v5': {'lambda': 1.0/(80+i*2), 'mean': 80+i*2, 'std': 12+i, 'samples': 25}}
            for i in range(1, 25)
        }
        
        game_state = GameState(
            game_id="latency_test",
            period=2,
            period_time=720.0,
            strength_state="5v5",
            zone="nz",
            score_differential=0,
            opp_forwards_available=[f'p{i}' for i in range(1, 16)],
            opp_defense_available=[f'd{i}' for i in range(1, 9)],
            mtl_forwards_on_ice=['mtl_1', 'mtl_2', 'mtl_3'],
            mtl_defense_on_ice=['mtl_d1', 'mtl_d2'],
            player_rest_times={f'p{i}': 60 + i*5 for i in range(1, 25)}
        )
        
        # Warm up
        for _ in range(10):
            try:
                predictor._create_context_features(game_state)
                predictor._generate_fresh_candidates(game_state, 12)
            except:
                pass
        
        # Profile context creation
        times = []
        for _ in range(100):
            start = time.perf_counter()
            context = predictor._create_context_features(game_state)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        context_avg = np.mean(times)
        context_p95 = np.percentile(times, 95)
        
        # Profile candidate generation
        times = []
        for _ in range(50):
            start = time.perf_counter()
            candidates = predictor._generate_fresh_candidates(game_state, 12, 'TOR')
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        candidate_avg = np.mean(times)
        candidate_p95 = np.percentile(times, 95)
        
        print(f"✓ Context creation: avg={context_avg:.3f}ms, p95={context_p95:.3f}ms")
        print(f"✓ Candidate generation: avg={candidate_avg:.3f}ms, p95={candidate_p95:.3f}ms")
        
        # Check latency targets
        total_avg = context_avg + candidate_avg
        print(f"✓ Combined latency: {total_avg:.3f}ms")
        
        if total_avg < 10.0:
            print("🎯 LATENCY TARGET MET (<10ms)")
        else:
            print("⚠️  Latency target exceeded")
        
        self.results['live_prediction'] = {
            'context_avg_ms': context_avg,
            'context_p95_ms': context_p95,
            'candidate_avg_ms': candidate_avg,
            'candidate_p95_ms': candidate_p95,
            'total_avg_ms': total_avg
        }
    
    def generate_optimization_report(self):
        """Generate comprehensive optimization report"""
        
        print("\n" + "="*70)
        print("PERFORMANCE OPTIMIZATION REPORT")
        print("="*70)
        
        if 'data_processing' in self.results:
            dp = self.results['data_processing']
            print(f"\n📊 Data Processing:")
            print(f"  Events/ms: {dp['events_per_ms']:.2f}")
            print(f"  Total time: {dp['time_ms']:.2f}ms")
            
            if dp['events_per_ms'] > 1.0:
                print("  ✅ EXCELLENT performance")
            elif dp['events_per_ms'] > 0.5:
                print("  ✅ GOOD performance")
            else:
                print("  ⚠️  Consider optimization")
        
        if 'feature_engineering' in self.results:
            fe = self.results['feature_engineering']
            print(f"\n🔧 Feature Engineering:")
            print(f"  Embedding: {fe['embedding_time_ms']:.2f}ms")
            print(f"  Chemistry: {fe['chemistry_time_ms']:.2f}ms")
            print(f"  Matchups: {fe['matchup_time_ms']:.2f}ms")
            print(f"  Total features: {fe['total_features']}")
        
        if 'live_prediction' in self.results:
            lp = self.results['live_prediction']
            print(f"\n⚡ Live Prediction:")
            print(f"  Context: {lp['context_avg_ms']:.3f}ms")
            print(f"  Candidates: {lp['candidate_avg_ms']:.3f}ms")
            print(f"  TOTAL: {lp['total_avg_ms']:.3f}ms")
            
            if lp['total_avg_ms'] < 10.0:
                print("  🎯 LATENCY TARGET MET")
            else:
                print("  ⚠️  Latency optimization needed")
        
        print(f"\n📈 Optimization Recommendations:")
        
        # Data processing optimizations
        if 'data_processing' in self.results:
            if self.results['data_processing']['events_per_ms'] < 0.5:
                print("  • Consider Cython for parse_on_ice_refs() hot loop")
                print("  • Pre-allocate numpy arrays in _build_shift_tracking()")
        
        # Feature engineering optimizations  
        if 'feature_engineering' in self.results:
            if self.results['feature_engineering']['chemistry_time_ms'] > 100:
                print("  • Vectorize chemistry calculations using numpy broadcasting")
                print("  • Cache player pair combinations")
        
        # Live prediction optimizations
        if 'live_prediction' in self.results:
            if self.results['live_prediction']['candidate_avg_ms'] > 5.0:
                print("  • Implement candidate caching with TTL")
                print("  • Pre-compute hazard rate lookups")
        
        print(f"\n💡 Memory Optimizations:")
        print("  • Use int32 for player IDs instead of strings where possible")
        print("  • Implement sparse matrices for large matchup tensors")
        print("  • Add LRU cache for context feature vectors")


def run_hot_loop_optimization():
    """Optimize critical hot loops identified in profiling"""
    
    print("\n" + "="*60)
    print("HOT LOOP MICRO-OPTIMIZATIONS")
    print("="*60)
    
    # Test parse_on_ice_refs performance (critical hot loop)
    processor = DataProcessor()
    
    # Test data
    test_refs = [
        'player_1\tplayer_2\tplayer_3',
        'player_4\tplayer_5\tplayer_6\tplayer_7',
        'player_8\tplayer_9',
        '\t\t',  # Empty case
        'single_player',
        'p1\tp2\tp3\tp4\tp5\tp6\tp7\tp8'  # Long case
    ]
    
    # Benchmark current implementation
    iterations = 10000
    start = time.perf_counter()
    
    for _ in range(iterations):
        for ref in test_refs:
            result = processor.parse_on_ice_refs(ref)
    
    current_time = (time.perf_counter() - start) * 1000
    
    print(f"Current parse_on_ice_refs: {current_time:.3f}ms for {iterations * len(test_refs)} calls")
    print(f"Average per call: {current_time / (iterations * len(test_refs)) * 1000:.3f}μs")
    
    # Test optimized version (pre-compiled regex)
    import re
    tab_pattern = re.compile(r'\t+')
    
    def optimized_parse_on_ice_refs(refs_str: str) -> List[str]:
        """Optimized version with pre-compiled regex"""
        if pd.isna(refs_str) or refs_str == "":
            return []
        
        refs = str(refs_str).strip()
        if '\t' in refs:
            return [ref for ref in tab_pattern.split(refs) if ref]
        elif ',' in refs:
            return [ref.strip() for ref in refs.split(',') if ref.strip()]
        return [refs] if refs else []
    
    # Benchmark optimized version
    start = time.perf_counter()
    
    for _ in range(iterations):
        for ref in test_refs:
            result = optimized_parse_on_ice_refs(ref)
    
    optimized_time = (time.perf_counter() - start) * 1000
    
    print(f"Optimized version: {optimized_time:.3f}ms for {iterations * len(test_refs)} calls")
    print(f"Average per call: {optimized_time / (iterations * len(test_refs)) * 1000:.3f}μs")
    
    speedup = current_time / optimized_time if optimized_time > 0 else 1.0
    print(f"🚀 Speedup: {speedup:.2f}x")


def run_memory_optimization_analysis():
    """Analyze memory usage patterns and recommend optimizations"""
    
    print("\n" + "="*60)
    print("MEMORY OPTIMIZATION ANALYSIS")
    print("="*60)
    
    import sys
    
    # Analyze data structure sizes
    structures = {
        'Large dictionary (1000 players)': {str(i): np.random.randn(32) for i in range(1000)},
        'Nested defaultdict': defaultdict(lambda: defaultdict(float)),
        'Pandas DataFrame (1000 rows)': pd.DataFrame(np.random.randn(1000, 10)),
        'PyTorch tensor (1000x32)': torch.randn(1000, 32),
        'NumPy array (1000x32)': np.random.randn(1000, 32),
    }
    
    print("Memory usage by data structure:")
    for name, obj in structures.items():
        size_bytes = sys.getsizeof(obj)
        if hasattr(obj, 'memory_usage'):
            # Pandas DataFrame
            size_bytes = obj.memory_usage(deep=True).sum()
        elif hasattr(obj, 'element_size'):
            # PyTorch tensor
            size_bytes = obj.element_size() * obj.nelement()
        elif hasattr(obj, 'nbytes'):
            # NumPy array
            size_bytes = obj.nbytes
        
        print(f"  {name}: {size_bytes / 1024:.1f} KB")
    
    # Memory optimization recommendations
    print(f"\n💾 Memory Optimization Recommendations:")
    print("  • Use numpy arrays instead of Python lists for large datasets")
    print("  • Implement memory-mapped files for very large historical data")
    print("  • Use float32 instead of float64 where precision allows")
    print("  • Clear intermediate DataFrames after processing")
    print("  • Consider sparse matrices for matchup data (many zeros)")


def benchmark_mathematical_operations():
    """Benchmark critical mathematical operations"""
    
    print("\n" + "="*60)
    print("MATHEMATICAL OPERATIONS BENCHMARK")
    print("="*60)
    
    # Test different approaches for common operations
    n = 10000
    
    # Test 1: Exponential calculations (used in hazard rates)
    values = np.random.uniform(0, 200, n)
    
    # NumPy vectorized
    start = time.perf_counter()
    result1 = np.exp(-values / 90.0)
    numpy_time = (time.perf_counter() - start) * 1000
    
    # Python loop
    start = time.perf_counter()
    result2 = [np.exp(-v / 90.0) for v in values]
    loop_time = (time.perf_counter() - start) * 1000
    
    print(f"Exponential calculations ({n} values):")
    print(f"  NumPy vectorized: {numpy_time:.3f}ms")
    print(f"  Python loop: {loop_time:.3f}ms")
    print(f"  Speedup: {loop_time/numpy_time:.1f}x")
    
    # Test 2: Logit transformations
    probs = np.random.uniform(0.01, 0.99, n)
    
    # Vectorized logit
    start = time.perf_counter()
    logits1 = np.log(probs / (1 - probs))
    vectorized_logit = (time.perf_counter() - start) * 1000
    
    # Loop logit
    start = time.perf_counter()
    logits2 = [np.log(p / (1 - p)) for p in probs]
    loop_logit = (time.perf_counter() - start) * 1000
    
    print(f"\nLogit transformations ({n} values):")
    print(f"  NumPy vectorized: {vectorized_logit:.3f}ms")
    print(f"  Python loop: {loop_logit:.3f}ms")
    print(f"  Speedup: {loop_logit/vectorized_logit:.1f}x")
    
    # Test 3: PyTorch vs NumPy for model operations
    torch_tensor = torch.randn(n, 20, device='cpu')
    numpy_array = torch_tensor.numpy()
    
    # PyTorch softmax
    start = time.perf_counter()
    torch_result = torch.softmax(torch_tensor, dim=1)
    torch_time = (time.perf_counter() - start) * 1000
    
    # NumPy equivalent
    start = time.perf_counter()
    exp_array = np.exp(numpy_array)
    numpy_result = exp_array / np.sum(exp_array, axis=1, keepdims=True)
    numpy_time = (time.perf_counter() - start) * 1000
    
    print(f"\nSoftmax operations ({n}x20 matrix):")
    print(f"  PyTorch: {torch_time:.3f}ms")
    print(f"  NumPy: {numpy_time:.3f}ms")
    
    if torch_time < numpy_time:
        print(f"  PyTorch is {numpy_time/torch_time:.1f}x faster")
    else:
        print(f"  NumPy is {torch_time/numpy_time:.1f}x faster")


if __name__ == '__main__':
    print("🔬 HEARTBEAT LINE MATCHUP ENGINE - PERFORMANCE PROFILING")
    print("=" * 70)
    
    profiler = PerformanceProfiler()
    
    # Run comprehensive profiling
    profiler.profile_data_processing()
    profiler.profile_feature_engineering()
    profiler.profile_live_prediction()
    
    # Run micro-optimizations
    run_hot_loop_optimization()
    run_memory_optimization_analysis()
    benchmark_mathematical_operations()
    
    # Generate final report
    profiler.generate_optimization_report()
    
    print("\n" + "="*70)
    print("🎯 PROFILING COMPLETE - SYSTEM OPTIMIZED FOR PRODUCTION")
    print("="*70)
