-- HeartBeat Engine - Media Schema Migration
-- Production-grade video clip metadata storage in Cloud SQL Postgres
-- 
-- Architecture:
--   - Metadata: Postgres (system of record)
--   - Assets: GCS bucket (MP4, HLS, thumbnails)
--   - Delivery: Signed URLs + Cloud CDN

-- Create media schema
CREATE SCHEMA IF NOT EXISTS media;

-- Clips table (master metadata)
CREATE TABLE IF NOT EXISTS media.clips (
    id SERIAL PRIMARY KEY,
    clip_id VARCHAR(64) UNIQUE NOT NULL,  -- Unique external ID (hash-based)
    
    -- Context
    player_id VARCHAR(20) NOT NULL,
    player_name VARCHAR(255),
    team_code VARCHAR(10) NOT NULL,
    opponent_code VARCHAR(10),
    game_id VARCHAR(20) NOT NULL,
    game_date DATE,
    season VARCHAR(10),
    period INTEGER,
    
    -- Event
    event_type VARCHAR(50) NOT NULL,
    outcome VARCHAR(50),
    zone VARCHAR(50),
    start_timecode_s DOUBLE PRECISION NOT NULL,
    end_timecode_s DOUBLE PRECISION NOT NULL,
    duration_s DOUBLE PRECISION NOT NULL,
    
    -- Processing metadata
    source_gcs_uri VARCHAR(512),
    processing_status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, ready, failed
    processing_time_s DOUBLE PRECISION,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT ck_clip_status CHECK (processing_status IN ('pending', 'processing', 'ready', 'failed')),
    CONSTRAINT ck_clip_duration CHECK (duration_s > 0 AND duration_s <= 300)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS ix_clips_player_id ON media.clips(player_id);
CREATE INDEX IF NOT EXISTS ix_clips_team_code ON media.clips(team_code);
CREATE INDEX IF NOT EXISTS ix_clips_game_id ON media.clips(game_id);
CREATE INDEX IF NOT EXISTS ix_clips_event_type ON media.clips(event_type);
CREATE INDEX IF NOT EXISTS ix_clips_created_at ON media.clips(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_clips_status ON media.clips(processing_status);
CREATE INDEX IF NOT EXISTS ix_clips_composite ON media.clips(player_id, created_at DESC);

-- Clip assets (MP4, HLS, thumbnails stored in GCS)
CREATE TABLE IF NOT EXISTS media.clip_assets (
    id SERIAL PRIMARY KEY,
    clip_id INTEGER NOT NULL REFERENCES media.clips(id) ON DELETE CASCADE,
    
    -- Asset details
    asset_type VARCHAR(20) NOT NULL,  -- mp4, hls_playlist, hls_segment, thumbnail, thumbnail_grid
    gcs_uri VARCHAR(512) NOT NULL,  -- gs://bucket/path/to/asset
    cdn_path VARCHAR(512),  -- Optional CDN path if different from GCS
    
    -- Metadata
    file_size_bytes BIGINT,
    duration_s DOUBLE PRECISION,  -- For video assets
    width INTEGER,
    height INTEGER,
    codec VARCHAR(50),
    bitrate_kbps INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT ck_asset_type CHECK (
        asset_type IN ('mp4', 'hls_playlist', 'hls_segment', 'thumbnail', 'thumbnail_grid', 'dash_manifest')
    ),
    CONSTRAINT uq_clip_asset_type UNIQUE (clip_id, asset_type, gcs_uri)
);

CREATE INDEX IF NOT EXISTS ix_clip_assets_clip_id ON media.clip_assets(clip_id);
CREATE INDEX IF NOT EXISTS ix_clip_assets_type ON media.clip_assets(asset_type);

-- Clip tags (for categorization and search)
CREATE TABLE IF NOT EXISTS media.clip_tags (
    id SERIAL PRIMARY KEY,
    clip_id INTEGER NOT NULL REFERENCES media.clips(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    tag_type VARCHAR(50),  -- auto, manual, ai_generated
    confidence DOUBLE PRECISION,  -- For AI-generated tags
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_clip_tag UNIQUE (clip_id, tag)
);

CREATE INDEX IF NOT EXISTS ix_clip_tags_clip_id ON media.clip_tags(clip_id);
CREATE INDEX IF NOT EXISTS ix_clip_tags_tag ON media.clip_tags(tag);
CREATE INDEX IF NOT EXISTS ix_clip_tags_type ON media.clip_tags(tag_type);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION media.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_clips_updated_at BEFORE UPDATE ON media.clips
    FOR EACH ROW EXECUTE FUNCTION media.update_updated_at_column();

-- Comments
COMMENT ON SCHEMA media IS 'Production video clip metadata storage';
COMMENT ON TABLE media.clips IS 'Master clip metadata (assets stored in GCS)';
COMMENT ON TABLE media.clip_assets IS 'Asset variants (MP4, HLS, thumbnails) with GCS URIs';
COMMENT ON TABLE media.clip_tags IS 'Searchable tags for clip categorization';
COMMENT ON COLUMN media.clips.clip_id IS 'External unique ID (hash-based, stable across environments)';
COMMENT ON COLUMN media.clip_assets.gcs_uri IS 'Google Cloud Storage URI (gs://bucket/path)';
COMMENT ON COLUMN media.clip_assets.cdn_path IS 'Optional Cloud CDN path for delivery';

