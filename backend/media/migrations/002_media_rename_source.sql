-- HeartBeat Engine - Media Migration
-- Rename column source_video -> source_gcs_uri in media.clips (if exists)

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='media' AND table_name='clips' AND column_name='source_video'
    ) THEN
        ALTER TABLE media.clips RENAME COLUMN source_video TO source_gcs_uri;
    END IF;
END$$;


