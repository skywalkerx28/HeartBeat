# HeartBeat Engine - GCP Phase 1 Implementation Complete

## Overview

Phase 1 establishes the foundational GCP infrastructure for HeartBeat Engine, creating a Palantir-inspired Ontology framework with pluggable backends and hybrid data access (BigQuery + Parquet fallback).

**Completed:** October 19, 2025

## What Was Implemented

### 1. GCS Data Lake Structure

**Bucket:** `gs://heartbeat-474020-lake`

**Tier Organization:**
- `bronze/` - Raw CSV ingestion
- `silver/` - Clean Parquet files (source for BigLake)
  - `silver/dim/rosters/` - Unified roster snapshots
  - `silver/dim/depth_charts/` - Team depth charts
  - `silver/dim/player_profiles/` - Player profile indexes
  - `silver/fact/pbp/` - Play-by-play events (Hive partitioned)
  - `silver/fact/league_player_stats/` - League-wide player stats (10 seasons)
  - `silver/market/contracts/` - Player contracts
- `gold/` - Analytics-ready tables
  - `gold/analytics/` - Materialized analytics views
  - `gold/ontology/` - Ontology semantic layer (Phase 2)
- `rag/` - RAG embeddings and metadata

### 2. BigQuery Datasets

**Created:**
- `heartbeat-474020.raw` - External tables over silver Parquet (BigLake)
- `heartbeat-474020.core` - Native tables with partitioning/clustering
- `heartbeat-474020.analytics` - Materialized views (Phase 2)
- `heartbeat-474020.ontology` - Semantic layer (Phase 2)
- `heartbeat-474020.market` - Already exists (contract analytics)

### 3. BigLake External Tables

**Tables Created in `raw` dataset:**
- `rosters_parquet` - NHL unified roster snapshots
- `depth_charts_parquet` - Team depth charts with prospects
- `player_profiles_parquet` - Player advanced profile indexes
- `pbp_parquet` - Play-by-play events (Hive partitioned)
- `contracts_parquet` - Player contracts and cap info
- `league_player_stats_parquet` - 10 seasons of advanced player metrics

**Note:** Montreal-centric tables removed (system is now league-wide, team-agnostic)

### 4. Vector Store Backend Interface

**Created pluggable architecture for RAG backends:**

**Abstract Interface:** `orchestrator/tools/vector_store_backend.py`
- Defines common methods: `upsert_vectors()`, `search()`, `delete()`, `get_stats()`

**Pinecone Backend:** `orchestrator/tools/vector_backends/pinecone_backend.py`
- Production implementation using Pinecone gRPC API
- Current default backend

**Vertex Backend (Stub):** `orchestrator/tools/vector_backends/vertex_backend.py`
- Placeholder for Phase 3 implementation
- Raises NotImplementedError with helpful messages

**Factory:** `orchestrator/tools/pinecone_mcp_client.VectorStoreFactory`
- Creates backend based on `VECTOR_BACKEND` environment variable
- Supports: `pinecone` (default), `vertex` (Phase 3)

### 5. BigQuery Analytics Client

**Created:** `orchestrator/tools/analytics_data_client_bq.py`

**Mirrors ParquetDataClientV2 methods:**
- `get_player_stats()` - Player statistics with parameterized SQL
- `get_matchup_data()` - Team matchup analytics
- `get_season_results()` - Game-by-game results with filtering

**Features:**
- Parameterized queries to prevent SQL injection
- Consistent API with Parquet client for seamless fallback
- Error handling with detailed logging

### 6. Integrated Parquet Analyzer

**Updated:** `orchestrator/nodes/parquet_analyzer.py`

**New Behavior:**
- Lazy-loads BigQuery client only if `USE_BIGQUERY_ANALYTICS=true`
- Tries BigQuery first for player stats and matchup queries
- Falls back to Parquet on any BigQuery error
- Zero disruption to existing Parquet-first workflows

### 7. Configuration Updates

**Settings:** `orchestrator/config/settings.py`

Added:
- `BigQueryConfig` - Project ID, datasets, location
- `GCSConfig` - Bucket name, tier prefixes
- `vector_backend` - Backend selection

**Startup Script:** `start_heartbeat.sh`

New environment variables:
```bash
USE_BIGQUERY_ANALYTICS=false    # Enable BigQuery analytics
GCP_PROJECT=heartbeat-474020     # GCP project ID
BQ_DATASET_CORE=core             # Core dataset name
GCS_LAKE_BUCKET=heartbeat-474020-lake  # Data lake bucket
VECTOR_BACKEND=pinecone          # Vector backend (pinecone|vertex)
```

## Deployment Scripts

### Infrastructure Setup
```bash
bash scripts/gcp_phase1_setup.sh
```
- Enables GCP APIs
- Creates GCS bucket with tier structure
- Creates BigQuery datasets
- Configures IAM permissions

### Data Conversion
```bash
python3 scripts/gcp/convert_csv_to_parquet.py
```
- Converts depth charts (CSVs → Parquet)
- Creates unified roster snapshot
- Converts MTL play-by-play (CSVs → Parquet)
- Converts league player stats (10 seasons)

### GCS Sync
```bash
python3 scripts/gcp/sync_parquet_to_gcs.py
```
- Uploads Parquet files to GCS silver tier
- Preserves Hive-style partitioning
- Uploads: rosters, depth charts, player profiles, league stats, analytics

### BigLake Setup
```bash
bash scripts/gcp/create_biglake_tables.sh
```
- Creates BigLake connection
- Grants GCS permissions to BigLake service account
- Creates external tables over silver Parquet

### Load Core Tables
```bash
python3 scripts/gcp/load_core_tables.py
```
- Loads hot facts into native BigQuery tables
- Creates `core.snap_roster_scd2` with SCD2 columns

### Validation
```bash
python3 scripts/gcp/test_phase1_deployment.py
```
- Tests GCS access
- Verifies BigQuery datasets
- Checks BigLake tables
- Validates vector backend factory
- Tests BigQuery analytics client

## Usage

### Enable BigQuery Analytics

```bash
# In .env or export before starting
export USE_BIGQUERY_ANALYTICS=true
export GCP_PROJECT=heartbeat-474020
export BQ_DATASET_CORE=core

# Start HeartBeat
bash start_heartbeat.sh
```

### Query Player Stats (Auto-fallback)

Queries will automatically try BigQuery first, fall back to Parquet:

```python
from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode

analyzer = ParquetAnalyzerNode()

# Tries BigQuery if enabled, falls back to Parquet
stats = await analyzer.analyze("Nick Suzuki 2024-2025 stats")
```

### Switch Vector Backends

```bash
# Use Pinecone (default, production)
export VECTOR_BACKEND=pinecone

# Use Vertex AI (Phase 3, currently stub)
export VECTOR_BACKEND=vertex
```

## Backward Compatibility

### Zero Disruption Guarantee

- All existing Parquet-first workflows continue unchanged
- BigQuery is opt-in via `USE_BIGQUERY_ANALYTICS` flag
- Parquet remains the fallback for all queries
- No changes required to existing code

### Hybrid Access Pattern

1. **Query attempt:** Try BigQuery (if enabled)
2. **On error:** Fall back to Parquet
3. **Result:** Client code sees no difference

## Data Sources

### Current Data in GCS

After running `sync_parquet_to_gcs.py`:

- Roster snapshots (32 teams, latest)
- Depth charts (32 teams × roster/non-roster/unsigned)
- Player profiles (46,006 advanced profiles)
- League player stats (10 seasons: 2015-2025)
- Market data (contracts, performance indexes)
- Analytics (existing processed Parquet)

### Schema Notes

- **snapshot_date** column in rosters for SCD2 tracking
- **season** column with Hive partitioning for time-series data
- **team_abbrev** for cross-team queries
- **loaded_at** timestamp for data lineage

## Next Steps (Phase 2)

### Ontology Semantic Layer

Create views in `ontology` dataset:
- `objects_player` - Player entities with canonical IDs
- `objects_team` - Team entities
- `objects_game` - Game entities
- `links_player_contract` - Player-contract relationships
- `links_player_team` - Employment links

### Analytics Materialization

Load high-frequency queries into `analytics` dataset:
- Performance indexes by position
- Market comparables
- Trend analysis views

### Full BigQuery Coverage

Expand `AnalyticsDataClientBQ` to mirror all ParquetDataClientV2 methods:
- Power play stats
- Penalty kill stats
- Line combinations
- Advanced metrics

## Phase 3 Preview (Vertex AI Vector Search)

### Planned Implementation

1. Create Vertex AI indexes for each namespace
2. Deploy indexes to managed endpoints
3. Implement dual-write (Pinecone + Vertex)
4. Validate retrieval parity
5. Switch default to Vertex, keep Pinecone fallback

### Benefits of Vertex Migration

- GCP-native IAM and security
- Low-latency intra-GCP traffic
- Unified monitoring with BigQuery/GCS
- Integration with Vertex AI Agent Builder
- Direct grounding to BigQuery tables

## Troubleshooting

### BigQuery queries fail

```bash
# Disable BigQuery, use Parquet only
export USE_BIGQUERY_ANALYTICS=false
```

### GCS permissions error

```bash
# Re-grant permissions
gsutil iam ch user:$(gcloud config get-value account):objectAdmin \
  gs://heartbeat-474020-lake
```

### Vector backend error

```bash
# Fall back to Pinecone
export VECTOR_BACKEND=pinecone
```

### Data not found in BigLake

```bash
# Check if data is uploaded
gsutil ls gs://heartbeat-474020-lake/silver/dim/rosters/

# If empty, run sync
python3 scripts/gcp/sync_parquet_to_gcs.py
```

## Rollback Procedure

If Phase 1 causes issues:

```bash
# 1. Disable BigQuery
export USE_BIGQUERY_ANALYTICS=false

# 2. Keep Pinecone (no change)
export VECTOR_BACKEND=pinecone

# 3. Original Parquet files unchanged (GCS is additive)

# 4. Optional: Delete BigQuery datasets
bq rm -r -f heartbeat-474020:raw
bq rm -r -f heartbeat-474020:core
```

## Success Metrics

- [x] GCS bucket created with bronze/silver/gold structure
- [x] BigQuery datasets (raw, core, analytics, ontology) created
- [x] BigLake connection configured
- [x] External tables created (6 tables)
- [x] Vector backend interface implemented (Pinecone + Vertex stub)
- [x] BigQuery analytics client created
- [x] Parquet Analyzer integrated with hybrid fallback
- [x] Configuration settings updated
- [x] Test suite created
- [x] Zero disruption to existing workflows
- [x] League-wide, team-agnostic data architecture

## Files Created

**Infrastructure:**
- `scripts/gcp_phase1_setup.sh` - GCP setup automation
- `scripts/gcp/convert_csv_to_parquet.py` - CSV to Parquet conversion
- `scripts/gcp/sync_parquet_to_gcs.py` - Upload to GCS
- `scripts/gcp/create_biglake_tables.sh` - BigLake setup
- `scripts/gcp/create_biglake_tables.sql` - External table DDL
- `scripts/gcp/load_core_tables.py` - Load native BigQuery tables
- `scripts/gcp/test_phase1_deployment.py` - Validation tests

**Vector Backends:**
- `orchestrator/tools/vector_store_backend.py` - Abstract interface
- `orchestrator/tools/vector_backends/__init__.py` - Module exports
- `orchestrator/tools/vector_backends/pinecone_backend.py` - Pinecone implementation
- `orchestrator/tools/vector_backends/vertex_backend.py` - Vertex stub

**Analytics:**
- `orchestrator/tools/analytics_data_client_bq.py` - BigQuery client

**Modified:**
- `orchestrator/config/settings.py` - Added GCP configs
- `orchestrator/nodes/parquet_analyzer.py` - Integrated BigQuery
- `orchestrator/tools/pinecone_mcp_client.py` - Added VectorStoreFactory
- `start_heartbeat.sh` - Added GCP environment variables

## Architecture Alignment

### Palantir Ontology Framework

**Semantic Layer (Phase 1 Foundation):**
- BigLake external tables provide semantic mappings
- Data catalog remains physical resolver
- Schema-on-read for flexible querying

**Kinetic Layer (Phase 2):**
- Tool nodes as action types
- Object SDK for bound functions
- Ontology views map semantic → kinetic

**Dynamic Layer (Current):**
- LLM binds to tools via orchestrator
- RAG provides context with pluggable backends
- Dynamic query routing (BigQuery vs Parquet)

## Contact & Support

For questions or issues:
1. Check test results: `python3 scripts/gcp/test_phase1_deployment.py`
2. Review logs in `backend.log`
3. Verify GCP authentication: `gcloud auth application-default print-access-token`

## Conclusion

GCP Phase 1 successfully establishes:
- Scalable data lake on GCS
- Flexible query layer (BigQuery + Parquet)
- Pluggable vector backends (Pinecone + Vertex ready)
- Zero-disruption migration path
- League-wide, team-agnostic architecture

**Ready for Phase 2:** Ontology materialization and full BigQuery analytics coverage.

