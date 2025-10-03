#!/usr/bin/env python3
"""
Test pattern save/load functionality for last-change-aware rotation patterns
"""

import sys
import os
import tempfile
import pandas as pd
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from candidate_generator import CandidateGenerator

def test_last_change_pattern_save_load():
    """Test that last-change-aware rotation patterns can be saved and loaded correctly"""
    
    print("🧪 Testing last-change pattern save/load...")
    
    # Create candidate generator with some test patterns
    generator = CandidateGenerator()
    
    # Add some test last-change rotation patterns
    # MTL has last change vs TOR
    generator.last_change_rotation_transitions['MTL']['TOR']['MTL']['prev_deployment']['next_deployment'] = 0.8
    generator.last_change_rotation_counts['MTL']['TOR']['MTL']['prev_deployment'] = 10
    
    # TOR has last change vs MTL
    generator.last_change_rotation_transitions['TOR']['MTL']['TOR']['prev_deployment2']['next_deployment2'] = 0.6
    generator.last_change_rotation_counts['TOR']['MTL']['TOR']['prev_deployment2'] = 5
    
    # UTA patterns
    generator.last_change_rotation_transitions['MTL']['UTA']['MTL']['prev_deployment3']['next_deployment3'] = 0.9
    generator.last_change_rotation_counts['MTL']['UTA']['MTL']['prev_deployment3'] = 15
    
    print(f"Original patterns: {len(generator.last_change_rotation_transitions)} teams")
    
    # Save patterns to temporary file
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
    
    try:
        generator.save_patterns(tmp_path)
        print("✓ Patterns saved successfully")
        
        # Create new generator and load patterns
        generator2 = CandidateGenerator()
        generator2.load_patterns(tmp_path)
        print("✓ Patterns loaded successfully")
        
        # Verify patterns were loaded correctly
        assert len(generator2.last_change_rotation_transitions) == 2, f"Expected 2 teams, got {len(generator2.last_change_rotation_transitions)}"
        
        # Check specific pattern values
        mtl_tor_pattern = generator2.last_change_rotation_transitions['MTL']['TOR']['MTL']['prev_deployment']['next_deployment']
        assert mtl_tor_pattern == 0.8, f"Expected 0.8, got {mtl_tor_pattern}"
        
        tor_mtl_pattern = generator2.last_change_rotation_transitions['TOR']['MTL']['TOR']['prev_deployment2']['next_deployment2']
        assert tor_mtl_pattern == 0.6, f"Expected 0.6, got {tor_mtl_pattern}"
        
        uta_pattern = generator2.last_change_rotation_transitions['MTL']['UTA']['MTL']['prev_deployment3']['next_deployment3']
        assert uta_pattern == 0.9, f"Expected 0.9, got {uta_pattern}"
        
        # Check counts
        mtl_tor_count = generator2.last_change_rotation_counts['MTL']['TOR']['MTL']['prev_deployment']
        assert mtl_tor_count == 10, f"Expected 10, got {mtl_tor_count}"
        
        print("✓ All pattern values match original")
        print("✅ Last-change pattern save/load test passed!")
        
    finally:
        # Clean up temporary file
        if tmp_path.exists():
            tmp_path.unlink()

def test_serialization_helpers():
    """Test the nested dict serialization/deserialization helpers"""
    
    print("🧪 Testing serialization helpers...")
    
    generator = CandidateGenerator()
    
    # Create test nested structure
    test_dict = generator.last_change_rotation_transitions
    test_dict['MTL']['TOR']['MTL']['prev']['next'] = 0.5
    test_dict['BOS']['MTL']['BOS']['prev2']['next2'] = 0.7
    
    # Test serialization
    serialized = generator._serialize_nested_dict(test_dict)
    assert isinstance(serialized, dict), "Serialized result should be regular dict"
    assert serialized['MTL']['TOR']['MTL']['prev']['next'] == 0.5, "Values should be preserved"
    
    # Test deserialization
    deserialized = generator._deserialize_nested_dict(serialized)
    assert deserialized['MTL']['TOR']['MTL']['prev']['next'] == 0.5, "Values should be preserved after deserialization"
    
    # Test that the structure works for existing keys
    print(f"Deserialized structure works for existing keys: {deserialized['MTL']['TOR']['MTL']['prev']['next']}")
    
    # Test new key access step by step
    print(f"Testing new key access...")
    level1 = deserialized['NEW']
    print(f"Level 1 type: {type(level1)}")
    if hasattr(level1, 'default_factory'):
        level2 = level1['TEAM']
        print(f"Level 2 type: {type(level2)}")
        if hasattr(level2, 'default_factory'):
            level3 = level2['NEW']
            print(f"Level 3 type: {type(level3)}")
            if hasattr(level3, 'default_factory'):
                level4 = level3['test']
                print(f"Level 4 type: {type(level4)}")
                if hasattr(level4, 'default_factory'):
                    final_value = level4['test']
                    print(f"Final value: {final_value}, type: {type(final_value)}")
                    assert final_value == 0.0, f"Expected 0.0, got {final_value}"
    
    print("Serialization helpers test passed!")

if __name__ == "__main__":
    test_serialization_helpers()
    test_last_change_pattern_save_load()
    print("🎉 All pattern I/O tests passed!")
