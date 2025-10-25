#!/usr/bin/env python3
"""
Ingest a master video into the HeartBeat lake and register in Postgres.

Usage:
  DATABASE_URL=... MEDIA_GCS_BUCKET=heartbeat-media \
  python3 scripts/media/ingest_master_to_lake.py \
    --file /path/to/master.mp4 \
    --team MTL --season 2025-2026 --game_id 20031 --clip_id CLIP123

This uploads to: gs://heartbeat-474020-lake/media/raw/{TEAM}/{SEASON}/{GAME_ID}/{filename}
Then sets media.clips.source_gcs_uri for the clip (creates clip if absent).
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.media.repository import ClipRepository

try:
    from google.cloud import storage
except Exception as e:
    print("ERROR: google-cloud-storage not installed or ADC not set.")
    print("Install: pip install google-cloud-storage")
    print("Run: gcloud auth application-default login")
    sys.exit(2)

PROJECT_ID = os.getenv('GCP_PROJECT', 'heartbeat-474020')
LAKE_BUCKET = os.getenv('MEDIA_LAKE_BUCKET', f'{PROJECT_ID}-lake')


def upload_to_lake(local_path: Path, team: str, season: str, game_id: str) -> str:
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(LAKE_BUCKET)
    lake_path = f"media/raw/{team}/{season}/{game_id}/{local_path.name}"
    blob = bucket.blob(lake_path)
    blob.upload_from_filename(str(local_path), content_type="video/mp4")
    return f"gs://{LAKE_BUCKET}/{lake_path}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', required=True, help='Local path to master video (mp4)')
    p.add_argument('--team', required=True)
    p.add_argument('--season', required=True)
    p.add_argument('--game_id', required=True)
    p.add_argument('--clip_id', required=True)
    args = p.parse_args()

    local = Path(args.file)
    if not local.exists():
        print(f"ERROR: file not found: {local}")
        sys.exit(1)

    # Upload to lake
    lake_uri = upload_to_lake(local, args.team.upper(), args.season, args.game_id)
    print(f"✓ Uploaded to lake: {lake_uri}")

    # Update Postgres
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('ERROR: DATABASE_URL not set')
        sys.exit(2)

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        repo = ClipRepository(session)
        clip = repo.get_clip_by_id(args.clip_id)
        if not clip:
            # Create a minimal clip record if absent
            clip = repo.create_clip(
                clip_id=args.clip_id,
                player_id='',
                team_code=args.team.upper(),
                game_id=args.game_id,
                event_type='INGEST',
                start_timecode_s=0.0,
                end_timecode_s=0.0,
                duration_s=1.0,
            )
        # Set source_gcs_uri
        clip.source_gcs_uri = lake_uri
        session.commit()
        print(f"✓ Updated clip {clip.clip_id} with source_gcs_uri")
    finally:
        session.close()


if __name__ == '__main__':
    main()
