-- BigQuery DDL for NHL Market Analytics
-- Project: heartbeat-474020
-- Dataset: market

-- Create dataset if not exists
CREATE SCHEMA IF NOT EXISTS `heartbeat-474020.market`
OPTIONS(
  location="us-central1",
  description="NHL market analytics: contracts, cap management, trades, and market comparables"
);

-- ==========================================
-- EXTERNAL TABLES (Point to GCS Parquet)
-- Cost-effective for historical queries
-- ==========================================

-- Player Contracts External Table
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.market.players_contracts_external`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-market-data/contracts/players_contracts_*.parquet']
);

-- Contract Performance Index External Table
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.market.contract_performance_index_external`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-market-data/performance_index/contract_performance_index_*.parquet']
);

-- Team Cap Management External Table
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.market.team_cap_management_external`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-market-data/cap_management/team_cap_management_*.parquet']
);

-- Trade History External Table
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.market.trade_history_external`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-market-data/trades/trade_history_*.parquet']
);

-- Market Comparables External Table
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.market.market_comparables_external`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-market-data/comparables/market_comparables_*.parquet']
);

-- ==========================================
-- NATIVE TABLES (Optimized for queries)
-- Current + last season for 90% of queries
-- ==========================================

-- Player Contracts Native Table
CREATE OR REPLACE TABLE `heartbeat-474020.market.players_contracts`
PARTITION BY DATE_TRUNC(sync_date, MONTH)
CLUSTER BY team_abbrev, position, contract_status
AS SELECT * FROM `heartbeat-474020.market.players_contracts_external`
WHERE season IN ('2024-2025', '2025-2026');

-- Contract Performance Index Native Table
CREATE OR REPLACE TABLE `heartbeat-474020.market.contract_performance_index`
PARTITION BY DATE_TRUNC(TIMESTAMP_TRUNC(last_calculated, DAY), MONTH)
CLUSTER BY season
AS SELECT * FROM `heartbeat-474020.market.contract_performance_index_external`
WHERE season IN ('2024-2025', '2025-2026');

-- Team Cap Management Native Table
CREATE OR REPLACE TABLE `heartbeat-474020.market.team_cap_management`
PARTITION BY DATE_TRUNC(sync_date, MONTH)
CLUSTER BY team_abbrev, season
AS SELECT * FROM `heartbeat-474020.market.team_cap_management_external`
WHERE season IN ('2024-2025', '2025-2026');

-- Trade History Native Table
CREATE OR REPLACE TABLE `heartbeat-474020.market.trade_history`
PARTITION BY DATE_TRUNC(trade_date, MONTH)
CLUSTER BY season
AS SELECT * FROM `heartbeat-474020.market.trade_history_external`
WHERE trade_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR);

-- Market Comparables Native Table  
CREATE OR REPLACE TABLE `heartbeat-474020.market.market_comparables`
PARTITION BY DATE_TRUNC(calculation_date, MONTH)
CLUSTER BY position, season
AS SELECT * FROM `heartbeat-474020.market.market_comparables_external`
WHERE season IN ('2024-2025', '2025-2026');

-- ==========================================
-- VIEWS FOR COMMON QUERIES
-- ==========================================

-- Active Contracts View (Most common query pattern)
CREATE OR REPLACE VIEW `heartbeat-474020.market.active_contracts` AS
SELECT 
    c.*,
    p.performance_index,
    p.contract_efficiency,
    p.market_value,
    p.surplus_value,
    p.status as performance_status
FROM `heartbeat-474020.market.players_contracts` c
LEFT JOIN `heartbeat-474020.market.contract_performance_index` p
    ON c.nhl_player_id = p.nhl_player_id 
    AND c.season = p.season
WHERE c.contract_status = 'active';

-- Team Cap Summary View
CREATE OR REPLACE VIEW `heartbeat-474020.market.team_cap_summary` AS
SELECT 
    t.team_abbrev,
    t.season,
    t.cap_ceiling,
    t.cap_hit_total,
    t.cap_space,
    t.ltir_pool,
    t.deadline_cap_space,
    t.contracts_expiring,
    COUNT(c.nhl_player_id) as active_contracts,
    SUM(c.cap_hit) as total_cap_hit_check,
    AVG(c.cap_hit) as avg_contract_value
FROM `heartbeat-474020.market.team_cap_management` t
LEFT JOIN `heartbeat-474020.market.players_contracts` c
    ON t.team_abbrev = c.team_abbrev 
    AND t.season = c.season
    AND c.contract_status = 'active'
GROUP BY 1,2,3,4,5,6,7,8;

-- Contract Efficiency Leaders View
CREATE OR REPLACE VIEW `heartbeat-474020.market.contract_efficiency_leaders` AS
SELECT 
    c.nhl_player_id,
    c.full_name,
    c.team_abbrev,
    c.position,
    c.cap_hit,
    p.contract_efficiency,
    p.surplus_value,
    p.performance_percentile,
    p.status
FROM `heartbeat-474020.market.players_contracts` c
INNER JOIN `heartbeat-474020.market.contract_performance_index` p
    ON c.nhl_player_id = p.nhl_player_id 
    AND c.season = p.season
WHERE c.contract_status = 'active'
    AND c.cap_hit > 1000000
    AND p.contract_efficiency IS NOT NULL
ORDER BY p.contract_efficiency DESC
LIMIT 100;

-- Recent Trades View
CREATE OR REPLACE VIEW `heartbeat-474020.market.recent_trades` AS
SELECT *
FROM `heartbeat-474020.market.trade_history`
WHERE trade_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY trade_date DESC;

-- ==========================================
-- SCHEDULED QUERIES (Setup separately)
-- ==========================================

-- Schedule: Daily at 10 PM ET
-- Query: Refresh native tables from external tables
-- Transfer type: WRITE_TRUNCATE for current season data

