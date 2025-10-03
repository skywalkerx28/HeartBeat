"""
HeartBeat Performance and Memory Diagnostics
Comprehensive monitoring for rotation/rest pattern structures and system performance
Professional-grade diagnostics for NHL analytics production deployment
"""

import logging
import psutil
import gc
import sys
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class MemoryProfiler:
    """
    Memory profiling for HeartBeat components
    Tracks memory usage of pattern structures and identifies potential leaks
    """
    
    def __init__(self):
        self.snapshots = []
        self.component_sizes = defaultdict(list)
        self.peak_memory = 0
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
    def take_snapshot(self, label: str, components: Dict[str, Any] = None):
        """Take a memory snapshot with optional component size analysis"""
        process = psutil.Process()
        memory_info = process.memory_info()
        current_memory = memory_info.rss / 1024 / 1024  # MB
        
        snapshot = {
            'timestamp': time.time(),
            'label': label,
            'memory_mb': current_memory,
            'memory_percent': process.memory_percent(),
            'cpu_percent': process.cpu_percent(),
            'gc_count': len(gc.get_objects())
        }
        
        # Analyze component sizes if provided
        if components:
            component_analysis = {}
            for name, component in components.items():
                size_info = self._analyze_component_size(component)
                component_analysis[name] = size_info
                self.component_sizes[name].append(size_info)
            
            snapshot['component_sizes'] = component_analysis
        
        self.snapshots.append(snapshot)
        self.peak_memory = max(self.peak_memory, current_memory)
        
        logger.info(f"Memory snapshot [{label}]: {current_memory:.1f}MB "
                   f"({current_memory - self.start_memory:+.1f}MB from start)")
        
        return snapshot
    
    def _analyze_component_size(self, component) -> Dict[str, Any]:
        """Analyze the memory footprint of a component"""
        try:
            if hasattr(component, '__len__'):
                item_count = len(component)
            else:
                item_count = 1
            
            # Estimate size using sys.getsizeof recursively
            total_size = self._get_deep_size(component)
            
            return {
                'item_count': item_count,
                'size_bytes': total_size,
                'size_mb': total_size / 1024 / 1024,
                'avg_item_size': total_size / max(item_count, 1)
            }
        except Exception as e:
            logger.warning(f"Failed to analyze component size: {e}")
            return {'error': str(e)}
    
    def _get_deep_size(self, obj, seen=None) -> int:
        """Calculate deep size of an object including nested structures"""
        if seen is None:
            seen = set()
        
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        
        seen.add(obj_id)
        size = sys.getsizeof(obj)
        
        if isinstance(obj, dict):
            size += sum([self._get_deep_size(v, seen) for v in obj.values()])
            size += sum([self._get_deep_size(k, seen) for k in obj.keys()])
        elif hasattr(obj, '__dict__'):
            size += self._get_deep_size(obj.__dict__, seen)
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
            try:
                size += sum([self._get_deep_size(i, seen) for i in obj])
            except:
                pass
        
        return size
    
    def get_memory_growth_analysis(self) -> Dict[str, Any]:
        """Analyze memory growth patterns"""
        if len(self.snapshots) < 2:
            return {'error': 'Need at least 2 snapshots for growth analysis'}
        
        start_memory = self.snapshots[0]['memory_mb']
        end_memory = self.snapshots[-1]['memory_mb']
        growth = end_memory - start_memory
        
        # Component growth analysis
        component_growth = {}
        for component_name, sizes in self.component_sizes.items():
            if len(sizes) >= 2:
                start_size = sizes[0]['size_mb']
                end_size = sizes[-1]['size_mb']
                component_growth[component_name] = {
                    'start_mb': start_size,
                    'end_mb': end_size,
                    'growth_mb': end_size - start_size,
                    'growth_percent': ((end_size - start_size) / max(start_size, 0.001)) * 100
                }
        
        return {
            'total_growth_mb': growth,
            'peak_memory_mb': self.peak_memory,
            'growth_percent': (growth / max(start_memory, 0.001)) * 100,
            'component_growth': component_growth,
            'snapshots_count': len(self.snapshots)
        }
    
    def log_summary(self):
        """Log comprehensive memory usage summary"""
        growth_analysis = self.get_memory_growth_analysis()
        
        logger.info("MEMORY USAGE SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Peak Memory: {self.peak_memory:.1f}MB")
        logger.info(f"Total Growth: {growth_analysis.get('total_growth_mb', 0):+.1f}MB "
                   f"({growth_analysis.get('growth_percent', 0):+.1f}%)")
        
        if 'component_growth' in growth_analysis:
            logger.info("\nComponent Memory Growth:")
            for comp, growth in growth_analysis['component_growth'].items():
                logger.info(f"  {comp}: {growth['start_mb']:.1f}MB → {growth['end_mb']:.1f}MB "
                           f"({growth['growth_mb']:+.1f}MB, {growth['growth_percent']:+.1f}%)")


class PerformanceTimer:
    """
    Performance timing for HeartBeat operations
    Tracks execution times and identifies bottlenecks
    """
    
    def __init__(self):
        self.timings = defaultdict(list)
        self.active_timers = {}
        
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.active_timers[operation] = time.time()
        
    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration"""
        if operation not in self.active_timers:
            logger.warning(f"Timer '{operation}' was not started")
            return 0.0
        
        duration = time.time() - self.active_timers[operation]
        self.timings[operation].append(duration)
        del self.active_timers[operation]
        
        logger.debug(f"Operation '{operation}' took {duration:.3f}s")
        return duration
    
    def get_timing_stats(self, operation: str) -> Dict[str, float]:
        """Get timing statistics for an operation"""
        if operation not in self.timings:
            return {}
        
        times = self.timings[operation]
        return {
            'count': len(times),
            'total_time': sum(times),
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'last_time': times[-1]
        }
    
    def log_performance_summary(self):
        """Log comprehensive performance summary"""
        logger.info("PERFORMANCE TIMING SUMMARY")
        logger.info("=" * 50)
        
        for operation, times in self.timings.items():
            stats = self.get_timing_stats(operation)
            logger.info(f"{operation}:")
            logger.info(f"  Count: {stats['count']}, Total: {stats['total_time']:.2f}s")
            logger.info(f"  Avg: {stats['avg_time']:.3f}s, Min: {stats['min_time']:.3f}s, Max: {stats['max_time']:.3f}s")


class PatternStructureDiagnostics:
    """
    Specialized diagnostics for HeartBeat pattern structures
    Monitors rotation priors, rest patterns, and player matchups
    """
    
    def __init__(self):
        self.pattern_stats = {}
        
    def analyze_data_processor(self, processor) -> Dict[str, Any]:
        """Comprehensive analysis of DataProcessor pattern structures"""
        analysis = {
            'timestamp': time.time(),
            'component': 'DataProcessor'
        }
        
        # Team player rest patterns
        if hasattr(processor, 'team_player_rest_patterns'):
            rest_analysis = self._analyze_nested_dict(
                processor.team_player_rest_patterns, 
                name="team_player_rest_patterns"
            )
            analysis['team_rest_patterns'] = rest_analysis
        
        # Player matchup counts
        if hasattr(processor, 'player_matchup_counts'):
            matchup_analysis = self._analyze_dict_structure(
                processor.player_matchup_counts,
                name="player_matchup_counts"
            )
            analysis['player_matchups'] = matchup_analysis
        
        # Last change player matchups
        if hasattr(processor, 'last_change_player_matchups'):
            lc_analysis = self._analyze_dict_structure(
                processor.last_change_player_matchups,
                name="last_change_player_matchups"
            )
            analysis['last_change_matchups'] = lc_analysis
        
        # Situation player matchups
        if hasattr(processor, 'situation_player_matchups'):
            sit_analysis = self._analyze_nested_dict(
                processor.situation_player_matchups,
                name="situation_player_matchups"
            )
            analysis['situation_matchups'] = sit_analysis
        
        return analysis
    
    def analyze_candidate_generator(self, generator) -> Dict[str, Any]:
        """Comprehensive analysis of CandidateGenerator pattern structures"""
        analysis = {
            'timestamp': time.time(),
            'component': 'CandidateGenerator'
        }
        
        # Last change rotation transitions
        if hasattr(generator, 'last_change_rotation_transitions'):
            lc_transitions = self._analyze_dict_structure(
                generator.last_change_rotation_transitions,
                name="last_change_rotation_transitions"
            )
            analysis['last_change_transitions'] = lc_transitions
        
        # Player matchup counts (loaded patterns)
        if hasattr(generator, 'player_matchup_counts'):
            matchup_analysis = self._analyze_dict_structure(
                generator.player_matchup_counts,
                name="player_matchup_counts"
            )
            analysis['player_matchups'] = matchup_analysis
        
        return analysis
    
    def _analyze_dict_structure(self, data_dict, name: str) -> Dict[str, Any]:
        """Analyze a dictionary structure"""
        if not data_dict:
            return {'name': name, 'empty': True}
        
        total_items = len(data_dict)
        
        # Sample some keys to understand structure
        sample_keys = list(data_dict.keys())[:5]
        key_types = [type(k).__name__ for k in sample_keys]
        
        # Analyze values
        sample_values = [data_dict[k] for k in sample_keys]
        value_types = [type(v).__name__ for v in sample_values]
        
        # Calculate approximate memory usage
        estimated_size = sum(sys.getsizeof(k) + sys.getsizeof(v) 
                           for k, v in list(data_dict.items())[:100])
        estimated_total_size = (estimated_size / min(100, total_items)) * total_items
        
        return {
            'name': name,
            'total_items': total_items,
            'sample_key_types': key_types,
            'sample_value_types': value_types,
            'estimated_size_mb': estimated_total_size / 1024 / 1024,
            'avg_item_size': estimated_total_size / total_items if total_items > 0 else 0
        }
    
    def _analyze_nested_dict(self, nested_dict, name: str, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze nested dictionary structures"""
        if not nested_dict:
            return {'name': name, 'empty': True}
        
        def count_nested_items(d, depth=0):
            if depth >= max_depth or not isinstance(d, dict):
                return 1
            return sum(count_nested_items(v, depth + 1) for v in d.values())
        
        total_nested_items = count_nested_items(nested_dict)
        top_level_items = len(nested_dict)
        
        return {
            'name': name,
            'top_level_items': top_level_items,
            'total_nested_items': total_nested_items,
            'avg_nesting_factor': total_nested_items / max(top_level_items, 1),
            'max_analyzed_depth': max_depth
        }
    
    def log_pattern_diagnostics(self, analysis: Dict[str, Any]):
        """Log pattern structure diagnostics"""
        logger.info(f"PATTERN DIAGNOSTICS - {analysis['component']}")
        logger.info("=" * 50)
        
        for key, data in analysis.items():
            if key in ['timestamp', 'component']:
                continue
                
            if isinstance(data, dict) and 'name' in data:
                if data.get('empty'):
                    logger.info(f"{data['name']}: EMPTY")
                else:
                    logger.info(f"{data['name']}:")
                    if 'total_items' in data:
                        logger.info(f"  Items: {data['total_items']:,}")
                        logger.info(f"  Est. Size: {data.get('estimated_size_mb', 0):.1f}MB")
                    if 'total_nested_items' in data:
                        logger.info(f"  Nested Items: {data['total_nested_items']:,}")
                        logger.info(f"  Nesting Factor: {data.get('avg_nesting_factor', 0):.1f}")


def create_diagnostics_suite() -> Dict[str, Any]:
    """Create a complete diagnostics suite for HeartBeat components"""
    return {
        'memory_profiler': MemoryProfiler(),
        'performance_timer': PerformanceTimer(),
        'pattern_diagnostics': PatternStructureDiagnostics()
    }


def run_comprehensive_diagnostics(data_processor=None, candidate_generator=None, 
                                model=None, output_path: Optional[Path] = None):
    """
    Run comprehensive diagnostics on HeartBeat components
    
    Args:
        data_processor: DataProcessor instance to analyze
        candidate_generator: CandidateGenerator instance to analyze  
        model: PyTorchConditionalLogit model to analyze
        output_path: Optional path to save diagnostics report
    """
    logger.info("Starting comprehensive HeartBeat diagnostics...")
    
    diagnostics = create_diagnostics_suite()
    memory_profiler = diagnostics['memory_profiler']
    pattern_diagnostics = diagnostics['pattern_diagnostics']
    
    # Initial memory snapshot
    components = {}
    if data_processor:
        components['data_processor'] = data_processor
    if candidate_generator:
        components['candidate_generator'] = candidate_generator
    if model:
        components['model'] = model
    
    memory_profiler.take_snapshot("Initial State", components)
    
    # Analyze pattern structures
    if data_processor:
        dp_analysis = pattern_diagnostics.analyze_data_processor(data_processor)
        pattern_diagnostics.log_pattern_diagnostics(dp_analysis)
    
    if candidate_generator:
        cg_analysis = pattern_diagnostics.analyze_candidate_generator(candidate_generator)
        pattern_diagnostics.log_pattern_diagnostics(cg_analysis)
    
    # Final memory snapshot
    memory_profiler.take_snapshot("Final State", components)
    
    # Log summaries
    memory_profiler.log_summary()
    
    # Save report if requested
    if output_path:
        report = {
            'memory_snapshots': memory_profiler.snapshots,
            'memory_growth': memory_profiler.get_memory_growth_analysis(),
            'data_processor_analysis': dp_analysis if data_processor else None,
            'candidate_generator_analysis': cg_analysis if candidate_generator else None
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Diagnostics report saved to {output_path}")
    
    logger.info("Comprehensive diagnostics completed")
    return diagnostics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    print("HeartBeat Performance Diagnostics")
    print("This module provides comprehensive memory and performance monitoring.")
    print("Import and use with your HeartBeat components for production monitoring.")
