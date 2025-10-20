Scripts Directory Structure

This folder is organized into focused subdirectories to make it easier to navigate and maintain. All references in the repo have been updated to these canonical paths; there are no legacy symlinks.

Structure

- `cba/` – CBA ingestion, processing, and validation
  - `ingest_cba_documents.py`
  - `process_cba_rules.py`
  - `sync_cba_to_gcs.py`
  - `create_cba_views.sql`
  - `test_cba_retrieval.py`
  - `upload_cba_pdfs.sh`

- `gcp/` – GCP/BigQuery/BigLake jobs and utilities
  - `convert_csv_to_parquet.py`
  - `sync_parquet_to_gcs.py`
  - `create_biglake_tables.sh`
  - `create_biglake_tables.sql`
  - `create_biglake_pbp_tables.py`
  - `load_core_tables.py`
  - `test_phase1_deployment.py`
  - `gcp_phase1_setup.sh`
  - `vertex_index_setup.py`
  - `vertex_upsert_from_gcs.py`

- `tests/` – Standalone validation and smoke tests
  - `test_clip_system_production.py`
  - `test_comprehensive_clip_retrieval.py`
  - `test_contract_csv_endpoint.py`
  - `test_duckdb_simple.py`
  - `test_e2e_clip_retrieval.py`
  - `test_extraction.py`
  - `test_heartbeat_model.py`
  - `test_orchestrator.py`
  - `test_roster_sync.py`

- `market_data/` – Market analytics SQL and helpers (existing)

- `ingest/` – Fetchers, scrapers, sync jobs
  - e.g., `fetch_team_rosters.py`, `daily_active_roster_sync.py`, `batch_extraction_processor.py`, `scrape_player_contract.py`

- `transform/` – Aggregations, feature engineering, table/build scripts
  - e.g., `aggregate_team_metrics.py`, `create_core_pbp_models.py`, `build_unified_roster.py`

- `ops/` – Maintenance, migrations, operational utilities
  - e.g., `fix_db_schema.py`, `pbp_schema_migration.py`, `setup_roster_cron.sh`, `run_app.py`

- `ml/` – Training, datasets, model deployment
  - e.g., `build_training_datasets.py`, `train_forecasts.py`, `deploy_model_endpoint.py`

Guidelines

- New scraping/import jobs → place under `ingest/` (to be added as needed).
- Transform/aggregation/model-building → place under `transform/` (to be added).
- One-off operational utilities (migrations, cron helpers) → consider `ops/`.
- Keep test-only entry points in `tests/` to avoid crowding the top level.

Notes

- Use the canonical subfolder paths in docs, scripts, and automation (e.g., `scripts/gcp/sync_parquet_to_gcs.py`).
- Avoid adding top-level files under `scripts/`; keep them within the appropriate subfolder.
