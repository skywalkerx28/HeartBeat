# HeartBeat Engine - Production Media Architecture

## Overview

Replaced DuckDB with production-grade architecture:
- **Storage**: Google Cloud Storage (GCS) for all video assets
- **Metadata**: Cloud SQL Postgres (`media` schema)
- **Delivery**: Signed URLs + optional Cloud CDN
- **RBAC**: Policy enforcement via existing UserContext

## Path Conventions (multi-tenant)

- Lake masters (immutable, long retention)
  - `gs://heartbeat-474020-lake/media/raw/{TEAM}/{SEASON}/{GAME_ID}/{filename}`
- Delivery artifacts (CDN-friendly)
  - `gs://heartbeat-media/{TEAM}/{SEASON}/{GAME_ID}/{CLIP_ID}/{clip.mp4|playlist.m3u8|thumb.jpg}`

Examples:
- `gs://heartbeat-474020-lake/media/raw/MTL/2025-2026/20031/p1-20251011-MTLvsCHI.mp4`
- `gs://heartbeat-media/MTL/2025-2026/20031/CLIP123/clip.mp4`

## Ingestion Helper (masters → lake)

Use the helper to upload a master into the lake and register the source URI in Postgres:

```bash
# ADC and proxy must be configured
export DATABASE_URL="postgresql+psycopg2://heartbeat:PASSWORD@127.0.0.1:5434/postgres"
export MEDIA_LAKE_BUCKET=heartbeat-474020-lake

python3 scripts/media/ingest_master_to_lake.py \
  --file /path/to/master.mp4 \
  --team MTL --season 2025-2026 --game_id 20031 --clip_id CLIP123
```

This writes `media.clips.source_gcs_uri` and uploads to lake path `media/raw/{TEAM}/{SEASON}/{GAME_ID}/`.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT (Web/Mobile)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Cloud Run)                │
│  • /api/v2/clips/ (list, get)                               │
│  • RBAC enforcement (PolicyEngine + UserContext)            │
│  • Generate signed URLs (60min TTL)                         │
└──────┬────────────────────────────────────┬─────────────────┘
       │                                    │
       │ Query metadata                     │ Generate signed URL
       │                                    │
       ▼                                    ▼
┌────────────────────┐           ┌─────────────────────────┐
│  Cloud SQL Postgres│           │    GCS Buckets          │
│  ┌────────────────┐│           │  Lake: hb-474020-lake   │
│  │ media.clips    ││           │  Media: heartbeat-media │
│  │ media.clip_    ││           │                         │
│  │   assets       ││           │ /media/raw/{TEAM}/{...} │
│  │ media.clip_tags││           └─────────────────────────┘
│  └────────────────┘│           │ (Optional)
│                         │
│                         ▼
│                                 ┌──────────────────────┐
│                                 │   Cloud CDN          │
│                                 │  cdn.heartbeat.com   │
│                                 └──────────────────────┘
```

## Database Schema

### media.clips
- `clip_id` (VARCHAR, unique)
- `player_id`, `team_code`, `game_id`, `event_type`
- `source_gcs_uri` (lake master path)
- `duration_s`, `processing_status`
- Indexes on player_id, team_code, game_id, event_type, created_at DESC

### media.clip_assets
- `asset_type`: mp4 | hls_playlist | thumbnail | hls_segment | thumbnail_grid
- `gcs_uri` (delivery bucket path)

## CDN Enablement (heartbeat-media)

1) Create backend bucket and set up Cloud CDN
```bash
# Backend bucket (via gcloud storage buckets backends or LB backend bucket)
# Example with load balancer (recommended for custom domain + SSL):
# - Create backend bucket pointing to heartbeat-media
# - Create HTTPS LB with managed cert for cdn.heartbeat.com
# - Enable Cloud CDN on backend bucket
```
2) Tune caching
- Cache static assets (HLS segments, thumbnails) aggressively
- Respect signed URLs TTL (60m default, adjust per UX)
3) Configure env
```bash
export MEDIA_CDN_DOMAIN=cdn.heartbeat.com
```

## Setup & Testing

- Initialize schema: `./scripts/media/init_media_schema.sh`
- Verify system: `python3 scripts/media/verify_media_system.py` (DB + GCS)
- Run API: `python3 -m uvicorn backend.main:app --reload`
- Endpoints: `/api/v2/clips/`, `/api/v2/clips/{clip_id}`, `/api/v2/clips/stats/overview`

## Status

- Schema, repository, signed URLs, v2 API, lake/media paths: ✅
- CDN plan and ingestion helper: ✅
- Migration from DuckDB: not required for media; new pipeline writes to Postgres+GCS.

