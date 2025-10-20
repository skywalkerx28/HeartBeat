"""
Create Ontology per-season PBP views and a union view.

Views created:
  - ontology.player_game_events_<YYYY_YYYY>
  - ontology.player_game_events (UNION ALL across seasons)
"""

from google.cloud import bigquery
import logging
import os

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
    rows = client.query(query).result()
    return [row[0] for row in rows]


def create_views(client: bigquery.Client, tables: list[str]):
    seasons = []
    for t in tables:
        try:
            season = t.replace('pbp_', '').replace('_parquet', '').replace('_', '-')
        except Exception:
            continue
        seasons.append((season, t))

    if not seasons:
        logger.warning('No PBP season tables found to create views')
        return

    # Determine common columns across seasons for safe UNION view
    common_cols = None
    col_map = {}
    for _, table in seasons:
        q = f"""
        SELECT column_name
        FROM `{PROJECT_ID}.raw.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{table}'
        ORDER BY ordinal_position
        """
        cols = [r[0] for r in client.query(q).result()]
        col_map[table] = cols
        common_cols = set(cols) if common_cols is None else (common_cols & set(cols))

    # Preserve a stable order for common columns
    ordered_common = [c for c in col_map[seasons[-1][1]] if c in common_cols]

    # Create per-season views (all columns)
    for season, table in seasons:
        view_id = f"{PROJECT_ID}.ontology.player_game_events_{season.replace('-', '_')}"
        sql = f"""
        CREATE OR REPLACE VIEW `{view_id}` AS
        SELECT * FROM `{PROJECT_ID}.raw.{table}`
        """
        client.query(sql).result()
        logger.info(f"✓ Created view: {view_id}")

    # Create union view with the common subset
    select_list = ", ".join(f"CAST(`{c}` AS STRING) AS `{c}`" for c in ordered_common)
    union_sql_parts = [f"SELECT {select_list} FROM `{PROJECT_ID}.raw.{table}`" for _, table in seasons]
    union_sql = "\nUNION ALL\n".join(union_sql_parts)
    union_view_id = f"{PROJECT_ID}.ontology.player_game_events"
    sql = f"CREATE OR REPLACE VIEW `{union_view_id}` AS\n{union_sql}"
    client.query(sql).result()
    logger.info(f"✓ Created union view: {union_view_id}")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    tables = list_pbp_season_tables(client)
    create_views(client, tables)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
