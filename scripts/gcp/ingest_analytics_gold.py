"""
HeartBeat Engine - Ingest Analytics Gold Artifacts to GCS + BigQuery

1) Convert player profiles aggregated JSON → Parquet
   - Source: data/processed/player_profiles/aggregated_stats/**/**/*.json
   - Target (local): data/processed/gold/analytics/player_profiles/player_profiles_agg.parquet
   - Upload: gs://<bucket>/gold/analytics/player_profiles/player_profiles_agg.parquet
   - BigLake external: raw.player_profiles_agg_parquet
   - Ontology view:   ontology.player_profiles_agg

2) Convert team advanced metrics JSON → Parquet
   - Source: data/processed/team_profiles/advanced_metrics/*/*.json
   - Target (local): data/processed/gold/analytics/team_advanced/team_advanced_metrics.parquet
   - Upload: gs://<bucket>/gold/analytics/team_advanced/team_advanced_metrics.parquet
   - BigLake external: raw.team_advanced_metrics_parquet
   - Ontology view:   ontology.team_advanced_metrics

Usage:
  python3 scripts/gcp/ingest_analytics_gold.py
"""

from pathlib import Path
from typing import List, Tuple
import os
import json
import logging
import re

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage, bigquery
from google.api_core.exceptions import Conflict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv('GCP_PROJECT', 'heartbeat-474020')
BUCKET = os.getenv('GCS_LAKE_BUCKET', 'heartbeat-474020-lake')

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / 'data' / 'processed'


def _ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def convert_player_profiles_agg() -> Path:
    """Convert player aggregated profile JSONs to a single Parquet file."""
    src_root = DATA_ROOT / 'player_profiles' / 'aggregated_stats'
    out_file = DATA_ROOT / 'gold' / 'analytics' / 'player_profiles' / 'player_profiles_agg.parquet'
    rows: List[pd.DataFrame] = []

    if not src_root.exists():
        logger.warning(f"Player profiles aggregated source not found: {src_root}")
        return out_file

    for json_path in src_root.rglob('*.json'):
        try:
            # player_id is directory name just above the file
            try:
                player_id = json_path.parent.name
            except Exception:
                player_id = None
            # season like 19901991_... extract 8 digits → 1990-1991
            season_match = re.search(r'(\d{4})(\d{4})', json_path.stem)
            season = f"{season_match.group(1)}-{season_match.group(2)}" if season_match else None
            scope = re.sub(r'^\d{8}_?', '', json_path.stem)  # suffix after season digits
            with open(json_path, 'r') as f:
                data = json.load(f)
            # Flatten object/array
            if isinstance(data, list):
                df = pd.json_normalize(data)
            else:
                df = pd.json_normalize(data)
            df['player_id'] = player_id
            df['season'] = season
            df['scope'] = scope
            df['source_path'] = str(json_path)
            rows.append(df)
        except Exception as e:
            logger.warning(f"Failed to process {json_path}: {e}")

    if not rows:
        logger.info("No player aggregated profiles found to convert")
        return out_file

    full = pd.concat(rows, ignore_index=True)
    # Sanitize column names for BigQuery compatibility
    full = _sanitize_columns(full)
    # Coerce obvious numeric fields if feasible; keep flexible otherwise
    for col in ['player_id']:
        if col in full.columns:
            full[col] = pd.to_numeric(full[col], errors='ignore')
    # Coerce nested values to JSON strings to avoid nested Parquet field names conflicts
    full = full.applymap(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
    _ensure_parent(out_file)
    full.to_parquet(out_file, engine='pyarrow', compression='ZSTD', index=False)
    logger.info(f"✓ Player profiles Parquet written: {out_file}")
    return out_file


def convert_team_advanced_metrics() -> Path:
    """Convert team advanced metrics JSON to a single Parquet file."""
    src_root = DATA_ROOT / 'team_profiles' / 'advanced_metrics'
    out_file = DATA_ROOT / 'gold' / 'analytics' / 'team_advanced' / 'team_advanced_metrics.parquet'
    rows: List[pd.DataFrame] = []

    if not src_root.exists():
        logger.warning(f"Team advanced metrics source not found: {src_root}")
        return out_file

    for team_dir in src_root.iterdir():
        if not team_dir.is_dir():
            continue
        team = team_dir.name
        for json_path in team_dir.glob('*.json'):
            try:
                season_match = re.search(r'(\d{4})(\d{4})', json_path.stem)
                season = f"{season_match.group(1)}-{season_match.group(2)}" if season_match else None
                with open(json_path, 'r') as f:
                    data = json.load(f)
                df = pd.json_normalize(data)
                df['team'] = team
                df['season'] = season
                df['source_path'] = str(json_path)
                rows.append(df)
            except Exception as e:
                logger.warning(f"Failed to process {json_path}: {e}")

    if not rows:
        logger.info("No team advanced metrics found to convert")
        return out_file

    full = pd.concat(rows, ignore_index=True)
    full = _sanitize_columns(full)
    # Coerce nested values to JSON strings
    full = full.applymap(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
    _ensure_parent(out_file)
    full.to_parquet(out_file, engine='pyarrow', compression='ZSTD', index=False)
    logger.info(f"✓ Team advanced Parquet written: {out_file}")
    return out_file


def upload_to_gcs(local: Path, gcs_prefix: str) -> str:
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET)
    dest = f"{gcs_prefix}/{local.name}"
    blob = bucket.blob(dest)
    logger.info(f"Uploading {local} -> gs://{BUCKET}/{dest}")
    blob.upload_from_filename(str(local))
    return f"gs://{BUCKET}/{dest}"


def create_external_table(client: bigquery.Client, table_id: str, uris: List[str], description: str = None):
    table = bigquery.Table(table_id)
    external_config = bigquery.ExternalConfig('PARQUET')
    external_config.source_uris = uris
    table.external_data_configuration = external_config
    if description:
        table.description = description
    try:
        client.create_table(table)
        logger.info(f"✓ Created external table: {table_id}")
    except Conflict:
        client.update_table(table, ['external_data_configuration'])
        logger.info(f"✓ Replaced external table: {table_id}")


def create_ontology_view(client: bigquery.Client, view_id: str, source_table: str):
    sql = f"""
    CREATE OR REPLACE VIEW `{view_id}` AS
    SELECT * FROM `{source_table}`
    """
    client.query(sql).result()
    logger.info(f"✓ Created view: {view_id}")


def main():
    # 1) Convert to Parquet (local)
    players_parquet = convert_player_profiles_agg()
    team_parquet = convert_team_advanced_metrics()

    # 2) Upload to GCS gold/analytics
    player_uri = upload_to_gcs(players_parquet, 'gold/analytics/player_profiles') if players_parquet.exists() else None
    team_uri = upload_to_gcs(team_parquet, 'gold/analytics/team_advanced') if team_parquet.exists() else None

    # 3) Create BigLake external tables
    client = bigquery.Client(project=PROJECT_ID)
    if player_uri:
        create_external_table(
            client,
            f"{PROJECT_ID}.raw.player_profiles_agg_parquet",
            [player_uri],
            "Flattened player profiles aggregated metrics (gold)"
        )
        create_ontology_view(
            client,
            f"{PROJECT_ID}.ontology.player_profiles_agg",
            f"{PROJECT_ID}.raw.player_profiles_agg_parquet"
        )
    if team_uri:
        create_external_table(
            client,
            f"{PROJECT_ID}.raw.team_advanced_metrics_parquet",
            [team_uri],
            "Team advanced metrics (gold)"
        )
        create_ontology_view(
            client,
            f"{PROJECT_ID}.ontology.team_advanced_metrics",
            f"{PROJECT_ID}.raw.team_advanced_metrics_parquet"
        )

    # 4) Quick test: BigQuery analytics client for game events
    try:
        from orchestrator.tools.analytics_data_client_bq import AnalyticsDataClientBQ
        analytics = AnalyticsDataClientBQ(project_id=PROJECT_ID, dataset_core='core', dataset_raw='raw')
        import asyncio
        res = asyncio.run(analytics.get_recent_game_events(team='MTL', season='2025-2026', limit=10))
        logger.info(f"Test get_recent_game_events: rows={res.get('rows')} season={res.get('season')} team={res.get('team')}")
    except Exception as e:
        logger.warning(f"BigQuery analytics test skipped/failed: {e}")

    return 0


 # ---------------- helpers -----------------
def _sanitize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with BigQuery‑safe column names.
    - Replace non [A-Za-z0-9_] with '_'
    - Prefix leading digits with '_'
    - Collapse repeated underscores and strip
    """
    def fix(name: str) -> str:
        safe = re.sub(r"\W", "_", str(name))
        if re.match(r"^[0-9]", safe):
            safe = "_" + safe
        safe = re.sub(r"_+", "_", safe).strip("_")
        # Ensure non-empty
        return safe or "_col"
    return df.rename(columns={c: fix(c) for c in df.columns})


if __name__ == '__main__':
    raise SystemExit(main())
