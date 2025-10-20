"""
Create BigLake external tables for Play-by-Play Parquet by season.

Scans local Parquet layout at data/processed/fact/pbp/season=YYYY-YYYY/team=TEAM/*.parquet
and creates external tables in BigQuery `raw` dataset with explicit URIs per team
to satisfy single-wildcard constraints.
"""

from pathlib import Path
from google.cloud import bigquery
from google.api_core.exceptions import Conflict
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv('GCP_PROJECT', 'heartbeat-474020')
DATASET = 'raw'
BUCKET = os.getenv('GCS_LAKE_BUCKET', 'heartbeat-474020-lake')

LOCAL_PBP_ROOT = Path('data/processed/fact/pbp')


def create_external_table_for_season(client: bigquery.Client, season: str, teams: list[str]):
    table_id = f"{PROJECT_ID}.{DATASET}.pbp_{season.replace('-', '_')}_parquet"
    table = bigquery.Table(table_id)
    external_config = bigquery.ExternalConfig('PARQUET')
    uris = [
        f"gs://{BUCKET}/silver/fact/pbp/season={season}/team={team}/*.parquet"
        for team in sorted(teams)
    ]
    external_config.source_uris = uris
    table.external_data_configuration = external_config
    try:
        client.create_table(table)
        logger.info(f"✓ Created external table: {table_id} with {len(uris)} team URIs")
    except Conflict:
        client.update_table(table, ['external_data_configuration'])
        logger.info(f"✓ Replaced external table: {table_id} with {len(uris)} team URIs")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    if not LOCAL_PBP_ROOT.exists():
        logger.error(f"Local PBP Parquet root not found: {LOCAL_PBP_ROOT}")
        return 1

    seasons = []
    for season_dir in LOCAL_PBP_ROOT.glob('season=*'):
        if season_dir.is_dir():
            seasons.append(season_dir.name.split('=', 1)[1])

    if not seasons:
        logger.warning("No seasons found under data/processed/fact/pbp")
        return 0

    for season in sorted(seasons):
        teams = []
        for team_dir in (LOCAL_PBP_ROOT / f"season={season}").glob('team=*'):
            if team_dir.is_dir():
                teams.append(team_dir.name.split('=', 1)[1])
        if not teams:
            logger.info(f"No team partitions for season {season}; skipping")
            continue
        create_external_table_for_season(client, season, teams)

    logger.info("✓ BigLake PBP external tables created/updated")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

