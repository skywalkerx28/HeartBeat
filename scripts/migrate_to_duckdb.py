#!/usr/bin/env python3
"""
Migrate existing JSON clip index to DuckDB
One-time migration script
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.tools.clip_index_db import get_clip_index


def main():
    """Migrate JSON index to DuckDB"""
    print("\n" + "="*70)
    print("Migrating Clip Index: JSON → DuckDB")
    print("="*70 + "\n")
    
    # Get DuckDB index
    index = get_clip_index()
    
    # Path to old JSON index
    json_path = Path(__file__).parent.parent / "data/clips/generated/clip_index.json"
    
    if not json_path.exists():
        print(f"No JSON index found at {json_path}")
        print("Nothing to migrate.")
        return
    
    print(f"Found JSON index: {json_path}")
    print("Migrating...")
    
    # Migrate
    count = index.migrate_from_json(str(json_path))
    
    print(f"\n✅ Migration complete!")
    print(f"   Migrated: {count} clips")
    
    # Show stats
    print("\nDuckDB Index Statistics:")
    stats = index.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Backup old JSON
    backup_path = json_path.with_suffix('.json.backup')
    json_path.rename(backup_path)
    print(f"\nOld JSON backed up to: {backup_path}")
    
    # Shutdown gracefully
    index.shutdown()


if __name__ == "__main__":
    main()

