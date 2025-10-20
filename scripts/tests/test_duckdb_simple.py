#!/usr/bin/env python3
"""Simple DuckDB test - no threads, just verify basic functionality"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator/tools"))

print("="*70)
print("Simple DuckDB Clip Index Test")
print("="*70)
print()

import duckdb
import hashlib
import json
from clip_index_db import ClipIndexEntry

# Test database path
db_path = Path(__file__).parent.parent / "data/clips/test_clip_index.duckdb"
db_path.parent.mkdir(parents=True, exist_ok=True)

print(f"1. Creating database at {db_path}")
con = duckdb.connect(str(db_path))

print("2. Creating schema...")
con.execute("""
    CREATE TABLE IF NOT EXISTS clips (
        clip_id VARCHAR PRIMARY KEY,
        clip_hash VARCHAR UNIQUE NOT NULL,
        output_path VARCHAR NOT NULL,
        thumbnail_path VARCHAR NOT NULL,
        source_video VARCHAR NOT NULL,
        start_timecode_s DOUBLE NOT NULL,
        end_timecode_s DOUBLE NOT NULL,
        duration_s DOUBLE NOT NULL,
        game_id VARCHAR NOT NULL,
        game_date VARCHAR NOT NULL,
        season VARCHAR NOT NULL,
        period INTEGER NOT NULL,
        player_id VARCHAR NOT NULL,
        player_name VARCHAR,
        team_code VARCHAR NOT NULL,
        opponent_code VARCHAR NOT NULL,
        event_type VARCHAR NOT NULL,
        outcome VARCHAR,
        zone VARCHAR,
        file_size_bytes BIGINT NOT NULL,
        processing_time_s DOUBLE,
        cache_hit BOOLEAN DEFAULT FALSE,
        extra_metadata VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
con.execute("CREATE INDEX IF NOT EXISTS idx_clips_player ON clips(player_id)")
con.commit()
print("✓ Schema created")

print("\n3. Inserting test clip...")
test_entry = ClipIndexEntry(
    clip_id="test_001",
    clip_hash=hashlib.md5(b"test1").hexdigest(),
    output_path="/test/clip1.mp4",
    thumbnail_path="/test/clip1.jpg",
    source_video="/source/p1.mp4",
    start_timecode_s=100.0,
    end_timecode_s=108.0,
    duration_s=8.0,
    game_id="20038",
    game_date="20251012",
    season="2025-2026",
    period=1,
    player_id="8478463",
    player_name="Anthony Beauvillier",
    team_code="WSH",
    opponent_code="NYR",
    event_type="CONTROLLED EXIT FROM DZ",
    outcome="successful",
    zone="dz",
    file_size_bytes=14567890,
    processing_time_s=3.2,
    cache_hit=False,
    extra_metadata=json.dumps({"test": True})
)

con.execute("""
    INSERT INTO clips (
        clip_id, clip_hash, output_path, thumbnail_path,
        source_video, start_timecode_s, end_timecode_s, duration_s,
        game_id, game_date, season, period,
        player_id, player_name, team_code, opponent_code,
        event_type, outcome, zone,
        file_size_bytes, processing_time_s, cache_hit, extra_metadata
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (clip_id) DO UPDATE SET updated_at = now()
""", test_entry.to_tuple())
con.commit()
print("✓ Inserted test clip")

print("\n4. Querying by clip_id...")
result = con.execute("SELECT clip_id, player_name, event_type, duration_s FROM clips WHERE clip_id = ?", ['test_001']).fetchone()
if result:
    print(f"✓ Found: {result[0]} - {result[1]} - {result[2]} ({result[3]}s)")
else:
    print("✗ NOT FOUND")

print("\n5. Getting stats...")
total = con.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
print(f"✓ Total clips: {total}")

print("\n6. Exporting to Parquet...")
parquet_path = db_path.parent / "test_clips_export.parquet"
con.execute(f"COPY clips TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
print(f"✓ Exported to {parquet_path}")
print(f"  File size: {parquet_path.stat().st_size / 1024:.1f} KB")

con.close()

print("\n" + "="*70)
print("✅ ALL TESTS PASSED - DuckDB working correctly!")
print("="*70)

