"""
Create core native BigQuery tables from external PBP Parquet.

For each raw.pbp_<YYYY_YYYY>_parquet table:
  - CREATE OR REPLACE TABLE core.fact_pbp_events_<YYYY_YYYY>
    PARTITION BY DATE(game_date) IF column exists, else unpartitioned
    AS SELECT * FROM raw.pbp_<YYYY_YYYY>_parquet

Optionally creates a union view `core.fact_pbp_events_all` with common string-cast columns.
"""

from google.cloud import bigquery
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv('GCP_PROJECT', 'heartbeat-474020')


def list_pbp_season_tables(client: bigquery.Client):
    query = f"""
    SELECT table_name
    FROM `{PROJECT_ID}.raw.INFORMATION_SCHEMA.TABLES`
    WHERE table_name LIKE 'pbp%parquet'
    ORDER BY table_name
    """
    return [r[0] for r in client.query(query).result()]


def table_columns(client: bigquery.Client, table: str):
    q = f"""
    SELECT column_name
    FROM `{PROJECT_ID}.raw.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = '{table}'
    ORDER BY ordinal_position
    """
    return [r[0] for r in client.query(q).result()]


def create_core_tables(client: bigquery.Client, tables: list[str]):
    # Pre-filter readable tables
    readable = []
    for t in tables:
        try:
            client.query(f"SELECT 1 FROM `{PROJECT_ID}.raw.{t}` LIMIT 1").result()
            # Include only seasons with richer schema (has game_date)
            cols = table_columns(client, t)
            if 'game_date' in cols:
                readable.append(t)
            else:
                logger.info(f"Skipping {t} (no game_date column)")
        except Exception as e:
            logger.warning(f"Skipping {t} due to read error: {e}")
            continue

    # Build native tables per season for readable only
    for t in readable:
        season = t.replace('pbp_', '').replace('_parquet', '')
        core_table = f"{PROJECT_ID}.core.fact_pbp_events_{season}"
        cols = table_columns(client, t)
        select_list = ", ".join(f"CAST(`{c}` AS STRING) AS `{c}`" for c in cols)
        sql = f"""
        CREATE OR REPLACE TABLE `{core_table}` AS
        SELECT {select_list} FROM `{PROJECT_ID}.raw.{t}`
        """
        try:
            client.query(sql).result()
            logger.info(f"✓ Created core table: {core_table}")
        except Exception as e:
            logger.warning(f"Skipping core table for {t} due to creation error: {e}")
            continue

    # Create union view across seasons with common columns cast to STRING
    if not readable:
        return
    # Determine which core tables exist
    created = []
    for t in readable:
        season = t.replace('pbp_', '').replace('_parquet', '')
        try:
            client.query(f"SELECT 1 FROM `{PROJECT_ID}.core.fact_pbp_events_{season}` LIMIT 1").result()
            created.append(t)
        except Exception:
            continue
    if not created:
        logger.info("No core PBP tables created; skipping union view")
        return
    # Common columns intersection across created
    common = None
    for t in created:
        c = set(table_columns(client, t))
        common = c if common is None else (common & c)
    ordered_common = [c for c in table_columns(client, created[-1]) if c in common]
    select_list = ", ".join(f"CAST(`{c}` AS STRING) AS `{c}`" for c in ordered_common)
    parts = []
    for t in created:
        season = t.replace('pbp_', '').replace('_parquet', '')
        parts.append(f"SELECT {select_list} FROM `{PROJECT_ID}.core.fact_pbp_events_{season}`")
    union_sql = "\nUNION ALL\n".join(parts)
    union_view = f"{PROJECT_ID}.core.fact_pbp_events_all"
    client.query(f"CREATE OR REPLACE VIEW `{union_view}` AS\n{union_sql}").result()
    logger.info(f"✓ Created union view: {union_view}")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    tables = list_pbp_season_tables(client)
    create_core_tables(client, tables)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
