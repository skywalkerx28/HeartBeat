"""
HeartBeat.bot Database Layer (Postgres-only)

Production database interface for HeartBeat.bot using Postgres via SQLAlchemy.
All functions expose a simple ``execute/fetch/commit`` contract so call sites do
not need to know about SQLAlchemy.
"""

from __future__ import annotations
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
import time
import os

# Optional SQLAlchemy for Postgres backend
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine, Connection
    _SA_AVAILABLE = True
except Exception:
    _SA_AVAILABLE = False

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")

_pg_engine: Optional["Engine"] = None

def _get_pg_engine() -> "Engine":
    global _pg_engine
    if _pg_engine is not None:
        return _pg_engine
    if not _SA_AVAILABLE:
        raise RuntimeError("SQLAlchemy not available; cannot use postgres backend")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set; cannot use postgres backend")
    _pg_engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return _pg_engine

def _init_postgres_schema(engine: "Engine") -> None:
    """Create schema in Postgres (safe if exists)."""
    ddl = [
        # transactions
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            transaction_date DATE NOT NULL,
            player_name VARCHAR NOT NULL,
            player_id VARCHAR,
            team_from VARCHAR,
            team_to VARCHAR,
            transaction_type VARCHAR NOT NULL,
            description TEXT NOT NULL,
            source_url VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type)",
        # team_news
        """
        CREATE TABLE IF NOT EXISTS team_news (
            id INTEGER PRIMARY KEY,
            team_code VARCHAR NOT NULL,
            news_date DATE NOT NULL,
            title VARCHAR NOT NULL,
            summary TEXT,
            content TEXT,
            source_url VARCHAR,
            image_url VARCHAR,
            url_hash VARCHAR UNIQUE,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_team_news_team ON team_news(team_code)",
        "CREATE INDEX IF NOT EXISTS idx_team_news_date ON team_news(news_date)",
        # injury_reports
        """
        CREATE TABLE IF NOT EXISTS injury_reports (
            id INTEGER PRIMARY KEY,
            player_name VARCHAR NOT NULL,
            player_id VARCHAR,
            team_code VARCHAR NOT NULL,
            position VARCHAR,
            injury_type VARCHAR,
            injury_status VARCHAR NOT NULL,
            injury_description TEXT,
            return_estimate VARCHAR,
            placed_on_ir_date DATE,
            source_url VARCHAR,
            url_hash VARCHAR UNIQUE,
            verified BOOLEAN DEFAULT FALSE,
            sources JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_injury_team ON injury_reports(team_code)",
        "CREATE INDEX IF NOT EXISTS idx_injury_status ON injury_reports(injury_status)",
        # news_entities
        """
        CREATE TABLE IF NOT EXISTS news_entities (
            id INTEGER PRIMARY KEY,
            news_id INTEGER NOT NULL,
            entity_type VARCHAR NOT NULL,
            team_code VARCHAR,
            player_id VARCHAR,
            player_name VARCHAR,
            confidence DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_news_entities_news ON news_entities(news_id)",
        "CREATE INDEX IF NOT EXISTS idx_news_entities_player ON news_entities(entity_type, player_id)",
        "CREATE INDEX IF NOT EXISTS idx_news_entities_team ON news_entities(entity_type, team_code)",
        # players_registry
        """
        CREATE TABLE IF NOT EXISTS players_registry (
            player_id VARCHAR,
            player_name VARCHAR NOT NULL,
            team_code VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_players_registry_name ON players_registry((lower(player_name)))",
        # game_summaries (full fields used by code)
        """
        CREATE TABLE IF NOT EXISTS game_summaries (
            game_id VARCHAR PRIMARY KEY,
            game_date DATE NOT NULL,
            home_team VARCHAR NOT NULL,
            away_team VARCHAR NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            highlights TEXT,
            top_performers JSONB,
            period_summary JSONB,
            game_recap TEXT,
            image_url VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_game_summaries_date ON game_summaries(game_date)",
        "CREATE INDEX IF NOT EXISTS idx_game_summaries_teams ON game_summaries(home_team, away_team)",
        # player_updates
        """
        CREATE TABLE IF NOT EXISTS player_updates (
            id INTEGER PRIMARY KEY,
            player_id VARCHAR NOT NULL,
            player_name VARCHAR NOT NULL,
            team_code VARCHAR,
            update_date DATE NOT NULL,
            summary TEXT NOT NULL,
            recent_stats JSONB,
            notable_achievements JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_player_updates_player ON player_updates(player_id)",
        "CREATE INDEX IF NOT EXISTS idx_player_updates_date ON player_updates(update_date)",
        # daily_articles
        """
        CREATE TABLE IF NOT EXISTS daily_articles (
            article_date DATE PRIMARY KEY,
            title VARCHAR NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            metadata JSONB,
            source_count INTEGER,
            image_url VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # player_contracts
        """
        CREATE TABLE IF NOT EXISTS player_contracts (
            id INTEGER PRIMARY KEY,
            player_name VARCHAR NOT NULL,
            player_id VARCHAR,
            team_code VARCHAR NOT NULL,
            contract_type VARCHAR,
            signing_date DATE,
            signed_by VARCHAR,
            length_years INTEGER,
            total_value BIGINT,
            expiry_status VARCHAR,
            cap_hit BIGINT,
            cap_percent DOUBLE PRECISION,
            source_url VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_player_contracts_player ON player_contracts(player_name)",
        "CREATE INDEX IF NOT EXISTS idx_player_contracts_team ON player_contracts(team_code)",
        # contract_details
        """
        CREATE TABLE IF NOT EXISTS contract_details (
            id INTEGER PRIMARY KEY,
            contract_id INTEGER NOT NULL,
            season VARCHAR NOT NULL,
            clause VARCHAR,
            cap_hit BIGINT,
            cap_percent DOUBLE PRECISION,
            aav BIGINT,
            performance_bonuses BIGINT,
            signing_bonuses BIGINT,
            base_salary BIGINT,
            total_salary BIGINT,
            minors_salary BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_contract_details_contract ON contract_details(contract_id)",
        "CREATE INDEX IF NOT EXISTS idx_contract_details_season ON contract_details(season)",
        # team_rosters
        """
        CREATE TABLE IF NOT EXISTS team_rosters (
            id INTEGER PRIMARY KEY,
            team_code VARCHAR NOT NULL,
            player_name VARCHAR NOT NULL,
            player_id VARCHAR,
            position VARCHAR,
            roster_status VARCHAR NOT NULL,
            jersey_number INTEGER,
            cap_hit BIGINT,
            cap_percent DOUBLE PRECISION,
            age INTEGER,
            contract_expiry VARCHAR,
            handed VARCHAR,
            birthplace VARCHAR,
            draft_info VARCHAR,
            drafted_by VARCHAR,
            draft_year VARCHAR,
            draft_round VARCHAR,
            draft_overall VARCHAR,
            must_sign_date VARCHAR,
            dead_cap BOOLEAN DEFAULT FALSE,
            birth_date DATE,
            birth_country VARCHAR,
            height_inches INTEGER,
            weight_pounds INTEGER,
            shoots_catches VARCHAR,
            headshot VARCHAR,
            source_url VARCHAR,
            scraped_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_team_rosters_team ON team_rosters(team_code)",
        "CREATE INDEX IF NOT EXISTS idx_team_rosters_player ON team_rosters(player_name)",
        "CREATE INDEX IF NOT EXISTS idx_team_rosters_status ON team_rosters(roster_status)",
        "CREATE INDEX IF NOT EXISTS idx_team_rosters_date ON team_rosters(scraped_date)",
    ]
    conn = engine.connect()
    trans = conn.begin()
    try:
        for stmt in ddl:
            conn.execute(text(stmt))
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()

class _PgConnAdapter:
    """Adapter to provide DuckDB-like execute/fetch/commit API over SQLAlchemy connection."""
    def __init__(self, conn: "Connection", trans=None):
        self._conn = conn
        self._trans = trans
    def execute(self, sql: str, params: Optional[List[Any]] = None):
        if params is None:
            return self._conn.execute(text(sql))
        # Replace ? placeholders with :p{idx}
        bind = {f"p{i}": v for i, v in enumerate(params)}
        sql_named = sql
        for i in range(len(params)):
            sql_named = sql_named.replace('?', f":p{i}", 1)
        return self._conn.execute(text(sql_named), bind)
    def executemany(self, sql: str, seq_of_params: List[List[Any]]):
        # Simple looped executemany to avoid complex param binding
        for params in seq_of_params:
            self.execute(sql, params)
    def fetchone(self):
        raise NotImplementedError
    def fetchall(self):
        raise NotImplementedError
    def commit(self):
        if self._trans:
            self._trans.commit()
            self._trans = None
    def close(self):
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass


def initialize_database():
    """Initialize database schema in Postgres."""
    engine = _get_pg_engine()
    _init_postgres_schema(engine)
    logger.info("Postgres schema initialized")


@contextmanager
def get_connection(read_only: bool = False, retries: int = 10, retry_delay: float = 0.2):
    """
    Context manager for Postgres connections (via SQLAlchemy). Returns a thin
    adapter with ``execute`` and ``commit`` methods, mimicking the subset of the
    DB-API used by this module.
    """
    engine = _get_pg_engine()
    attempt = 0
    while True:
        try:
            conn = engine.connect()
            trans = None if read_only else conn.begin()
            adapter = _PgConnAdapter(conn, trans)
            break
        except Exception:
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(retry_delay)
    try:
        yield adapter
    finally:
        try:
            adapter.commit()
        except Exception:
            pass
        adapter.close()


# Transaction Operations
def insert_transaction(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """Insert transaction with de-duplication.

    Dedup key: (transaction_date, player_name, transaction_type, description)
    This avoids duplicates when scrapers re-run with identical events.
    """
    # Skip if duplicate exists
    exists = conn.execute(
        """
        SELECT id FROM transactions
        WHERE transaction_date = ? AND lower(player_name) = lower(?)
          AND lower(transaction_type) = lower(?) AND description = ?
        LIMIT 1
        """,
        [
            data.get('date'),
            data.get('player_name') or '',
            (data.get('type') or data.get('transaction_type') or ''),
            data.get('description') or ''
        ]
    ).fetchone()
    if exists:
        return exists[0]

    # Get next ID
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM transactions").fetchone()
    next_id = max_id_result[0] if max_id_result else 1

    result = conn.execute(
        """
        INSERT INTO transactions (
            id, transaction_date, player_name, player_id, team_from, team_to,
            transaction_type, description, source_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [
            next_id,
            data.get('date'),
            data.get('player_name'),
            data.get('player_id'),
            data.get('team_from'),
            data.get('team_to'),
            (data.get('type') or data.get('transaction_type')),
            data.get('description'),
            data.get('source_url')
        ]
    ).fetchone()

    conn.commit()
    return result[0] if result else None


def get_latest_transactions(conn: duckdb.DuckDBPyConnection, hours: int = 24) -> List[Dict]:
    """Get transactions from the last N hours"""
    cutoff = datetime.now() - timedelta(hours=hours)
    
    results = conn.execute("""
        SELECT 
            id, transaction_date as date, player_name, player_id,
            team_from, team_to, transaction_type, description,
            source_url, created_at
        FROM transactions
        WHERE created_at >= ?
        ORDER BY transaction_date DESC, created_at DESC
    """, [cutoff]).fetchall()
    
    return [dict(zip(['id', 'date', 'player_name', 'player_id', 'team_from', 
                      'team_to', 'transaction_type', 'description', 'source_url', 'created_at'], row))
            for row in results]


# Team News Operations
def insert_injury_report(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """
    Insert or update injury report with deduplication
    
    Deduplication by url_hash (source_url) or player_name + team_code
    """
    import hashlib
    import json
    
    source_url = (data.get('source_url') or '').strip()
    player_name = (data.get('player_name') or '').strip()
    team_code = (data.get('team_code') or '').strip().upper()
    
    if source_url:
        url_hash = hashlib.md5(source_url.encode()).hexdigest()
    else:
        url_hash = hashlib.md5(f"{team_code}|{player_name}".encode()).hexdigest()
    
    # Check if already exists
    exists = conn.execute("SELECT id FROM injury_reports WHERE url_hash = ?", [url_hash]).fetchone()
    if exists:
        # Update existing injury
        conn.execute("""
            UPDATE injury_reports SET
                injury_status = ?,
                injury_description = ?,
                return_estimate = ?,
                verified = ?,
                sources = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [
            data.get('injury_status'),
            data.get('injury_description'),
            data.get('return_estimate'),
            data.get('verified', False),
            json.dumps(data.get('sources', [])),
            exists[0]
        ])
        conn.commit()
        return exists[0]
    
    # Get next ID
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM injury_reports").fetchone()
    next_id = max_id_result[0] if max_id_result else 1
    
    # Insert new injury
    result = conn.execute("""
        INSERT INTO injury_reports (
            id, player_name, player_id, team_code, position, injury_type,
            injury_status, injury_description, return_estimate, placed_on_ir_date,
            source_url, url_hash, verified, sources
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, [
        next_id,
        data.get('player_name'),
        data.get('player_id'),
        data.get('team_code'),
        data.get('position'),
        data.get('injury_type'),
        data.get('injury_status'),
        data.get('injury_description'),
        data.get('return_estimate'),
        data.get('placed_on_ir_date') or data.get('date'),
        data.get('source_url'),
        url_hash,
        data.get('verified', False),
        json.dumps(data.get('sources', []))
    ]).fetchone()
    
    conn.commit()
    return result[0] if result else None


def get_team_injuries(conn: duckdb.DuckDBPyConnection, team_code: str = None, active_only: bool = True) -> List[Dict]:
    """
    Get injury reports, optionally filtered by team
    
    Args:
        team_code: Optional team code filter
        active_only: If True, only return active injuries (not returned to play)
    """
    query = "SELECT * FROM injury_reports WHERE 1=1"
    params = []
    
    if team_code:
        query += " AND team_code = ?"
        params.append(team_code.upper())
    
    if active_only:
        # Filter out players who are back/healthy
        query += " AND injury_status NOT IN ('Healthy', 'Active', 'Cleared')"
    
    query += " ORDER BY updated_at DESC"
    
    results = conn.execute(query, params).fetchall()
    
    columns = ['id', 'player_name', 'player_id', 'team_code', 'position', 'injury_type',
               'injury_status', 'injury_description', 'return_estimate', 'placed_on_ir_date',
               'source_url', 'url_hash', 'verified', 'sources', 'created_at', 'updated_at']
    
    return [dict(zip(columns, row)) for row in results]


def insert_team_news(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """Insert or update team news with robust deduplication.

    Primary key: url_hash when source_url present.
    Fallback key: md5(team_code|date|normalized_title) when source_url missing.
    """
    import hashlib

    source_url = (data.get('source_url') or '').strip()
    title_norm = (data.get('title') or '').strip().lower()
    team_code = (data.get('team_code') or '').strip().upper()
    date_str = str(data.get('date') or '')

    if source_url:
        url_hash = hashlib.md5(source_url.encode()).hexdigest()
    else:
        url_hash = hashlib.md5(f"{team_code}|{date_str}|{title_norm}".encode()).hexdigest()

    # Check if already exists
    exists = conn.execute("SELECT id FROM team_news WHERE url_hash = ?", [url_hash]).fetchone()
    if exists:
        conn.execute("UPDATE team_news SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", [exists[0]])
        conn.commit()
        return exists[0]
    
    # Get next ID
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM team_news").fetchone()
    next_id = max_id_result[0] if max_id_result else 1
    
    result = conn.execute("""
        INSERT INTO team_news (
            id, team_code, news_date, title, summary, content, source_url, image_url, url_hash, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, [
        next_id,
        data.get('team_code'),
        data.get('date'),
        data.get('title'),
        data.get('summary'),
        data.get('content'),
        data.get('source_url'),
        data.get('image_url'),
        url_hash,
        json.dumps(data.get('metadata', {}))
    ]).fetchone()
    
    conn.commit()
    return result[0] if result else None


def upsert_player_registry(conn: duckdb.DuckDBPyConnection, player_name: str, team_code: Optional[str] = None, player_id: Optional[str] = None):
    """Create or update a players_registry entry.
    Uses case-insensitive match on player_name.
    """
    if not player_name:
        return
    existing = conn.execute("""
        SELECT player_id, team_code FROM players_registry
        WHERE lower(player_name) = lower(?)
        LIMIT 1
    """, [player_name]).fetchone()
    if existing:
        # Update missing fields only
        if (not existing[0] and player_id) or (not existing[1] and team_code):
            conn.execute(
                """
                UPDATE players_registry
                SET player_id = COALESCE(?, player_id),
                    team_code = COALESCE(?, team_code)
                WHERE lower(player_name) = lower(?)
                """,
                [player_id, team_code, player_name]
            )
            conn.commit()
        return
    # Insert new
    conn.execute(
        """
        INSERT INTO players_registry (player_id, player_name, team_code)
        VALUES (?, ?, ?)
        """,
        [player_id, player_name, team_code]
    )
    conn.commit()


def bulk_insert_news_entities(conn: duckdb.DuckDBPyConnection, news_id: int, entities: List[Dict[str, Any]]):
    """Upsert-like insert for entity tags for a news item.

    Strategy: remove existing tags for this news_id, then insert the new set.
    Prevents duplicate rows when re-tagging the same article.
    """
    if not entities:
        return

    # Clear existing tags for this news to avoid duplicates
    conn.execute("DELETE FROM news_entities WHERE news_id = ?", [news_id])

    # Determine next id start
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM news_entities").fetchone()
    next_id = (max_id_result[0] or 0) + 1
    rows = []
    for e in entities:
        rows.append([
            next_id,
            news_id,
            e.get('entity_type'),
            e.get('team_code'),
            e.get('player_id'),
            e.get('player_name'),
            float(e.get('confidence', 0.8))
        ])
        next_id += 1
    conn.executemany(
        """
        INSERT INTO news_entities (
            id, news_id, entity_type, team_code, player_id, player_name, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows
    )
    conn.commit()


def get_team_news(conn: duckdb.DuckDBPyConnection, team_code: str, days: int = 7) -> List[Dict]:
    """Get team news from the last N days"""
    cutoff = datetime.now() - timedelta(days=days)
    
    results = conn.execute("""
        SELECT 
            id, team_code, news_date as date, title, summary,
            source_url, created_at
        FROM team_news
        WHERE team_code = ? AND news_date >= ?
        ORDER BY news_date DESC, created_at DESC
    """, [team_code, cutoff.date()]).fetchall()
    
    return [dict(zip(['id', 'team_code', 'date', 'title', 'summary', 'source_url', 'created_at'], row))
            for row in results]


# Entity Queries
def get_news_by_team_tag(conn: duckdb.DuckDBPyConnection, team_code: str, days: int = 7) -> List[Dict[str, Any]]:
    """Fetch news items tagged with a given team via news_entities."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    rows = conn.execute(
        """
        SELECT DISTINCT n.id, n.team_code, n.news_date as date, n.title, n.summary, n.content,
               n.source_url, n.image_url, n.metadata, n.created_at
        FROM team_news n
        JOIN news_entities e ON e.news_id = n.id AND e.entity_type = 'team' AND e.team_code = ?
        WHERE n.news_date >= ?
        ORDER BY n.created_at DESC
        """,
        [team_code, cutoff.date()]
    ).fetchall()
    return [
        dict(
            id=r[0], team_code=r[1], date=r[2], title=r[3], summary=r[4], content=r[5],
            source_url=r[6], image_url=r[7], metadata=(json.loads(r[8]) if r[8] else {}), created_at=r[9]
        ) for r in rows
    ]


def get_news_by_player(conn: duckdb.DuckDBPyConnection, player_id: Optional[str] = None, player_name: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
    """Fetch news items tagged with a given player (by id or case-insensitive name)."""
    if not player_id and not player_name:
        return []
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    if player_id:
        rows = conn.execute(
            """
            SELECT DISTINCT n.id, n.team_code, n.news_date as date, n.title, n.summary, n.content,
                   n.source_url, n.image_url, n.metadata, n.created_at
            FROM team_news n
            JOIN news_entities e ON e.news_id = n.id AND e.entity_type = 'player' AND e.player_id = ?
            WHERE n.news_date >= ?
            ORDER BY n.created_at DESC
            """,
            [player_id, cutoff.date()]
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT DISTINCT n.id, n.team_code, n.news_date as date, n.title, n.summary, n.content,
                   n.source_url, n.image_url, n.metadata, n.created_at
            FROM team_news n
            JOIN news_entities e ON e.news_id = n.id AND e.entity_type = 'player' AND lower(e.player_name) = lower(?)
            WHERE n.news_date >= ?
            ORDER BY n.created_at DESC
            """,
            [player_name, cutoff.date()]
        ).fetchall()
    return [
        dict(
            id=r[0], team_code=r[1], date=r[2], title=r[3], summary=r[4], content=r[5],
            source_url=r[6], image_url=r[7], metadata=(json.loads(r[8]) if r[8] else {}), created_at=r[9]
        ) for r in rows
    ]


def get_transactions_for_player(conn: duckdb.DuckDBPyConnection, player_id: Optional[str] = None, player_name: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
    """Transactions for a given player over last N days (by id or name)."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).date()
    if player_id:
        rows = conn.execute(
            """
            SELECT id, transaction_date as date, player_name, player_id, team_from, team_to,
                   transaction_type, description, source_url, created_at
            FROM transactions
            WHERE player_id = ? AND transaction_date >= ?
            ORDER BY transaction_date DESC, created_at DESC
            """,
            [player_id, cutoff]
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, transaction_date as date, player_name, player_id, team_from, team_to,
                   transaction_type, description, source_url, created_at
            FROM transactions
            WHERE lower(player_name) = lower(?) AND transaction_date >= ?
            ORDER BY transaction_date DESC, created_at DESC
            """,
            [player_name, cutoff]
        ).fetchall()
    return [
        dict(zip(['id','date','player_name','player_id','team_from','team_to','transaction_type','description','source_url','created_at'], r))
        for r in rows
    ]


def get_transactions_for_team(conn: duckdb.DuckDBPyConnection, team_code: str, days: int = 7) -> List[Dict[str, Any]]:
    """Transactions where team_from or team_to match team_code over last N days."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).date()
    rows = conn.execute(
        """
        SELECT id, transaction_date as date, player_name, player_id, team_from, team_to,
               transaction_type, description, source_url, created_at
        FROM transactions
        WHERE transaction_date >= ? AND (team_from = ? OR team_to = ?)
        ORDER BY transaction_date DESC, created_at DESC
        """,
        [cutoff, team_code, team_code]
    ).fetchall()
    return [
        dict(zip(['id','date','player_name','player_id','team_from','team_to','transaction_type','description','source_url','created_at'], r))
        for r in rows
    ]

# Game Summary Operations
def insert_game_summary(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> str:
    """Insert or update game summary"""
    # Check if exists
    exists = conn.execute("SELECT game_id FROM game_summaries WHERE game_id = ?", [data.get('game_id')]).fetchone()
    
    if exists:
        # Update
        conn.execute("""
            UPDATE game_summaries SET
                highlights = ?,
                top_performers = ?,
                period_summary = ?,
                game_recap = ?,
                image_url = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE game_id = ?
        """, [
            data.get('highlights'),
            json.dumps(data.get('top_performers', [])),
            json.dumps(data.get('period_summary', {})),
            data.get('game_recap'),
            data.get('image_url'),
            data.get('game_id')
        ])
    else:
        # Insert
        conn.execute("""
            INSERT INTO game_summaries (
                game_id, game_date, home_team, away_team, home_score, away_score,
                highlights, top_performers, period_summary, game_recap, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            data.get('game_id'),
            data.get('date'),
            data.get('home_team'),
            data.get('away_team'),
            data.get('home_score'),
            data.get('away_score'),
            data.get('highlights'),
            json.dumps(data.get('top_performers', [])),
            json.dumps(data.get('period_summary', {})),
            data.get('game_recap'),
            data.get('image_url')
        ])
    
    conn.commit()
    return data.get('game_id')


def get_game_summaries(conn: duckdb.DuckDBPyConnection, days: int = 1) -> List[Dict]:
    """Get game summaries from the last N days"""
    cutoff = datetime.now() - timedelta(days=days)
    
    results = conn.execute("""
        SELECT 
            game_id, game_date as date, home_team, away_team,
            home_score, away_score, highlights, top_performers, game_recap, image_url, created_at
        FROM game_summaries
        WHERE game_date >= ?
        ORDER BY game_date DESC, game_id DESC
    """, [cutoff.date()]).fetchall()
    
    return [dict(zip(['game_id', 'date', 'home_team', 'away_team', 'home_score', 
                      'away_score', 'highlights', 'top_performers', 'game_recap', 'image_url', 'created_at'], 
                     [r[0], r[1], r[2], r[3], r[4], r[5], r[6], 
                      json.loads(r[7]) if r[7] else [], r[8], r[9], r[10]]))
            for r in results]


# Player Update Operations
def insert_player_update(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """Insert or update player performance update"""
    # Get next ID
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM player_updates").fetchone()
    next_id = max_id_result[0] if max_id_result else 1
    
    result = conn.execute("""
        INSERT INTO player_updates (
            id, player_id, player_name, team_code, update_date, summary,
            recent_stats, notable_achievements
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
        RETURNING id
    """, [
        next_id,
        data.get('player_id'),
        data.get('player_name'),
        data.get('team_code'),
        data.get('date'),
        data.get('summary'),
        json.dumps(data.get('recent_stats', {})),
        json.dumps(data.get('notable_achievements', []))
    ]).fetchone()
    
    conn.commit()
    return result[0] if result else None


def get_player_update(conn: duckdb.DuckDBPyConnection, player_id: str) -> Optional[Dict]:
    """Get latest player update"""
    result = conn.execute("""
        SELECT 
            id, player_id, player_name, team_code, update_date as date,
            summary, recent_stats, notable_achievements, created_at
        FROM player_updates
        WHERE player_id = ?
        ORDER BY update_date DESC
        LIMIT 1
    """, [player_id]).fetchone()
    
    if result:
        return {
            'id': result[0],
            'player_id': result[1],
            'player_name': result[2],
            'team_code': result[3],
            'date': result[4],
            'summary': result[5],
            'recent_stats': json.loads(result[6]) if result[6] else {},
            'notable_achievements': json.loads(result[7]) if result[7] else [],
            'created_at': result[8]
        }
    return None


# Daily Article Operations
def insert_daily_article(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> str:
    """Insert or update daily article"""
    # Check if exists
    exists = conn.execute("SELECT article_date FROM daily_articles WHERE article_date = ?", [data.get('date')]).fetchone()
    
    if exists:
        # Update
        conn.execute("""
            UPDATE daily_articles SET
                title = ?,
                content = ?,
                summary = ?,
                metadata = ?,
                source_count = ?,
                image_url = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE article_date = ?
        """, [
            data.get('title'),
            data.get('content'),
            data.get('summary'),
            json.dumps(data.get('metadata', {})),
            data.get('source_count', 0),
            data.get('image_url'),
            data.get('date')
        ])
    else:
        # Insert
        conn.execute("""
            INSERT INTO daily_articles (
                article_date, title, content, summary, metadata, source_count, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            data.get('date'),
            data.get('title'),
            data.get('content'),
            data.get('summary'),
            json.dumps(data.get('metadata', {})),
            data.get('source_count', 0),
            data.get('image_url')
        ])
    
    conn.commit()
    return data.get('date')


def get_daily_article(conn: duckdb.DuckDBPyConnection, date: Optional[str] = None) -> Optional[Dict]:
    """Get daily article by date (or latest if no date specified)"""
    if date:
        result = conn.execute("""
            SELECT article_date as date, title, content, summary, metadata, source_count, image_url, created_at
            FROM daily_articles
            WHERE article_date = ?
        """, [date]).fetchone()
    else:
        result = conn.execute("""
            SELECT article_date as date, title, content, summary, metadata, source_count, image_url, created_at
            FROM daily_articles
            ORDER BY article_date DESC
            LIMIT 1
        """).fetchone()
    
    if result:
        meta_val = result[4]
        if isinstance(meta_val, (bytes, str)):
            try:
                meta_val = json.loads(meta_val) if meta_val else {}
            except Exception:
                meta_val = {}
        elif not isinstance(meta_val, dict):
            meta_val = {}
        return {
            'date': result[0],
            'title': result[1],
            'content': result[2],
            'summary': result[3],
            'metadata': meta_val,
            'source_count': result[5],
            'image_url': result[6],
            'created_at': result[7]
        }
    return None


# Aggregation for Article Generation
def get_recent_content(conn: duckdb.DuckDBPyConnection, hours: int = 24) -> Dict[str, Any]:
    """Get all recent content for article generation"""
    cutoff = datetime.now() - timedelta(hours=hours)
    
    transactions = get_latest_transactions(conn, hours)
    games = get_game_summaries(conn, days=1)
    
    # Get recent team news across all teams
    team_news_results = conn.execute("""
        SELECT team_code, title, summary
        FROM team_news
        WHERE created_at >= ?
        ORDER BY created_at DESC
        LIMIT 20
    """, [cutoff]).fetchall()
    
    team_news = [{'team': row[0], 'title': row[1], 'summary': row[2]} 
                 for row in team_news_results]
    
    return {
        'transactions': transactions,
        'games': games,
        'team_news': team_news,
        'timestamp': datetime.now().isoformat()
    }


# Contract Operations
def insert_player_contract(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """Insert player contract with deduplication"""
    import hashlib
    
    player_name = (data.get('player_name') or '').strip()
    signing_date = data.get('signing_date')
    contract_type = data.get('contract_type') or ''
    
    dedup_key = f"{player_name}|{signing_date}|{contract_type}"
    
    exists = conn.execute(
        "SELECT id FROM player_contracts WHERE lower(player_name) = lower(?) AND signing_date = ? AND contract_type = ?",
        [player_name, signing_date, contract_type]
    ).fetchone()
    
    if exists:
        return exists[0]
    
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM player_contracts").fetchone()
    next_id = max_id_result[0] if max_id_result else 1
    
    result = conn.execute("""
        INSERT INTO player_contracts (
            id, player_name, player_id, team_code, contract_type, signing_date,
            signed_by, length_years, total_value, expiry_status, cap_hit, cap_percent, source_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, [
        next_id,
        data.get('player_name'),
        data.get('player_id'),
        data.get('team_code'),
        data.get('contract_type'),
        data.get('signing_date'),
        data.get('signed_by'),
        data.get('length_years'),
        data.get('total_value'),
        data.get('expiry_status'),
        data.get('cap_hit'),
        data.get('cap_percent'),
        data.get('source_url')
    ]).fetchone()
    
    conn.commit()
    return result[0] if result else None


def insert_contract_detail(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """Insert contract yearly detail"""
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM contract_details").fetchone()
    next_id = max_id_result[0] if max_id_result else 1
    
    result = conn.execute("""
        INSERT INTO contract_details (
            id, contract_id, season, clause, cap_hit, cap_percent, aav,
            performance_bonuses, signing_bonuses, base_salary, total_salary, minors_salary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, [
        next_id,
        data.get('contract_id'),
        data.get('season'),
        data.get('clause'),
        data.get('cap_hit'),
        data.get('cap_percent'),
        data.get('aav'),
        data.get('performance_bonuses'),
        data.get('signing_bonuses'),
        data.get('base_salary'),
        data.get('total_salary'),
        data.get('minors_salary')
    ]).fetchone()
    
    conn.commit()
    return result[0] if result else None


def insert_player_career_stat(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """Insert player career stat with deduplication"""
    player_name = (data.get('player_name') or '').strip()
    season = data.get('season')
    team_code = data.get('team_code')
    is_playoffs = data.get('is_playoffs', False)
    
    exists = conn.execute(
        "SELECT id FROM player_career_stats WHERE lower(player_name) = lower(?) AND season = ? AND team_code = ? AND is_playoffs = ?",
        [player_name, season, team_code, is_playoffs]
    ).fetchone()
    
    if exists:
        return exists[0]
    
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM player_career_stats").fetchone()
    next_id = max_id_result[0] if max_id_result else 1
    
    result = conn.execute("""
        INSERT INTO player_career_stats (
            id, player_name, player_id, season, team_code, games_played, goals, assists,
            points, pts_per_game, toi, plus_minus, shot_percent, pim, is_playoffs
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, [
        next_id,
        data.get('player_name'),
        data.get('player_id'),
        data.get('season'),
        data.get('team_code'),
        data.get('games_played'),
        data.get('goals'),
        data.get('assists'),
        data.get('points'),
        data.get('pts_per_game'),
        data.get('toi'),
        data.get('plus_minus'),
        data.get('shot_percent'),
        data.get('pim'),
        data.get('is_playoffs', False)
    ]).fetchone()
    
    conn.commit()
    return result[0] if result else None


def get_player_contracts(conn: duckdb.DuckDBPyConnection, player_name: str) -> List[Dict]:
    """Get all contracts for a player"""
    results = conn.execute("""
        SELECT 
            id, player_name, player_id, team_code, contract_type, signing_date,
            signed_by, length_years, total_value, expiry_status, cap_hit, cap_percent,
            source_url, created_at
        FROM player_contracts
        WHERE lower(player_name) = lower(?)
        ORDER BY signing_date DESC
    """, [player_name]).fetchall()
    
    return [dict(zip(['id', 'player_name', 'player_id', 'team_code', 'contract_type', 
                      'signing_date', 'signed_by', 'length_years', 'total_value', 
                      'expiry_status', 'cap_hit', 'cap_percent', 'source_url', 'created_at'], row))
            for row in results]


def get_contract_details(conn: duckdb.DuckDBPyConnection, contract_id: int) -> List[Dict]:
    """Get yearly details for a contract"""
    results = conn.execute("""
        SELECT 
            id, contract_id, season, clause, cap_hit, cap_percent, aav,
            performance_bonuses, signing_bonuses, base_salary, total_salary, minors_salary
        FROM contract_details
        WHERE contract_id = ?
        ORDER BY season
    """, [contract_id]).fetchall()
    
    return [dict(zip(['id', 'contract_id', 'season', 'clause', 'cap_hit', 'cap_percent',
                      'aav', 'performance_bonuses', 'signing_bonuses', 'base_salary', 'total_salary', 'minors_salary'], row))
            for row in results]


# Player career stats functions removed - focusing only on contract data


# Team Roster/Depth Chart Operations
def insert_team_roster_player(conn: duckdb.DuckDBPyConnection, data: Dict[str, Any]) -> int:
    """Insert or update team roster player with deduplication"""
    team_code = (data.get('team_code') or '').strip().upper()
    player_name = (data.get('player_name') or '').strip()
    roster_status = data.get('roster_status')
    scraped_date = data.get('scraped_date')
    
    if not team_code or not player_name or not roster_status:
        logger.warning(f"Missing required fields for roster insert: team={team_code}, player={player_name}, status={roster_status}")
        return None
    
    exists = conn.execute(
        """SELECT id FROM team_rosters 
           WHERE team_code = ? AND lower(player_name) = lower(?) 
           AND roster_status = ? AND scraped_date = ?""",
        [team_code, player_name, roster_status, scraped_date]
    ).fetchone()
    
    if exists:
        conn.execute("""
            UPDATE team_rosters SET
                position = ?,
                jersey_number = ?,
                cap_hit = ?,
                cap_percent = ?,
                age = ?,
                contract_expiry = ?,
                handed = ?,
                birthplace = ?,
                draft_info = ?,
                drafted_by = ?,
                draft_year = ?,
                draft_round = ?,
                draft_overall = ?,
                must_sign_date = ?,
                dead_cap = ?,
                birth_date = ?,
                birth_country = ?,
                height_inches = ?,
                weight_pounds = ?,
                shoots_catches = ?,
                headshot = ?,
                source_url = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [
            data.get('position'),
            data.get('jersey_number'),
            data.get('cap_hit'),
            data.get('cap_percent'),
            data.get('age'),
            data.get('contract_expiry'),
            data.get('handed'),
            data.get('birthplace'),
            data.get('draft_info'),
            data.get('drafted_by'),
            data.get('draft_year'),
            data.get('draft_round'),
            data.get('draft_overall'),
            data.get('must_sign_date'),
            data.get('dead_cap', False),
            data.get('birth_date'),
            data.get('birth_country'),
            data.get('height_inches'),
            data.get('weight_pounds'),
            data.get('shoots_catches'),
            data.get('headshot'),
            data.get('source_url'),
            exists[0]
        ])
        conn.commit()
        return exists[0]
    
    max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM team_rosters").fetchone()
    next_id = max_id_result[0] if max_id_result else 1
    
    result = conn.execute("""
        INSERT INTO team_rosters (
            id, team_code, player_name, player_id, position, roster_status,
            jersey_number, cap_hit, cap_percent, age, contract_expiry,
            handed, birthplace, draft_info, drafted_by, draft_year,
            draft_round, draft_overall, must_sign_date, dead_cap,
            birth_date, birth_country, height_inches, weight_pounds, shoots_catches, headshot,
            source_url, scraped_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, [
        next_id,
        team_code,
        data.get('player_name'),
        data.get('player_id'),
        data.get('position'),
        data.get('roster_status'),
        data.get('jersey_number'),
        data.get('cap_hit'),
        data.get('cap_percent'),
        data.get('age'),
        data.get('contract_expiry'),
        data.get('handed'),
        data.get('birthplace'),
        data.get('draft_info'),
        data.get('drafted_by'),
        data.get('draft_year'),
        data.get('draft_round'),
        data.get('draft_overall'),
        data.get('must_sign_date'),
        data.get('dead_cap', False),
        data.get('birth_date'),
        data.get('birth_country'),
        data.get('height_inches'),
        data.get('weight_pounds'),
        data.get('shoots_catches'),
        data.get('headshot'),
        data.get('source_url'),
        data.get('scraped_date')
    ]).fetchone()
    
    conn.commit()
    return result[0] if result else None


def get_team_roster(conn: duckdb.DuckDBPyConnection, team_code: str, latest_only: bool = True) -> List[Dict]:
    """Get team roster/depth chart"""
    team_code = team_code.upper()
    
    if latest_only:
        latest_date = conn.execute(
            "SELECT MAX(scraped_date) FROM team_rosters WHERE team_code = ?",
            [team_code]
        ).fetchone()
        
        if not latest_date or not latest_date[0]:
            return []
        
        results = conn.execute("""
            SELECT 
                id, team_code, player_name, player_id, position, roster_status,
                jersey_number, cap_hit, cap_percent, age, contract_expiry,
                handed, birthplace, draft_info, drafted_by, draft_year,
                draft_round, draft_overall, must_sign_date, dead_cap,
                birth_date, birth_country, height_inches, weight_pounds, shoots_catches, headshot,
                source_url, scraped_date, created_at
            FROM team_rosters
            WHERE team_code = ? AND scraped_date = ?
            ORDER BY 
                CASE roster_status
                    WHEN 'roster' THEN 1
                    WHEN 'signed_roster' THEN 1
                    WHEN 'non_roster' THEN 2
                    WHEN 'signed_non_roster' THEN 2
                    WHEN 'unsigned' THEN 3
                    ELSE 4
                END,
                player_name
        """, [team_code, latest_date[0]]).fetchall()
    else:
        results = conn.execute("""
            SELECT 
                id, team_code, player_name, player_id, position, roster_status,
                jersey_number, cap_hit, cap_percent, age, contract_expiry,
                handed, birthplace, draft_info, drafted_by, draft_year,
                draft_round, draft_overall, must_sign_date, dead_cap,
                birth_date, birth_country, height_inches, weight_pounds, shoots_catches, headshot,
                source_url, scraped_date, created_at
            FROM team_rosters
            WHERE team_code = ?
            ORDER BY scraped_date DESC, player_name
        """, [team_code]).fetchall()
    
    return [dict(zip(['id', 'team_code', 'player_name', 'player_id', 'position', 'roster_status',
                      'jersey_number', 'cap_hit', 'cap_percent', 'age', 'contract_expiry',
                      'handed', 'birthplace', 'draft_info', 'drafted_by', 'draft_year',
                      'draft_round', 'draft_overall', 'must_sign_date', 'dead_cap',
                      'birth_date', 'birth_country', 'height_inches', 'weight_pounds', 'shoots_catches', 'headshot',
                      'source_url', 'scraped_date', 'created_at'], row))
            for row in results]


def delete_team_roster_snapshot(conn, team_code: str, scraped_date) -> int:
    """Delete a specific roster snapshot for a team"""
    result = conn.execute(
        "DELETE FROM team_rosters WHERE team_code = ? AND scraped_date = ?",
        [team_code.upper(), scraped_date]
    )
    # SQLAlchemy Result has rowcount; adapter.commit() will finalize
    deleted = getattr(result, "rowcount", 0) or 0
    conn.commit()
    return int(deleted)


# Initialize database on module import
try:
    initialize_database()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
