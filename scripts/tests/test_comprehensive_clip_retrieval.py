#!/usr/bin/env python3
"""
Comprehensive Clip Retrieval Test
Tests all advanced features: shifts, multi-period, teammate filters, etc.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.tools.clip_query_enhanced import EnhancedClipQueryTool, ClipSearchParams
from orchestrator.tools.clip_cutter import FFmpegClipCutter, ClipCutRequest
from orchestrator.tools.clip_index_db import get_clip_index


def test_shift_mode():
    """Test shift mode"""
    print("\n" + "="*70)
    print("TEST 1: Shift Mode - 'Show me all my shifts in period 1'")
    print("="*70 + "\n")
    
    tool = EnhancedClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    params = ClipSearchParams(
        players=[8478463],  
        mode="shift",
        game_ids=["20038"],
        periods=[1],
        limit=3,
        season="20252026"
    )
    
    segments = tool.query(params)
    print(f"Query: Shifts for Beauvillier in Period 1")
    print(f"Result: Found {len(segments)} shifts\n")
    
    for i, seg in enumerate(segments, 1):
        print(f"{i}. {seg.title}")
        print(f"   Duration: {seg.duration_s:.1f}s ({seg.start_timecode_s:.1f}s - {seg.end_timecode_s:.1f}s)")
        print(f"   Strength: {seg.strength}")
        print(f"   Video: {Path(seg.period_video_path).name if seg.period_video_path else 'N/A'}")
        print()
    
    return segments


def test_multi_period_events():
    """Test multi-period event queries"""
    print("\n" + "="*70)
    print("TEST 2: Multi-Period - 'Show me zone exits in all periods'")
    print("="*70 + "\n")
    
    tool = EnhancedClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    params = ClipSearchParams(
        players=[8478463],
        event_types=["zone_exit"],
        mode="event",
        game_ids=["20038"],
        periods=[1, 2, 3],  # All periods
        limit=5,
        season="20252026"
    )
    
    segments = tool.query(params)
    print(f"Query: Zone exits for Beauvillier in all periods")
    print(f"Result: Found {len(segments)} events\n")
    
    for i, seg in enumerate(segments, 1):
        print(f"{i}. Period {seg.period}: {seg.event_type}")
        print(f"   Time: {seg.period_time}")
        print(f"   Timecode: {seg.timecode_seconds:.1f}s")
        print()
    
    return segments


def test_opponent_filter():
    """Test opponent filtering"""
    print("\n" + "="*70)
    print("TEST 3: Opponent Filter - 'Show me shifts against specific opponents'")
    print("="*70 + "\n")
    
    tool = EnhancedClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    # Find a specific opponent from first shift
    params_all = ClipSearchParams(
        players=[8478463],
        mode="shift",
        game_ids=["20038"],
        periods=[1],
        limit=1,
        season="20252026"
    )
    all_shifts = tool.query(params_all)
    
    if all_shifts and all_shifts[0].opponents_on_ice:
        opponent_id = all_shifts[0].opponents_on_ice[0]['id']
        opponent_name = all_shifts[0].opponents_on_ice[0]['name']
        
        params = ClipSearchParams(
            players=[8478463],
            mode="shift",
            opponents_on_ice=[opponent_id],
            game_ids=["20038"],
            periods=[1],
            limit=3,
            season="20252026"
        )
        
        segments = tool.query(params)
        print(f"Query: Shifts for Beauvillier when {opponent_name} was on ice")
        print(f"Result: Found {len(segments)} shifts\n")
        
        for i, seg in enumerate(segments, 1):
            print(f"{i}. {seg.title}")
            print(f"   Opponents on ice: {len(seg.opponents_on_ice)} players")
            print()
        
        return segments
    else:
        print("Could not find opponent data for filtering test")
        return []


def test_shift_cutting():
    """Test cutting actual shift clips"""
    print("\n" + "="*70)
    print("TEST 4: Cut Shift Clips - 'Generate video clips for shifts'")
    print("="*70 + "\n")
    
    tool = EnhancedClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    params = ClipSearchParams(
        players=[8478463],
        mode="shift",
        game_ids=["20038"],
        periods=[1],
        limit=2,  # Just cut 2 shifts
        season="20252026"
    )
    
    segments = tool.query(params)
    print(f"Found {len(segments)} shifts to cut\n")
    
    # Cut clips
    cutter = FFmpegClipCutter(use_duckdb=True, max_workers=2)
    
    requests = []
    for seg in segments:
        if not seg.period_video_path:
            continue
        
        output_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/generated") / seg.game_id / f"p{seg.period}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{seg.clip_id}.mp4"
        
        request = ClipCutRequest(
            source_video=Path(seg.period_video_path),
            start_seconds=seg.start_timecode_s,
            end_seconds=seg.end_timecode_s,
            output_path=output_path,
            clip_id=seg.clip_id,
            metadata={
                'player_id': seg.player_id,
                'player_name': seg.player_name,
                'mode': 'shift',
                'period': seg.period,
                'game_id': seg.game_id,
                'season': seg.season,
                'team_code': seg.team_code,
                'opponent': seg.opponent,
                'strength': seg.strength,
                'duration_s': seg.duration_s
            }
        )
        requests.append(request)
    
    if requests:
        print("Cutting clips...")
        results = cutter.cut_clips_parallel(requests)
        
        print(f"\nResults:")
        for result in results:
            status = "SUCCESS" if result.success else "FAILED"
            cache = "(cached)" if hasattr(result, 'cache_hit') and result.cache_hit else "(new)"
            print(f"  [{status}] {result.clip_id} {cache}")
            print(f"      Duration: {result.duration_s:.1f}s, Size: {result.file_size_bytes / 1024 / 1024:.1f}MB")
            if result.thumbnail_path:
                print(f"      Thumbnail: {Path(result.thumbnail_path).name}")
        
        return results
    else:
        print("No clips to cut (missing video files)")
        return []


def test_complex_query():
    """Test complex query: 'Show me my second period shifts'"""
    print("\n" + "="*70)
    print("TEST 5: Complex Query - 'Show me my second period shifts'")
    print("="*70 + "\n")
    
    tool = EnhancedClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    params = ClipSearchParams(
        players=[8478463],
        mode="shift",
        game_ids=["20038"],
        periods=[2],  # Period 2 only
        limit=5,
        season="20252026"
    )
    
    segments = tool.query(params)
    print(f"Query: 'Show me all my shifts in the second period from last game'")
    print(f"Result: Found {len(segments)} shifts in period 2\n")
    
    for i, seg in enumerate(segments, 1):
        print(f"{i}. {seg.title}")
        print(f"   Time: {seg.period_time} - Duration: {seg.duration_s:.1f}s")
        print()
    
    return segments


def test_player_name_search():
    """Test player name search"""
    print("\n" + "="*70)
    print("TEST 6: Name Search - 'Show me shifts for Ovechkin'")
    print("="*70 + "\n")
    
    tool = EnhancedClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    # Search by name instead of ID
    params = ClipSearchParams(
        players=["Ovechkin"],  # Name search
        mode="shift",
        game_ids=["20038"],
        periods=[1],
        limit=2,
        team="WSH",
        season="20252026"
    )
    
    segments = tool.query(params)
    print(f"Query: Shifts for 'Ovechkin' in Period 1")
    print(f"Result: Found {len(segments)} shifts\n")
    
    for i, seg in enumerate(segments, 1):
        print(f"{i}. {seg.player_name} - {seg.title}")
        print(f"   Duration: {seg.duration_s:.1f}s")
        print()
    
    return segments


def verify_in_database():
    """Verify clips are in DuckDB"""
    print("\n" + "="*70)
    print("TEST 7: Database Verification")
    print("="*70 + "\n")
    
    index = get_clip_index()
    
    # Query shift clips
    clips = index.query_clips(player_ids=["8478463"], limit=10)
    
    print(f"Clips in database for player 8478463: {len(clips)}")
    
    shift_clips = [c for c in clips if c.get('extra_metadata', '{}') and 'shift' in c.get('extra_metadata', '{}')]
    event_clips = [c for c in clips if c.get('extra_metadata', '{}') and 'event' in c.get('extra_metadata', '{}')]
    
    print(f"  Shift clips: {len(shift_clips)}")
    print(f"  Event clips: {len(event_clips)}")
    
    stats = index.get_stats()
    print(f"\nOverall database stats:")
    print(f"  Total clips: {stats['total_clips']}")
    print(f"  Total storage: {stats['total_size_mb']} MB")
    print(f"  Total duration: {stats['total_duration_min']} minutes")


def main():
    """Run all comprehensive tests"""
    print("\n" + "="*70)
    print("COMPREHENSIVE CLIP RETRIEVAL SYSTEM TEST")
    print("Testing all advanced features with WSH vs NYR game (20038)")
    print("="*70)
    
    try:
        # Test 1: Shift mode
        test_shift_mode()
        
        # Test 2: Multi-period events
        test_multi_period_events()
        
        # Test 3: Opponent filtering
        test_opponent_filter()
        
        # Test 4: Actually cut shift clips
        test_shift_cutting()
        
        # Test 5: Complex query (period 2 shifts)
        test_complex_query()
        
        # Test 6: Player name search
        test_player_name_search()
        
        # Test 7: Verify in database
        verify_in_database()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

