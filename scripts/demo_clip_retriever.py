#!/usr/bin/env python3
"""
Clip Retriever End-to-End Demo
Demonstrates the complete flow from query to playable clips
"""

import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.tools.clip_query import ClipQueryTool, ClipSearchParams
from orchestrator.tools.clip_cutter import FFmpegClipCutter, ClipCutRequest


def demo_query_only():
    """Demo: Query events without cutting"""
    print("\n" + "="*70)
    print("DEMO 1: Query Events (No Cutting)")
    print("="*70 + "\n")
    
    tool = ClipQueryTool(
        extracted_metrics_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/extracted_metrics",
        clips_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips"
    )
    
    params = ClipSearchParams(
        players=["8478463", "8476880"],  # WSH players
        event_types=["zone_exit"],
        timeframe="last_game",
        game_ids=["20038"],
        limit=10
    )
    
    print(f"Query Parameters:")
    print(f"  Players: {params.players}")
    print(f"  Event types: {params.event_types}")
    print(f"  Game IDs: {params.game_ids}")
    print(f"  Limit: {params.limit}")
    print()
    
    segments = tool.query_events(params)
    
    print(f"Found {len(segments)} event segments:\n")
    for i, seg in enumerate(segments, 1):
        print(f"{i}. Player {seg.player_id} - {seg.event_type} ({seg.outcome})")
        print(f"   Period {seg.period} @ {seg.timecode} ({seg.timecode_seconds:.1f}s)")
        print(f"   Clip window: {seg.start_timecode_s:.1f}s - {seg.end_timecode_s:.1f}s")
        print(f"   Video: .../{Path(seg.period_video_path).name if seg.period_video_path else 'N/A'}")
        print()


def demo_cut_single_clip():
    """Demo: Cut a single clip"""
    print("\n" + "="*70)
    print("DEMO 2: Cut Single Clip")
    print("="*70 + "\n")
    
    cutter = FFmpegClipCutter(
        output_base_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/generated",
        max_workers=1
    )
    
    source = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/2025-2026/team/WSH/p1-20251012-NHL-WSHvsNYR-20252026-20038.MOV")
    
    request = ClipCutRequest(
        source_video=source,
        start_seconds=14.7,  # 3s before event at 17.7s
        end_seconds=22.7,    # 5s after event
        output_path=cutter.output_base_dir / "demo" / "single_clip_demo.mp4",
        clip_id="demo_single_clip",
        metadata={
            "demo": True,
            "event": "First controlled exit"
        }
    )
    
    print(f"Cutting clip:")
    print(f"  Source: {source.name}")
    print(f"  Time range: {request.start_seconds}s - {request.end_seconds}s ({request.duration}s)")
    print(f"  Output: {request.output_path}")
    print()
    
    result = cutter.cut_clip(request)
    
    print(f"Result:")
    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Output: {result.output_path}")
        print(f"  Thumbnail: {result.thumbnail_path}")
        print(f"  Duration: {result.duration_s:.2f}s")
        print(f"  File size: {result.file_size_bytes / 1024 / 1024:.1f} MB")
        print(f"  Processing time: {result.processing_time_s:.2f}s")
    else:
        print(f"  Error: {result.error_message}")


def demo_parallel_cutting():
    """Demo: Cut multiple clips in parallel"""
    print("\n" + "="*70)
    print("DEMO 3: Parallel Clip Cutting (3 workers)")
    print("="*70 + "\n")
    
    cutter = FFmpegClipCutter(
        output_base_dir="/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/generated",
        max_workers=3
    )
    
    source = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/2025-2026/team/WSH/p1-20251012-NHL-WSHvsNYR-20252026-20038.MOV")
    
    # Create 5 clip requests
    clip_times = [
        (14.7, 22.7, "early_exit"),
        (855.0, 863.0, "mid_period_exit_1"),
        (1041.0, 1049.0, "mid_period_exit_2"),
        (1822.0, 1830.0, "late_exit"),
        (446.63, 454.63, "another_exit")
    ]
    
    requests = []
    for start, end, label in clip_times:
        request = ClipCutRequest(
            source_video=source,
            start_seconds=start,
            end_seconds=end,
            output_path=cutter.output_base_dir / "demo" / f"parallel_{label}.mp4",
            clip_id=f"demo_parallel_{label}",
            metadata={"demo": True}
        )
        requests.append(request)
    
    print(f"Cutting {len(requests)} clips in parallel (max {cutter.max_workers} workers)...")
    print()
    
    results = cutter.cut_clips_parallel(requests)
    
    print(f"\nResults:")
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    total_time = sum(r.processing_time_s for r in results)
    total_size = sum(r.file_size_bytes or 0 for r in results if r.success)
    
    print(f"  Successful: {successful}/{len(results)}")
    print(f"  Failed: {failed}")
    print(f"  Total processing time: {total_time:.2f}s")
    print(f"  Total output size: {total_size / 1024 / 1024:.1f} MB")
    print(f"  Avg time per clip: {total_time / len(results):.2f}s")


async def demo_full_orchestrator():
    """Demo: Full orchestrator node flow"""
    print("\n" + "="*70)
    print("DEMO 4: Full Orchestrator Node (Query → Cut → Results)")
    print("="*70 + "\n")
    
    from orchestrator.nodes.clip_retriever import ClipRetrieverNode
    from orchestrator.utils.state import create_initial_state, UserContext, UserRole
    
    # Create node
    node = ClipRetrieverNode()
    
    # Create user context
    user_context = UserContext(
        user_id="test_demo",
        name="Demo User",
        role=UserRole.ANALYST,
        team_access=["WSH"]
    )
    
    # Test queries
    queries = [
        "Show me d-zone exits from the WSH game",
        "Show me zone exits from period 1"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 70)
        
        state = create_initial_state(user_context, query)
        state["intent_analysis"] = {"intent": "clip_retrieval"}
        state["required_tools"] = ["clip_retrieval"]
        
        result = await node.process(state)
        
        clips = result.get('analytics_data', {}).get('clips', [])
        print(f"Result: {len(clips)} clips generated")
        
        if clips:
            for clip in clips[:3]:  # Show first 3
                print(f"  - {clip['clip_id']}")
                print(f"    Event: {clip['event_type']} @ Period {clip['period']}")
                print(f"    Duration: {clip['duration']:.1f}s")


def main():
    """Run all demos"""
    print("\n" + "#"*70)
    print("# Clip Retriever End-to-End Demonstration")
    print("#"*70)
    
    # Demo 1: Query only
    demo_query_only()
    
    # Demo 2: Single clip cutting
    demo_cut_single_clip()
    
    # Demo 3: Parallel cutting
    demo_parallel_cutting()
    
    # Demo 4: Full orchestrator
    asyncio.run(demo_full_orchestrator())
    
    print("\n" + "#"*70)
    print("# All Demos Complete!")
    print("#"*70 + "\n")


if __name__ == "__main__":
    main()

