#!/usr/bin/env python3
"""
Production-Grade Clip System Test
Tests DuckDB index with concurrent writes
"""

import sys
from pathlib import Path
import asyncio
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.tools.clip_query import ClipQueryTool, ClipSearchParams
from orchestrator.tools.clip_cutter import FFmpegClipCutter
from orchestrator.tools.clip_index_db import get_clip_index


def test_concurrent_writes():
    """Test that concurrent writes don't lose data"""
    print("\n" + "="*70)
    print("TEST 1: Concurrent Write Safety")
    print("="*70 + "\n")
    
    index = get_clip_index()
    cutter = FFmpegClipCutter(use_duckdb=True, max_workers=4)
    
    # Query multiple clips
    query_tool = ClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    params = ClipSearchParams(
        players=["8478463", "8476880", "8478440"],  # Multiple players
        event_types=["zone_exit"],
        timeframe="last_game",
        game_ids=["20038"],
        limit=10
    )
    
    segments = query_tool.query_events(params)
    print(f"Found {len(segments)} event segments")
    
    if len(segments) < 3:
        print("Not enough segments for concurrent write test")
        return
    
    # Build cut requests
    from orchestrator.tools.clip_cutter import ClipCutRequest
    
    requests = []
    for seg in segments[:6]:  # Cut 6 clips concurrently
        if not seg.period_video_path or seg.period != 1:
            continue
        
        output_dir = cutter.output_base_dir / "concurrent_test"
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
    
    print(f"\nCutting {len(requests)} clips in parallel...")
    start = time.time()
    results = cutter.cut_clips_parallel(requests, force=True)  # Force re-cut
    elapsed = time.time() - start
    
    successful = sum(1 for r in results if r.success)
    print(f"\n✅ Results:")
    print(f"   Successful: {successful}/{len(results)}")
    print(f"   Total time: {elapsed:.2f}s")
    print(f"   Avg per clip: {elapsed/len(results):.2f}s")
    
    # Wait for index to flush
    print("\nWaiting for index writes to complete...")
    time.sleep(2)
    
    # Verify ALL clips are in index
    print("\nVerifying index integrity...")
    verified = 0
    for result in results:
        if result.success:
            clip_data = index.find_by_clip_id(result.clip_id)
            if clip_data:
                verified += 1
            else:
                print(f"   ❌ MISSING: {result.clip_id}")
    
    print(f"\n✅ Index Verification:")
    print(f"   Clips written: {successful}")
    print(f"   Clips in index: {verified}")
    print(f"   Data integrity: {'PASS' if verified == successful else 'FAIL'}")
    
    if verified == successful:
        print("\n🎉 CONCURRENT WRITE TEST PASSED!")
    else:
        print("\n❌ CONCURRENT WRITE TEST FAILED - Some clips missing from index")


def test_cache_hits():
    """Test that caching works correctly"""
    print("\n" + "="*70)
    print("TEST 2: Cache Hit Performance")
    print("="*70 + "\n")
    
    cutter = FFmpegClipCutter(use_duckdb=True, max_workers=1)
    source = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/2025-2026/team/WSH/p1-20251012-NHL-WSHvsNYR-20252026-20038.MOV")
    
    from orchestrator.tools.clip_cutter import ClipCutRequest
    
    request = ClipCutRequest(
        source_video=source,
        start_seconds=100.0,
        end_seconds=108.0,
        output_path=cutter.output_base_dir / "cache_test" / "test_cache.mp4",
        clip_id="cache_test_clip",
        metadata={'test': 'cache'}
    )
    
    # First cut
    print("First cut (should miss cache)...")
    start = time.time()
    result1 = cutter.cut_clip(request, force=True)
    time1 = time.time() - start
    
    # Second cut (should hit cache)
    print("Second cut (should hit cache)...")
    start = time.time()
    result2 = cutter.cut_clip(request, force=False)
    time2 = time.time() - start
    
    print(f"\n✅ Cache Test Results:")
    print(f"   First cut: {time1:.2f}s")
    print(f"   Second cut: {time2:.2f}s")
    print(f"   Speedup: {time1/time2 if time2 > 0 else float('inf'):.1f}x")
    print(f"   Cache working: {'YES' if time2 < time1/10 else 'NO'}")


def test_query_performance():
    """Test DuckDB query performance"""
    print("\n" + "="*70)
    print("TEST 3: Query Performance")
    print("="*70 + "\n")
    
    index = get_clip_index()
    
    # Test different query patterns
    queries = [
        ("By player_id", {'player_ids': ['8478463'], 'limit': 100}),
        ("By game_id", {'game_ids': ['20038'], 'limit': 100}),
        ("By event_type", {'event_types': ['CONTROLLED EXIT FROM DZ'], 'limit': 100}),
        ("Combined filters", {'player_ids': ['8478463'], 'game_ids': ['20038'], 'limit': 100})
    ]
    
    for query_name, filters in queries:
        start = time.time()
        results = index.query_clips(**filters)
        elapsed = time.time() - start
        
        print(f"{query_name}:")
        print(f"   Results: {len(results)}")
        print(f"   Time: {elapsed*1000:.2f}ms")


def test_stats_endpoint():
    """Test index statistics"""
    print("\n" + "="*70)
    print("TEST 4: Index Statistics")
    print("="*70 + "\n")
    
    index = get_clip_index()
    stats = index.get_stats()
    
    print("Index Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    """Run all production tests"""
    print("\n" + "#"*70)
    print("# Production-Grade Clip System Test Suite")
    print("# DuckDB Index + Thread-Safe Concurrent Writes")
    print("#"*70)
    
    test_concurrent_writes()
    test_cache_hits()
    test_query_performance()
    test_stats_endpoint()
    
    # Shutdown gracefully
    print("\nShutting down index...")
    index = get_clip_index()
    index.shutdown()
    
    print("\n" + "#"*70)
    print("# All Production Tests Complete!")
    print("#"*70 + "\n")


if __name__ == "__main__":
    main()

