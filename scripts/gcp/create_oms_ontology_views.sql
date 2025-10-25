-- HeartBeat Engine - OMS Ontology Views
-- BigQuery views for Ontology Metadata Service
-- 
-- CRITICAL: OMS does NOT copy data. These views point to existing data in BigQuery.
-- The OMS resolvers query these views; data stays in place.
--
-- Dataset: ontology (semantic layer)
-- Source datasets: raw, core, analytics

-- =============================================================================
-- OBJECT VIEWS - Canonical representations of NHL entities
-- =============================================================================

-- Player Object (Active NHL Roster Players)
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.objects_player` AS
SELECT
  -- Primary Key (OMS convention: {object}Id camelCase)
  CAST(player_id AS STRING) AS playerId,
  
  -- Core Properties
  player_name AS name,
  position,
  CAST(jersey_number AS INT64) AS jerseyNumber,
  team_abbrev AS teamId,
  
  -- Physical attributes
  SAFE_CAST(birth_date AS DATE) AS birthDate,
  CAST(birth_country AS STRING) AS birthCountry,
  CAST(ROUND(SAFE_CAST(NULLIF(CAST(height_inches AS STRING), '') AS FLOAT64) * 2.54) AS INT64) AS height,
  CAST(ROUND(SAFE_CAST(NULLIF(CAST(weight_pounds AS STRING), '') AS FLOAT64) * 0.45359237) AS INT64) AS weight,
  shoots_catches AS shootsCatches,
  
  -- Draft info (null for now, can join with draft data)
  CAST(NULL AS INT64) AS draftYear,
  CAST(NULL AS INT64) AS draftRound,
  CAST(NULL AS INT64) AS draftOverall,
  
  -- Roster status
  COALESCE(roster_status, 'Active') AS rosterStatus

FROM `heartbeat-474020.raw.depth_charts_parquet`
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM `heartbeat-474020.raw.depth_charts_parquet`)
  AND player_id IS NOT NULL
GROUP BY player_id, player_name, position, jersey_number, team_abbrev,
         birth_date, birth_country, height_inches, weight_pounds, 
         shoots_catches, roster_status;


-- Team Object
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.objects_team` AS
SELECT
  -- Primary Key
  team_abbrev AS teamId,
  
  -- Core Properties
  team_abbrev AS name,
  team_abbrev AS abbreviation,
  CAST(NULL AS STRING) AS city,
  
  -- Division and Conference
  CASE 
    WHEN team_abbrev IN ('BOS', 'BUF', 'DET', 'FLA', 'MTL', 'OTT', 'TBL', 'TOR') THEN 'Atlantic'
    WHEN team_abbrev IN ('CAR', 'CBJ', 'NJD', 'NYI', 'NYR', 'PHI', 'PIT', 'WSH') THEN 'Metropolitan'
    WHEN team_abbrev IN ('CHI', 'COL', 'DAL', 'MIN', 'NSH', 'STL', 'UTA', 'WPG') THEN 'Central'
    WHEN team_abbrev IN ('ANA', 'CGY', 'EDM', 'LAK', 'SEA', 'SJS', 'VAN', 'VGK') THEN 'Pacific'
  END AS division,
  CASE
    WHEN team_abbrev IN ('BOS', 'BUF', 'DET', 'FLA', 'MTL', 'OTT', 'TBL', 'TOR', 
                         'CAR', 'CBJ', 'NJD', 'NYI', 'NYR', 'PHI', 'PIT', 'WSH') THEN 'Eastern'
    ELSE 'Western'
  END AS conference,
  
  CAST(NULL AS STRING) AS venueId,
  CAST(NULL AS INT64) AS foundedYear

FROM (
  SELECT DISTINCT team_abbrev 
  FROM `heartbeat-474020.raw.depth_charts_parquet`
  WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM `heartbeat-474020.raw.depth_charts_parquet`)
);


-- Contract Object
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.objects_contract` AS
SELECT
  -- Primary Key (composite: player + season)
  CONCAT(CAST(nhl_player_id AS STRING), '_', 
         FORMAT_DATE('%Y', DATE(contract_start_date))) AS contractId,
  
  -- Foreign Keys
  CAST(nhl_player_id AS STRING) AS playerId,
  team_abbrev AS teamId,
  
  -- Contract Details
  CAST(contract_type AS STRING) AS contractType,
  SAFE_CAST(contract_start_date AS DATE) AS startDate,
  SAFE_CAST(contract_end_date AS DATE) AS endDate,
  
  -- Financials (restricted by policy)
  CAST(cap_hit * SAFE_CAST(contract_years_total AS NUMERIC) AS FLOAT64) AS totalValue,
  CAST(cap_hit AS FLOAT64) AS annualCapHit,
  CAST(NULL AS FLOAT64) AS signingBonus,
  CAST(NULL AS FLOAT64) AS performanceBonus,
  
  -- Clauses
  CAST(NULL AS BOOL) AS hasNMC,
  CAST(NULL AS BOOL) AS hasNTC,
  
  -- Status
  CASE 
    WHEN DATE(contract_end_date) <= DATE_ADD(CURRENT_DATE(), INTERVAL 1 YEAR) THEN TRUE 
    ELSE FALSE 
  END AS isExpiring,
  CAST(contract_years_total AS INT64) AS yearsSigned

FROM `heartbeat-474020.raw.players_contracts_parquet`
WHERE cap_hit IS NOT NULL
  AND nhl_player_id IS NOT NULL;


-- Prospect Object (placeholder - to be populated)
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.objects_prospect` AS
SELECT
  CAST(NULL AS STRING) AS prospectId,
  CAST(NULL AS STRING) AS name,
  CAST(NULL AS STRING) AS nhlTeamId,
  CAST(NULL AS STRING) AS currentLeague,
  CAST(NULL AS STRING) AS currentTeam,
  CAST(NULL AS STRING) AS position,
  CAST(NULL AS DATE) AS birthDate,
  CAST(NULL AS STRING) AS birthCity,
  CAST(NULL AS STRING) AS birthCountry,
  CAST(NULL AS INT64) AS height,
  CAST(NULL AS INT64) AS weight,
  CAST(NULL AS STRING) AS shootsCatches,
  CAST(NULL AS INT64) AS draftYear,
  CAST(NULL AS INT64) AS draftRound,
  CAST(NULL AS INT64) AS draftOverall,
  CAST(NULL AS STRING) AS contractStatus,
  CAST(NULL AS STRING) AS developmentStatus
FROM UNNEST([1]) AS _
WHERE FALSE;


-- =============================================================================
-- LINK VIEWS - Relationships between objects
-- =============================================================================

-- Link: Team → Players (one-to-many)
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.links_team_players` AS
SELECT
  team_abbrev AS teamId,
  CAST(player_id AS STRING) AS playerId
FROM `heartbeat-474020.raw.depth_charts_parquet`
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM `heartbeat-474020.raw.depth_charts_parquet`)
  AND player_id IS NOT NULL
  AND team_abbrev IS NOT NULL
GROUP BY team_abbrev, player_id;


-- Link: Player → Contracts (one-to-many)
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.links_player_contracts` AS
SELECT
  CAST(nhl_player_id AS STRING) AS playerId,
  CONCAT(CAST(nhl_player_id AS STRING), '_', 
         FORMAT_DATE('%Y', DATE(contract_start_date))) AS contractId
FROM `heartbeat-474020.raw.players_contracts_parquet`
WHERE nhl_player_id IS NOT NULL
  AND cap_hit IS NOT NULL;


-- Link: Team → Prospects (one-to-many) - placeholder
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.links_team_prospects` AS
SELECT
  CAST(NULL AS STRING) AS teamId,
  CAST(NULL AS STRING) AS prospectId
FROM UNNEST([1]) AS _
WHERE FALSE;


-- Link: Scout → Prospects (many-to-many) - placeholder
CREATE OR REPLACE VIEW `heartbeat-474020.ontology.links_scout_prospects` AS
SELECT
  CAST(NULL AS STRING) AS scoutId,
  CAST(NULL AS STRING) AS prospectId,
  CAST(NULL AS STRING) AS priority,
  CAST(NULL AS DATE) AS assignedDate
FROM UNNEST([1]) AS _
WHERE FALSE;


-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Count all objects
SELECT 'Player' AS object_type, COUNT(*) AS count 
FROM `heartbeat-474020.ontology.objects_player`
UNION ALL
SELECT 'Team', COUNT(*) 
FROM `heartbeat-474020.ontology.objects_team`
UNION ALL
SELECT 'Contract', COUNT(*) 
FROM `heartbeat-474020.ontology.objects_contract`
UNION ALL
SELECT 'Prospect', COUNT(*) 
FROM `heartbeat-474020.ontology.objects_prospect`;

-- Count all links
SELECT 'team_players' AS link_type, COUNT(*) AS count 
FROM `heartbeat-474020.ontology.links_team_players`
UNION ALL
SELECT 'player_contracts', COUNT(*) 
FROM `heartbeat-474020.ontology.links_player_contracts`;

