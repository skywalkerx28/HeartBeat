#!/usr/bin/env python3
"""
Migrate HeartBeat.bot local DuckDB content to Postgres (Cloud SQL/AlloyDB).

Usage:
  export DATABASE_URL=postgresql+psycopg2://user:pass@host:port/db
  python scripts/migrate_news_db_to_postgres.py

It reads DuckDB path from backend/bot/config.BOT_CONFIG['db_path'] and
inserts rows into Postgres tables (creating schema if necessary).

Tables migrated:
  - transactions
  - team_news
  - injury_reports
  - news_entities
  - game_summaries
  - player_updates
  - daily_articles
"""

import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("migrate")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.bot import db as botdb  # type: ignore
import duckdb
from sqlalchemy import create_engine, text


def fetch_all_duck(conn: duckdb.DuckDBPyConnection, sql: str):
    try:
        return conn.execute(sql).fetchall()
    except Exception as e:
        logger.warning(f"DuckDB fetch failed for query: {sql[:80]}... -> {e}")
        return []


def migrate_table(duck: duckdb.DuckDBPyConnection, pg_engine, table: str):
    logger.info(f"Migrating table: {table}")
    rows = fetch_all_duck(duck, f"SELECT * FROM {table}")
    if not rows:
        logger.info(f"  No rows in {table}")
        return 0

    # Build insert with positional placeholders -> named for SQLAlchemy
    with pg_engine.begin() as conn:
        # Get column names from DuckDB pragma
        cols = [r[1] for r in duck.execute(f"PRAGMA table_info({table})").fetchall()]
        placeholders = ", ".join([f":p{i}" for i in range(len(cols))])
        col_list = ", ".join([f"{c}" for c in cols])
        insert_sql = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")
        count = 0
        for r in rows:
            bind = {f"p{i}": r[i] for i in range(len(cols))}
            try:
                conn.execute(insert_sql, bind)
                count += 1
            except Exception as e:
                logger.debug(f"  Skip row error: {e}")
    logger.info(f"  Inserted {count} rows into {table}")
    return count


def main():
    db_backend = os.getenv("HEARTBEAT_DB_BACKEND", "duckdb")
    if db_backend != "postgres":
        logger.info("Set HEARTBEAT_DB_BACKEND=postgres and DATABASE_URL to test migration destination.")

    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if not database_url:
        logger.error("DATABASE_URL not set")
        return 1

    duck_path = botdb.DB_PATH
    if not duck_path.exists():
        logger.error(f"DuckDB file not found: {duck_path}")
        return 1

    logger.info(f"Source (DuckDB): {duck_path}")
    logger.info(f"Destination (Postgres): {database_url}")

    pg_engine = create_engine(database_url, pool_pre_ping=True)
    # Ensure schema exists
    try:
        botdb._init_postgres_schema(pg_engine)  # type: ignore[attr-defined]
    except Exception as e:
        logger.error(f"Failed to initialize Postgres schema: {e}")
        return 1

    duck = duckdb.connect(str(duck_path), read_only=True)
    totals = 0
    try:
        for t in (
            "transactions",
            "team_news",
            "injury_reports",
            "news_entities",
            "game_summaries",
            "player_updates",
            "daily_articles",
        ):
            try:
                totals += migrate_table(duck, pg_engine, t)
            except Exception as e:
                logger.warning(f"Table {t} migration warning: {e}")
    finally:
        duck.close()
    logger.info(f"Migration complete. Inserted {totals} rows across tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

