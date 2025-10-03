#!/usr/bin/env python3
"""
MyPy strict type checking enforcement for HeartBeat Line Matchup Engine
Ensures professional-grade type safety throughout the codebase
"""

import subprocess
import sys
from pathlib import Path

def run_mypy_strict_check() -> bool:
    """Run mypy --strict on all Python files in the engine"""
    
    print("=" * 60)
    print("RUNNING MYPY STRICT TYPE CHECKING")
    print("=" * 60)
    
    engine_path = Path(__file__).parent
    python_files = list(engine_path.glob("*.py"))
    
    # Files to check (exclude test files for now)
    core_files = [
        'data_processor.py',
        'feature_engineering.py', 
        'conditional_logit_model.py',
        'candidate_generator.py',
        'live_predictor.py',
        'train_engine.py',
        'player_mapper.py'
    ]
    
    all_passed = True
    
    for filename in core_files:
        file_path = engine_path / filename
        if file_path.exists():
            print(f"\n🔍 Checking {filename}...")
            
            try:
                result = subprocess.run(
                    ['mypy', '--strict', '--config-file', 'mypy.ini', str(file_path)],
                    cwd=engine_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(f"  ✅ {filename}: PASSED")
                else:
                    print(f"  ❌ {filename}: FAILED")
                    print(f"     Errors:\n{result.stdout}")
                    all_passed = False
                    
            except subprocess.TimeoutExpired:
                print(f"  ⏰ {filename}: TIMEOUT (taking too long)")
                all_passed = False
            except FileNotFoundError:
                print(f"  ⚠️  MyPy not installed - install with: pip install mypy")
                return False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 ALL FILES PASS MYPY STRICT CHECKING")
        print("✅ Professional-grade type safety achieved")
    else:
        print("⚠️  Some files need type annotation improvements")
        print("📝 Review errors above and add missing type hints")
    
    print(f"{'='*60}")
    return all_passed

if __name__ == "__main__":
    success = run_mypy_strict_check()
    sys.exit(0 if success else 1)
