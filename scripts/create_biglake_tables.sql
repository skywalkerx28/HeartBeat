-- HeartBeat Engine - BigLake External Tables Creation
-- Creates external tables pointing to GCS silver Parquet files

-- Step 1: Create BigLake connection (run once)
-- Note: This must be run in BigQuery console or via bq CLI
-- CREATE EXTERNAL CONNECTION `heartbeat-474020.US.lake-connection`
-- CONNECTION_TYPE = 'CLOUD_RESOURCE'
-- LOCATION = 'us-east1';

-- After creating connection, grant GCS permissions to the BigLake service account:
-- BQ_SA=$(bq show --connection --location=us-east1 --project_id=heartbeat-474020 lake-connection | grep serviceAccountId | cut -d'"' -f4)
-- gsutil iam ch serviceAccount:$BQ_SA:objectViewer gs://heartbeat-474020-lake

-- External Table: Roster Snapshots (unified from depth charts)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.rosters_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/dim/rosters/*.parquet'],
  description = 'NHL unified roster snapshots (converted from depth_charts CSVs)'
);

-- External Table: Depth Charts (per-team detailed rosters)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.depth_charts_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/dim/depth_charts/*.parquet'],
  description = 'NHL team depth charts with roster status, contract status, prospects'
);

-- External Table: Player Profile Indexes
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.player_profiles_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/dim/player_profiles/*.parquet'],
  description = 'NHL player advanced profile indexes (game logs, performance metrics)'
);

-- External Tables: Training Outputs (season-partitioned via Hive-style URIs)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.training_event_stream_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/fact/event_stream/season=20232024/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/event_stream/season=20242025/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/event_stream/season=20252026/*.parquet'
  ],
  description = 'Event stream rows per game (season partitioned)'
);

CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.training_next_action_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/fact/next_action/season=20232024/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/next_action/season=20242025/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/next_action/season=20252026/*.parquet'
  ],
  description = 'Next-action training targets (season partitioned)'
);

CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.training_sequence_windows_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/fact/sequence_windows/season=20232024/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/sequence_windows/season=20242025/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/sequence_windows/season=20252026/*.parquet'
  ],
  description = 'Whistle-to-whistle sequence windows (season partitioned)'
);

CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.training_transition_stats_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/fact/transition_stats/season=20232024/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/transition_stats/season=20242025/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/transition_stats/season=20252026/*.parquet'
  ],
  description = 'Action-to-action transition counts (season partitioned)'
);

-- External Tables: Player/Team Season Profiles (compact Parquet, season partitioned)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.player_season_profiles_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/dim/player_season_profiles/season=20242025/player_season_advanced.parquet',
    'gs://heartbeat-474020-lake/silver/dim/player_season_profiles/season=20252026/player_season_advanced.parquet'
  ],
  description = 'Compact player season advanced metrics (one row per player-season)'
);

CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.team_season_profiles_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/dim/team_season_profiles/season=20242025/team_season_advanced.parquet',
    'gs://heartbeat-474020-lake/silver/dim/team_season_profiles/season=20252026/team_season_advanced.parquet'
  ],
  description = 'Compact team season advanced metrics (one row per team-season)'
);

-- NOTE: Several 2025-10-17/18 payloads were malformed on first upload.
-- Temporarily limit JSON externals to the known-good season to avoid job failure.
-- Re-enable additional seasons after cleaning/replacing bad files.
-- Temporarily disable JSON external due to malformed historical payloads.
-- Provide an empty stub view to avoid downstream references breaking.
CREATE OR REPLACE VIEW `heartbeat-474020.raw.extracted_metrics_json` AS
SELECT 1 AS ok FROM UNNEST([1]) AS _ WHERE FALSE;

-- External Table: Play-by-Play Events
-- NOTE: pbp table omitted for now due to nested wildcard URI limitations.
-- Create per-season or per-team external tables later as needed.

-- External Table: Player Contracts (players_contracts only)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.players_contracts_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  -- Accept any season-specific players_contracts_*.parquet
  uris = ['gs://heartbeat-474020-lake/silver/market/contracts/players_contracts_*.parquet'],
  description = 'NHL player contracts and cap information (players_contracts)'
);

-- External Table: League Player Stats (10 seasons of advanced metrics)
-- External Table: League Player Stats
-- Provide explicit season URIs to satisfy single-wildcard constraint
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.league_player_stats_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2015-2016/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2016-2017/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2017-2018/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2018-2019/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2019-2020/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2020-2021/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2021-2022/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2022-2023/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2023-2024/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/league_player_stats/season=2024-2025/*.parquet'
  ],
  description = 'NHL league-wide player stats with advanced metrics (2015-2025)'
);

-- External Table: Extracted Metrics Game Index (compact Parquet)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.game_metrics_index_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/fact/game_metrics_index/season=20242025/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/game_metrics_index/season=20252026/*.parquet'
  ],
  description = 'Per-game extracted metrics index (one row per game)'
);

-- External Table: Extracted Metrics Team-Game Index (compact Parquet)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.team_game_metrics_parquet`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://heartbeat-474020-lake/silver/fact/team_game_metrics/season=20242025/*.parquet',
    'gs://heartbeat-474020-lake/silver/fact/team_game_metrics/season=20252026/*.parquet'
  ],
  description = 'Per-team per-game extracted metrics index (two rows per game)'
);

-- External Table: Extracted Metrics Team Pointers (JSON, lightweight)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.raw.extracted_metrics_pointers_json`
WITH CONNECTION `heartbeat-474020.US.lake-connection`
OPTIONS (
  format = 'JSON',
  uris = [
    'gs://heartbeat-474020-lake/bronze/extracted_metrics/by_team/season=20242025/team=*/*.json',
    'gs://heartbeat-474020-lake/bronze/extracted_metrics/by_team/season=20252026/team=*/*.json'
  ],
  description = 'Pointers to canonical per-game extracted metrics JSON for each team and season'
);

-- Verify tables created successfully
SELECT 
  table_name,
  table_type
FROM `heartbeat-474020.raw.INFORMATION_SCHEMA.TABLES`
WHERE table_type = 'EXTERNAL'
ORDER BY table_name;
