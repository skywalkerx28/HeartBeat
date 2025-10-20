-- HeartBeat Engine - Ontology Object Views
-- Maps silver tables to canonical object views for LLM consumption
-- Implements schema defined in orchestrator/ontology/schema.yaml

-- =============================================================================
-- OBJECT: Player
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_player` AS
SELECT
  -- Identity
  CAST(player_id AS INT64) AS nhl_player_id,
  player_name AS full_name,
  -- Simple normalization: lower-case and strip non-alphanumerics (diacritics removed via regex)
  LOWER(REGEXP_REPLACE(player_name, r'[^a-zA-Z0-9\s-]', '')) AS name_normalized,

  -- Core fields (best-effort from depth charts)
  position,
  shoots_catches,
  SAFE_CAST(birth_date AS DATE) AS birth_date,
  CAST(birth_country AS STRING) AS birth_country,
  -- Convert imperial to metric where possible
  CAST(ROUND(SAFE_CAST(NULLIF(CAST(height_inches AS STRING), '') AS FLOAT64) * 2.54) AS INT64) AS height_cm,
  CAST(ROUND(SAFE_CAST(NULLIF(CAST(weight_pounds AS STRING), '') AS FLOAT64) * 0.45359237) AS INT64) AS weight_kg,
  team_abbrev AS current_team,
  COALESCE(roster_status, 'active') AS current_status,
  CAST(NULL AS INT64) AS draft_year,
  CAST(NULL AS INT64) AS draft_round,
  CAST(NULL AS INT64) AS draft_pick,

  -- Metadata
  CURRENT_TIMESTAMP() AS last_updated,
  'depth_charts' AS data_source,
  NULL AS profile_uri,

  -- Relationship keys
  team_abbrev AS rel_current_team

FROM `heartbeat-474020.raw.depth_charts_parquet`
WHERE snapshot_date = (
  SELECT MAX(snapshot_date) FROM `heartbeat-474020.raw.depth_charts_parquet`
)
GROUP BY player_id, player_name, position, shoots_catches, birth_date, birth_country,
         height_inches, weight_pounds, team_abbrev, roster_status;

-- =============================================================================
-- OBJECT: Team
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_team` AS
SELECT
  -- Identity
  team_abbrev,
  team_abbrev AS team_name,  -- TODO: map to full names in a lookup table
  team_abbrev AS team_full_name,

  -- Core fields  
  CASE 
    WHEN team_abbrev IN ('BOS', 'BUF', 'DET', 'FLA', 'MTL', 'OTT', 'TBL', 'TOR') THEN 'Atlantic'
    WHEN team_abbrev IN ('CAR', 'CBJ', 'NJD', 'NYI', 'NYR', 'PHI', 'PIT', 'WSH') THEN 'Metropolitan'
    WHEN team_abbrev IN ('CHI', 'COL', 'DAL', 'MIN', 'NSH', 'STL', 'UTA', 'WPG') THEN 'Central'
    WHEN team_abbrev IN ('ANA', 'CGY', 'EDM', 'LAK', 'SEA', 'SJS', 'VAN', 'VGK') THEN 'Pacific'
  END AS division,
  CASE
    WHEN team_abbrev IN ('BOS', 'BUF', 'DET', 'FLA', 'MTL', 'OTT', 'TBL', 'TOR', 'CAR', 'CBJ', 'NJD', 'NYI', 'NYR', 'PHI', 'PIT', 'WSH') THEN 'Eastern'
    ELSE 'Western'
  END AS conference,
  CAST(NULL AS STRING) AS venue_name,
  CAST(NULL AS INT64) AS founded_year,
  CAST(NULL AS STRING) AS current_season_record,

  -- Metadata
  CURRENT_TIMESTAMP() AS last_updated,
  CONCAT('gs://heartbeat-474020-lake/silver/dim/depth_charts/', team_abbrev, '/') AS depth_chart_uri

FROM (
  SELECT DISTINCT team_abbrev 
  FROM `heartbeat-474020.raw.depth_charts_parquet`
  WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM `heartbeat-474020.raw.depth_charts_parquet`)
);

-- =============================================================================
-- OBJECT: Game
-- =============================================================================

-- Game objects from union of PBP events (core.fact_pbp_events_all)
-- Fields not derivable from events are left NULL for now
-- Fallback placeholder (replace with PBP union when available)
CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_game` AS
SELECT
  CAST(NULL AS INT64) AS game_id,
  CAST(NULL AS STRING) AS season,
  CAST(NULL AS STRING) AS game_type,
  CAST(NULL AS DATE) AS game_date,
  CAST(NULL AS TIMESTAMP) AS game_datetime,
  CAST(NULL AS STRING) AS home_team,
  CAST(NULL AS STRING) AS away_team,
  CAST(NULL AS INT64) AS home_score,
  CAST(NULL AS INT64) AS away_score,
  CAST(NULL AS STRING) AS game_state,
  CAST(NULL AS STRING) AS venue,
  CAST(NULL AS INT64) AS attendance,
  CURRENT_TIMESTAMP() AS last_updated,
  CAST(NULL AS STRING) AS pbp_uri,
  CAST(NULL AS INT64) AS event_count
FROM UNNEST([1]) AS _
WHERE FALSE;

-- =============================================================================
-- OBJECT: Event
-- =============================================================================

-- Event objects mapped from union of PBP events (core.fact_pbp_events_all)
-- Fallback placeholder (replace with PBP union when available)
CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_event` AS
SELECT
  CAST(NULL AS INT64) AS game_id,
  CAST(NULL AS INT64) AS event_idx,
  CAST(NULL AS INT64) AS period,
  CAST(NULL AS STRING) AS period_time,
  CAST(NULL AS STRING) AS period_time_remaining,
  CAST(NULL AS STRING) AS event_type,
  CAST(NULL AS STRING) AS team,
  CAST(NULL AS INT64) AS player_id,
  CAST(NULL AS STRING) AS player_name,
  CAST(NULL AS INT64) AS secondary_player_id,
  CAST(NULL AS FLOAT64) AS x_coord,
  CAST(NULL AS FLOAT64) AS y_coord,
  CAST(NULL AS STRING) AS shot_type,
  CAST(NULL AS STRING) AS strength,
  CURRENT_TIMESTAMP() AS extraction_time,
  CAST(NULL AS STRING) AS source_uri,
  CAST(NULL AS STRING) AS season
FROM UNNEST([1]) AS _
WHERE FALSE;

-- =============================================================================
-- OBJECT: Contract
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_contract` AS
SELECT
  -- Identity (by player + start season)
  CAST(nhl_player_id AS INT64) AS player_id,
  full_name AS player_name,

  -- Core fields
  team_abbrev AS team,
  FORMAT_DATE('%Y', DATE(contract_start_date)) || '-' || FORMAT_DATE('%Y', DATE_ADD(DATE(contract_start_date), INTERVAL 1 YEAR)) AS contract_start_season,
  FORMAT_DATE('%Y', DATE(contract_end_date)) || '-' || FORMAT_DATE('%Y', DATE_ADD(DATE(contract_end_date), INTERVAL 1 YEAR)) AS contract_end_season,
  CAST(contract_years_total AS INT64) AS contract_years,
  CAST(cap_hit AS NUMERIC) AS aav,  -- Treat cap hit as AAV
  CAST(cap_hit * SAFE_CAST(contract_years_total AS NUMERIC) AS NUMERIC) AS total_value,
  CAST(contract_type AS STRING) AS contract_type,
  CAST(signing_date AS DATE) AS signing_date,
  CAST(cap_hit AS NUMERIC) AS cap_hit,
  CAST(signing_age AS INT64) AS signing_age,
  CASE WHEN LOWER(contract_type) IN ('ufa','rfa') THEN UPPER(contract_type) ELSE 'club_control' END AS expiry_status,

  -- Metadata
  CURRENT_TIMESTAMP() AS last_updated,
  CONCAT('gs://heartbeat-474020-lake/silver/market/contracts/') AS source_uri

FROM `heartbeat-474020.raw.players_contracts_parquet`
WHERE cap_hit IS NOT NULL;

-- =============================================================================
-- OBJECT: DepthChart
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_depth_chart` AS
SELECT
  -- Identity
  team_abbrev,
  CAST(snapshot_date AS DATE) AS snapshot_date,

  -- Core fields
  CAST(player_id AS INT64) AS player_id,
  player_name,
  position,
  CAST(NULL AS INT64) AS line_number,
  shoots_catches,
  CAST(NULL AS INT64) AS games_played,
  CAST(NULL AS INT64) AS goals,
  CAST(NULL AS INT64) AS assists,

  -- Additional roster context often used by UI/LLM
  CAST(jersey_number AS STRING) AS jersey_number,
  CAST(roster_status AS STRING) AS roster_status,
  CAST(age AS STRING) AS age,
  CAST(headshot AS STRING) AS headshot,

  -- Metadata
  CURRENT_TIMESTAMP() AS last_updated,
  CONCAT('gs://heartbeat-474020-lake/silver/dim/depth_charts/', team_abbrev, '_', REPLACE(CAST(snapshot_date AS STRING), '-', '_'), '.parquet') AS source_uri,

  -- Relationship keys
  team_abbrev AS rel_team,
  player_id AS rel_player

FROM `heartbeat-474020.raw.depth_charts_parquet`;

-- =============================================================================
-- OBJECT: PlayerSeasonProfile
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_player_season_profile` AS
SELECT
  -- Identity
  CAST(player_id AS INT64) AS player_id,
  CAST(NULL AS STRING) AS player_name,
  season,

  -- Core fields (aligned to ontology where possible)
  CAST(NULL AS STRING) AS team,
  CAST(NULL AS STRING) AS position,
  CAST(games_count AS INT64) AS games_played,
  CAST(NULL AS INT64) AS goals,
  CAST(NULL AS INT64) AS assists,
  CAST(NULL AS INT64) AS points,
  CAST(NULL AS INT64) AS plus_minus,
  CAST(NULL AS INT64) AS pim,
  CAST(NULL AS INT64) AS shots,
  CAST(NULL AS FLOAT64) AS shooting_pct,
  CAST(ROUND(SAFE_DIVIDE(toi_game_sec, NULLIF(games_count, 0)), 2) AS FLOAT64) AS toi_per_game,
  CAST(NULL AS FLOAT64) AS faceoff_pct,

  -- Advanced metrics (from aggregated JSON)
  CAST(NULL AS FLOAT64) AS xg,
  CAST(NULL AS FLOAT64) AS xg_per_60,
  CAST(NULL AS FLOAT64) AS corsi_for_pct,
  CAST(NULL AS FLOAT64) AS fenwick_for_pct,
  CAST(NULL AS FLOAT64) AS war,

  -- Metadata
  CURRENT_TIMESTAMP() AS last_updated,
  NULL AS model_version,
  'player_profiles_advanced_json' AS feature_set_ref,
  CONCAT('gs://heartbeat-474020-lake/silver/player_profiles/parquet/season=', season, '/') AS source_uri

FROM `heartbeat-474020.raw.player_season_profiles_parquet`;

-- =============================================================================
-- OBJECT: TeamSeasonProfile
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_team_season_profile` AS
SELECT
  CAST(NULL AS STRING) AS team_abbrev,
  CAST(NULL AS STRING) AS team_name,
  CAST(NULL AS STRING) AS season,
  CAST(NULL AS INT64) AS games_played,
  CAST(NULL AS INT64) AS wins,
  CAST(NULL AS INT64) AS losses,
  CAST(NULL AS INT64) AS otl,
  CAST(NULL AS INT64) AS points,
  CAST(NULL AS FLOAT64) AS points_pct,
  CAST(NULL AS INT64) AS goals_for,
  CAST(NULL AS INT64) AS goals_against,
  CAST(NULL AS INT64) AS goal_diff,
  CAST(NULL AS FLOAT64) AS pp_pct,
  CAST(NULL AS FLOAT64) AS pk_pct,
  CAST(NULL AS FLOAT64) AS shots_for_per_game,
  CAST(NULL AS FLOAT64) AS shots_against_per_game,
  CAST(NULL AS FLOAT64) AS faceoff_win_pct,
  CAST(NULL AS FLOAT64) AS xgf_per_game,
  CAST(NULL AS FLOAT64) AS xga_per_game,
  CAST(NULL AS FLOAT64) AS corsi_for_pct,
  CAST(NULL AS FLOAT64) AS fenwick_for_pct,
  CAST(NULL AS FLOAT64) AS pdo,
  CURRENT_TIMESTAMP() AS last_updated,
  CAST(NULL AS STRING) AS source_uri
FROM UNNEST([1]) AS _
WHERE FALSE;

-- =============================================================================
-- OBJECT: Clip (placeholder - implement when clip data available)
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_clip` AS
SELECT
  CAST(NULL AS STRING) AS clip_id,
  CAST(NULL AS INT64) AS game_id,
  CAST(NULL AS STRING) AS event_id,
  CAST(NULL AS STRING) AS clip_title,
  CAST(NULL AS STRING) AS clip_description,
  CAST(NULL AS INT64) AS duration_seconds,
  CAST(NULL AS STRING) AS video_url,
  CAST(NULL AS STRING) AS thumbnail_url,
  CAST(NULL AS STRING) AS event_type,
  CAST(NULL AS INT64) AS period,
  CAST(NULL AS STRING) AS game_time,
  CAST(NULL AS STRING) AS team,
  CAST(NULL AS ARRAY<INT64>) AS players_involved,
  CURRENT_TIMESTAMP() AS created_at,
  'internal' AS source
FROM UNNEST([1]) AS _
WHERE FALSE;  -- Empty view until clip data is available

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Count objects by type
SELECT 'Player' AS object_type, COUNT(*) AS count FROM `heartbeat-474020.raw.objects_player`
UNION ALL
SELECT 'Team', COUNT(*) FROM `heartbeat-474020.raw.objects_team`
UNION ALL
SELECT 'Game', COUNT(*) FROM `heartbeat-474020.raw.objects_game`
UNION ALL
SELECT 'Event', COUNT(*) FROM `heartbeat-474020.raw.objects_event`
UNION ALL
SELECT 'Contract', COUNT(*) FROM `heartbeat-474020.raw.objects_contract`
UNION ALL
SELECT 'DepthChart', COUNT(*) FROM `heartbeat-474020.raw.objects_depth_chart`
UNION ALL
SELECT 'PlayerSeasonProfile', COUNT(*) FROM `heartbeat-474020.raw.objects_player_season_profile`
UNION ALL
SELECT 'TeamSeasonProfile', COUNT(*) FROM `heartbeat-474020.raw.objects_team_season_profile`;

-- =============================================================================
-- OBJECT: GameMetrics (index over extracted metrics JSON)
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_game_metrics` AS
SELECT
  SAFE_CAST(game_code AS INT64) AS game_id,
  CASE WHEN LENGTH(season) = 8 THEN CONCAT(SUBSTR(season,1,4), '-', SUBSTR(season,5,4)) ELSE season END AS season,
  SAFE_CAST(game_date AS DATE) AS game_date,
  CAST(team_a AS STRING) AS away_team,
  CAST(team_b AS STRING) AS home_team,
  CURRENT_TIMESTAMP() AS last_updated,
  CONCAT('gs://heartbeat-474020-lake/bronze/extracted_metrics/season=', season, '/', source_file) AS source_uri
FROM `heartbeat-474020.raw.game_metrics_index_parquet`;

-- =============================================================================
-- OBJECT: TeamGameMetrics (team-filterable index over extracted metrics JSON)
-- =============================================================================

CREATE OR REPLACE VIEW `heartbeat-474020.raw.objects_team_game_metrics` AS
SELECT
  CONCAT(CAST(team_abbrev AS STRING), '_', CAST(game_code AS STRING)) AS row_id,
  CAST(team_abbrev AS STRING) AS team_abbrev,
  CASE WHEN LENGTH(season) = 8 THEN CONCAT(SUBSTR(season,1,4), '-', SUBSTR(season,5,4)) ELSE season END AS season,
  SAFE_CAST(game_code AS INT64) AS game_id,
  SAFE_CAST(game_date AS DATE) AS game_date,
  CAST(opponent AS STRING) AS opponent,
  CURRENT_TIMESTAMP() AS last_updated,
  CONCAT('gs://heartbeat-474020-lake/bronze/extracted_metrics/season=', season, '/', source_file) AS source_uri
FROM `heartbeat-474020.raw.team_game_metrics_parquet`;
