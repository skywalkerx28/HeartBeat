#!/usr/bin/env python3
"""
Publish a delivery clip from a local master MP4.

This cuts a segment with FFmpeg, generates thumbnail and HLS (optional),
uploads assets to gs://heartbeat-media/{TEAM}/{SEASON}/{GAME_ID}/{CLIP_ID}/,
and registers assets in Postgres.

Usage:
  DATABASE_URL=... MEDIA_GCS_BUCKET=heartbeat-media \
  python3 scripts/media/publish_clip_from_master.py \
    --file /path/to/master.mp4 \
    --team MTL --season 2025-2026 --game_id 20062 \
    --clip_id DEV_MTL_NSH_20062_P1 --start 0 --end 10
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrator.tools.clip_cutter import FFmpegClipCutter, ClipCutRequest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', required=True, help='Local path to master MP4')
    p.add_argument('--team', required=True)
    p.add_argument('--season', required=True)
    p.add_argument('--game_id', required=True)
    p.add_argument('--clip_id', required=True)
    p.add_argument('--start', type=float, required=True)
    p.add_argument('--end', type=float, required=True)
    args = p.parse_args()

    local = Path(args.file)
    if not local.exists():
        print(f"ERROR: file not found: {local}")
        sys.exit(1)

    # Initialize cutter (uses DATABASE_URL and MEDIA_GCS_BUCKET)
    cutter = FFmpegClipCutter(max_workers=2)

    # Local output path (temporary); cutter will upload to GCS and register assets
    out_dir = Path('data/clips/generated/published')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.clip_id}.mp4"

    req = ClipCutRequest(
        source_video=local,
        start_seconds=args.start,
        end_seconds=args.end,
        output_path=out_path,
        clip_id=args.clip_id,
        metadata={
            'team_code': args.team,
            'season': args.season,
            'game_id': args.game_id,
            'event_type': 'PUBLISHED'
        }
    )

    print(f"Cutting clip {args.clip_id}: {args.start:.2f}s → {args.end:.2f}s …")
    result = cutter.cut_clip(req)

    if result.success:
        print("✓ Delivery assets published to GCS and registered in Postgres")
        print(f"  Local MP4: {result.output_path}")
        print(f"  Thumbnail: {result.thumbnail_path}")
    else:
        print(f"✗ Failed: {result.error_message}")
        sys.exit(2)


if __name__ == '__main__':
    main()
