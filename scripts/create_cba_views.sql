-- HeartBeat Engine - CBA Ontology Views
-- Creates external tables and object views for CBA rules and documents
-- Implements CBARule and CBADocument objects from orchestrator/ontology/schema.yaml

-- =============================================================================
-- STEP 1: Create External Tables (BigLake) over GCS Parquet
-- =============================================================================

-- External Table: CBA Documents Metadata
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.cba.cba_documents_parquet`
WITH CONNECTION `heartbeat-474020.us-east1.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/reference/cba/cba_documents.parquet'],
  description = 'NHL CBA document metadata and lineage (base + amendments)'
);

-- External Table: All CBA Rules (with history)
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.cba.cba_rules_all_parquet`
WITH CONNECTION `heartbeat-474020.us-east1.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/reference/cba/cba_rules_all.parquet'],
  description = 'All CBA structured rules including superseded versions (temporal history)'
);

-- External Table: Current CBA Rules Only
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.cba.cba_rules_current_parquet`
WITH CONNECTION `heartbeat-474020.us-east1.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/reference/cba/cba_rules_current.parquet'],
  description = 'Currently active CBA rules only (no history)'
);

-- Additional external tables for full-document ingestion (optional)

-- External Table: CBA Document Page Text
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.cba.cba_document_text_parquet`
WITH CONNECTION `heartbeat-474020.us-east1.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/reference/cba/cba_document_text.parquet'],
  description = 'Per-page extracted text from CBA PDFs'
);

-- External Table: CBA Articles
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.cba.cba_articles_parquet`
WITH CONNECTION `heartbeat-474020.us-east1.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/reference/cba/cba_articles.parquet'],
  description = 'Detected CBA articles with content and page spans'
);

-- External Table: CBA Chunks
CREATE OR REPLACE EXTERNAL TABLE `heartbeat-474020.cba.cba_chunks_parquet`
WITH CONNECTION `heartbeat-474020.us-east1.lake-connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://heartbeat-474020-lake/silver/reference/cba/cba_chunks.parquet'],
  description = 'Chunked CBA text windows for semantic search/RAG'
);

-- =============================================================================
-- STEP 2: Create Ontology Object Views
-- =============================================================================

-- Object View: CBADocument
-- Canonical view of CBA documents with lineage
CREATE OR REPLACE VIEW `heartbeat-474020.cba.objects_cba_document` AS
SELECT
  -- Identity
  CAST(document_id AS STRING) AS document_id,
  
  -- Core fields
  CAST(document_name AS STRING) AS document_name,
  CAST(document_type AS STRING) AS document_type,
  DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_date AS INT64) / 1000 AS INT64))) AS effective_date,
  DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(expiration_date AS INT64) / 1000 AS INT64))) AS expiration_date,
  CAST(predecessor_id AS STRING) AS predecessor_id,
  CAST(pdf_uri AS STRING) AS pdf_uri,
  CAST(summary AS STRING) AS summary,
  CAST(total_pages AS INT64) AS total_pages,
  
  -- Metadata
  CAST(last_updated AS TIMESTAMP) AS last_updated,
  CAST(uploaded_by AS STRING) AS uploaded_by,
  
  -- Derived fields
  DATE_DIFF(
    DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(expiration_date AS INT64) / 1000 AS INT64))),
    DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_date AS INT64) / 1000 AS INT64))),
    DAY
  ) AS validity_days,
  CASE 
    WHEN expiration_date IS NULL OR DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(expiration_date AS INT64) / 1000 AS INT64))) > CURRENT_DATE() THEN TRUE
    ELSE FALSE
  END AS is_active

FROM `heartbeat-474020.cba.cba_documents_parquet`;

-- Object View: CBARule (All versions with history)
-- Temporal view of all CBA rules including superseded versions
CREATE OR REPLACE VIEW `heartbeat-474020.cba.objects_cba_rule` AS
SELECT
  -- Identity
  CAST(rule_id AS STRING) AS rule_id,
  
  -- Core fields
  CAST(rule_category AS STRING) AS rule_category,
  CAST(rule_type AS STRING) AS rule_type,
  CAST(rule_name AS STRING) AS rule_name,
  CAST(value_numeric AS FLOAT64) AS value_numeric,
  CAST(value_text AS STRING) AS value_text,
  DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_from AS INT64) / 1000 AS INT64))) AS effective_from,
  DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_to AS INT64) / 1000 AS INT64))) AS effective_to,
  CAST(source_document AS STRING) AS source_document,
  CAST(source_article AS STRING) AS source_article,
  CAST(supersedes_rule_id AS STRING) AS supersedes_rule_id,
  CAST(is_current_version AS BOOL) AS is_current_version,
  CAST(change_summary AS STRING) AS change_summary,
  CAST(notes AS STRING) AS notes,
  
  -- Metadata
  CAST(last_updated AS TIMESTAMP) AS last_updated,
  CAST(verified_by AS STRING) AS verified_by,
  
  -- Derived fields
  CASE 
    WHEN effective_to IS NULL THEN DATE_DIFF(CURRENT_DATE(), DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_from AS INT64) / 1000 AS INT64))), DAY)
    ELSE DATE_DIFF(DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_to AS INT64) / 1000 AS INT64))), DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_from AS INT64) / 1000 AS INT64))), DAY)
  END AS validity_days,
  
  CASE
    WHEN effective_to IS NULL OR DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_to AS INT64) / 1000 AS INT64))) > CURRENT_DATE() THEN TRUE
    ELSE FALSE
  END AS is_currently_active,
  
  -- Point-in-time helpers
  CASE 
    WHEN DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_from AS INT64) / 1000 AS INT64))) <= CURRENT_DATE() 
      AND (effective_to IS NULL OR DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_to AS INT64) / 1000 AS INT64))) > CURRENT_DATE())
    THEN TRUE
    ELSE FALSE
  END AS active_today

FROM `heartbeat-474020.cba.cba_rules_all_parquet`;

-- Object View: CBARule Current (active rules only)
-- Simplified view for most common queries (no history)
CREATE OR REPLACE VIEW `heartbeat-474020.cba.objects_cba_rule_current` AS
SELECT
  rule_id,
  rule_category,
  rule_type,
  rule_name,
  value_numeric,
  value_text,
  effective_from,
  effective_to,
  source_document,
  source_article,
  supersedes_rule_id,
  is_current_version,
  change_summary,
  notes,
  last_updated,
  verified_by,
  validity_days,
  is_currently_active,
  active_today
FROM `heartbeat-474020.cba.objects_cba_rule`
WHERE is_current_version = TRUE;

-- =============================================================================
-- STEP 3: Analytics Helper Views
-- =============================================================================

-- Helper: Salary Cap History
CREATE OR REPLACE VIEW `heartbeat-474020.cba.analytics_salary_cap_history` AS
SELECT
  rule_id,
  rule_name,
  value_numeric AS cap_value,
  effective_from,
  effective_to,
  source_document,
  change_summary,
  CASE
    WHEN rule_type = 'Upper Limit' THEN 'Ceiling'
    WHEN rule_type = 'Lower Limit' THEN 'Floor'
  END AS cap_type
FROM `heartbeat-474020.cba.objects_cba_rule`
WHERE rule_category = 'Salary Cap'
ORDER BY effective_from DESC;

-- Helper: Current Cap Rules (for quick queries)
CREATE OR REPLACE VIEW `heartbeat-474020.cba.analytics_current_cap_rules` AS
SELECT
  MAX(CASE WHEN rule_type = 'Upper Limit' THEN value_numeric END) AS cap_ceiling,
  MAX(CASE WHEN rule_type = 'Lower Limit' THEN value_numeric END) AS cap_floor,
  MAX(CASE WHEN rule_type = 'Upper Limit' THEN effective_from END) AS ceiling_effective_from,
  MAX(CASE WHEN rule_category = 'Performance Bonuses' AND rule_type = 'Team Cushion' 
    THEN value_numeric END) AS performance_bonus_cushion
FROM `heartbeat-474020.cba.objects_cba_rule_current`
WHERE rule_category IN ('Salary Cap', 'Performance Bonuses')
  AND is_currently_active = TRUE;

-- Helper: Waiver Eligibility Rules
CREATE OR REPLACE VIEW `heartbeat-474020.cba.analytics_waiver_rules` AS
SELECT
  rule_id,
  rule_name,
  value_numeric,
  notes,
  source_article
FROM `heartbeat-474020.cba.objects_cba_rule_current`
WHERE rule_category = 'Waivers'
ORDER BY rule_name;

-- =============================================================================
-- STEP 4: Document/Article Object Views
-- =============================================================================

-- Generic Document view (portable shape)
CREATE OR REPLACE VIEW `heartbeat-474020.cba.objects_document` AS
SELECT
  CAST(document_id AS STRING) AS document_id,
  CAST(document_name AS STRING) AS title,
  CAST(document_type AS STRING) AS document_type,
  DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(effective_date AS INT64) / 1000 AS INT64))) AS effective_date,
  DATE(TIMESTAMP_MICROS(SAFE_CAST(CAST(expiration_date AS INT64) / 1000 AS INT64))) AS expiration_date,
  CAST(predecessor_id AS STRING) AS predecessor_id,
  CAST(pdf_uri AS STRING) AS source_uri,
  CAST(summary AS STRING) AS summary,
  CAST(total_pages AS INT64) AS total_pages,
  CAST(last_updated AS TIMESTAMP) AS last_updated,
  CAST(uploaded_by AS STRING) AS uploaded_by
FROM `heartbeat-474020.cba.cba_documents_parquet`;

-- Per-page document text
CREATE OR REPLACE VIEW `heartbeat-474020.cba.objects_document_page` AS
SELECT
  CAST(document_id AS STRING) AS document_id,
  CAST(page_number AS INT64) AS page_number,
  CAST(text AS STRING) AS page_text,
  CAST(char_count AS INT64) AS char_count,
  CAST(token_estimate AS INT64) AS token_estimate,
  CAST(article_hint AS STRING) AS article_hint,
  CAST(article_number AS STRING) AS article_number
FROM `heartbeat-474020.cba.cba_document_text_parquet`;

-- CBA Article object
CREATE OR REPLACE VIEW `heartbeat-474020.cba.objects_cba_article` AS
SELECT
  CAST(document_id AS STRING) AS document_id,
  CAST(article_number AS STRING) AS article_number,
  CAST(article_title AS STRING) AS article_title,
  CAST(start_page AS INT64) AS start_page,
  CAST(end_page AS INT64) AS end_page,
  CAST(content AS STRING) AS content,
  CAST(char_count AS INT64) AS char_count
FROM `heartbeat-474020.cba.cba_articles_parquet`;

-- Document chunk object
CREATE OR REPLACE VIEW `heartbeat-474020.cba.objects_document_chunk` AS
SELECT
  CAST(chunk_id AS STRING) AS chunk_id,
  CAST(document_id AS STRING) AS document_id,
  CAST(section AS STRING) AS section,
  CAST(page_start AS INT64) AS page_start,
  CAST(page_end AS INT64) AS page_end,
  CAST(text AS STRING) AS text,
  CAST(token_estimate AS INT64) AS token_estimate
FROM `heartbeat-474020.cba.cba_chunks_parquet`;

-- =============================================================================
-- STEP 5: Verify Tables Created
-- =============================================================================

SELECT 'CBA Tables Created Successfully' AS status,
  (SELECT COUNT(*) FROM `heartbeat-474020.cba.cba_documents_parquet`) AS documents_count,
  (SELECT COUNT(*) FROM `heartbeat-474020.cba.cba_rules_all_parquet`) AS rules_total,
  (SELECT COUNT(*) FROM `heartbeat-474020.cba.cba_rules_current_parquet`) AS rules_current;
