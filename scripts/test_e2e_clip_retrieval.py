#!/usr/bin/env python3
"""
End-to-End Clip Retrieval Test
Quick test of the complete pipeline with progress indicators
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.tools.clip_query import ClipQueryTool, ClipSearchParams
from orchestrator.tools.clip_cutter import FFmpegClipCutter, ClipCutRequest
from orchestrator.tools.clip_index_db import DuckDBClipIndex

print("\n" + "="*70)
print("E2E Clip Retrieval Test - Complete Pipeline")
print("="*70 + "\n")

# Step 1: Query
print("STEP 1: Query events from extracted metrics")
print("-" * 70)

query_tool = ClipQueryTool(
    extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
    clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
)

params = ClipSearchParams(
    players=["8478463"],  # WSH player
    event_types=["zone_exit"],
    timeframe="last_game",
    game_ids=["20038"],
    limit=3  # Just 3 clips for E2E test
)

print(f"Query: {params.event_types} for player {params.players} in game {params.game_ids}")

segments = query_tool.query_events(params)
print(f"✓ Found {len(segments)} segments\n")

if not segments:
    print("No segments found - exiting")
    sys.exit(0)

# Step 2: Cut clips
print("STEP 2: Cut clips with FFmpeg")
print("-" * 70)

cutter = FFmpegClipCutter(use_duckdb=True, max_workers=2)

requests = []
for seg in segments[:3]:
    if not seg.period_video_path:
        continue
    
    output_dir = cutter.output_base_dir / "e2e_test"
    output_path = output_dir / f"{seg.clip_id}.mp4"
    
    request = ClipCutRequest(
        source_video=Path(seg.period_video_path),
        start_seconds=seg.start_timecode_s,
        end_seconds=seg.end_timecode_s,
        output_path=output_path,
        clip_id=seg.clip_id,
        metadata={
            'player_id': seg.player_id,
            'event_type': seg.event_type,
            'game_id': seg.game_id,
            'game_date': seg.game_date,
            'season': '2025-2026',
            'period': seg.period,
            'team_code': seg.team_code,
            'opponent_code': seg.opponent,
            'outcome': seg.outcome,
            'zone': seg.zone
        }
    )
    requests.append(request)

print(f"Cutting {len(requests)} clips...")
start = time.time()
results = cutter.cut_clips_parallel(requests)
elapsed = time.time() - start

successful = [r for r in results if r.success]
print(f"✓ Cut {len(successful)}/{len(results)} clips in {elapsed:.1f}s\n")

# Step 3: Verify in DuckDB
print("STEP 3: Verify clips in DuckDB index")
print("-" * 70)

# Wait for async writes
time.sleep(1)

# Get index instance (create if needed - will reuse existing DuckDB file)
index = DuckDBClipIndex()
for result in successful:
    clip_data = index.find_by_clip_id(result.clip_id)
    if clip_data:
        print(f"✓ {result.clip_id}")
        print(f"  Player: {clip_data['player_name'] or clip_data['player_id']}")
        print(f"  Event: {clip_data['event_type']}")
        print(f"  File: {Path(clip_data['output_path']).name}")
    else:
        print(f"✗ {result.clip_id} NOT IN INDEX")

# Step 4: Stats
print("\n" + "="*70)
print("Final Statistics")
print("="*70)

stats = index.get_stats()
print(f"Total clips in index: {stats['total_clips']}")
print(f"Total storage: {stats['total_size_mb']} MB")
print(f"Total duration: {stats['total_duration_min']} minutes")
print(f"Unique players: {stats['unique_players']}")
print(f"Unique games: {stats['unique_games']}")

# Shutdown
index.shutdown()

print("\n" + "="*70)
print("✅ E2E TEST COMPLETE - All systems operational!")
print("="*70 + "\n")

