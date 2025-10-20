#!/usr/bin/env python3
"""
DuckDB Clip Index - Production Grade
Thread-safe clip metadata storage with analytics capabilities
Designed for local development and BigQuery migration
"""

import duckdb
import threading
import time
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from queue import Queue, Empty
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import atexit


@dataclass
class ClipIndexEntry:
    """Clip index entry for database storage"""
    clip_id: str
    clip_hash: str
    output_path: str
    thumbnail_path: str
    source_video: str
    start_timecode_s: float
    end_timecode_s: float
    duration_s: float
    game_id: str
    game_date: str
    season: str
    period: int
    player_id: str
    player_name: Optional[str]
    team_code: str
    opponent_code: str
    event_type: str
    outcome: Optional[str]
    zone: Optional[str]
    file_size_bytes: int
    processing_time_s: float
    cache_hit: bool
    extra_metadata: Optional[str] = None  # JSON string
    
    def to_tuple(self) -> tuple:
        """Convert to tuple for INSERT (excludes created_at/updated_at - use defaults)"""
        return (
            self.clip_id, self.clip_hash, self.output_path, self.thumbnail_path,
            self.source_video, self.start_timecode_s, self.end_timecode_s, self.duration_s,
            self.game_id, self.game_date, self.season, self.period,
            self.player_id, self.player_name, self.team_code, self.opponent_code,
            self.event_type, self.outcome, self.zone,
            self.file_size_bytes, self.processing_time_s, self.cache_hit,
            self.extra_metadata
        )


class DuckDBClipIndex:
    """
    Thread-safe DuckDB index for clip metadata
    
    SIMPLIFIED: Direct writes with retry logic (no background thread)
    DuckDB handles concurrent writes from same process natively
    
    Features:
    - Thread-safe direct writes with retry on busy
    - Concurrent readers (unlimited)
    - Automatic Parquet export capability
    - BigQuery-ready schema
    - Analytics-optimized indexes
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize DuckDB clip index
        
        Args:
            db_path: Path to DuckDB file (default: data/clips/clip_index.duckdb)
        """
        if db_path is None:
            workspace = Path(__file__).parent.parent.parent
            db_path = workspace / "data/clips/clip_index.duckdb"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Lock for write operations
        self.write_lock = threading.Lock()
        
        # Initialize schema
        self._init_schema()
        
        print(f"DuckDB Clip Index initialized: {self.db_path}")
    
    def _init_schema(self):
        """Initialize database schema"""
        print(f"Initializing schema at {self.db_path}...")
        con = duckdb.connect(str(self.db_path))
        
        try:
            print("Creating tables and indexes...")
            # Create clips table
            con.execute("""
                CREATE TABLE IF NOT EXISTS clips (
                    clip_id VARCHAR PRIMARY KEY,
                    clip_hash VARCHAR UNIQUE NOT NULL,
                    
                    -- File locations
                    output_path VARCHAR NOT NULL,
                    thumbnail_path VARCHAR NOT NULL,
                    
                    -- Timing
                    source_video VARCHAR NOT NULL,
                    start_timecode_s DOUBLE NOT NULL,
                    end_timecode_s DOUBLE NOT NULL,
                    duration_s DOUBLE NOT NULL,
                    
                    -- Game context
                    game_id VARCHAR NOT NULL,
                    game_date VARCHAR NOT NULL,
                    season VARCHAR NOT NULL,
                    period INTEGER NOT NULL,
                    
                    -- Player/Event
                    player_id VARCHAR NOT NULL,
                    player_name VARCHAR,
                    team_code VARCHAR NOT NULL,
                    opponent_code VARCHAR NOT NULL,
                    event_type VARCHAR NOT NULL,
                    outcome VARCHAR,
                    zone VARCHAR,
                    
                    -- Metadata
                    file_size_bytes BIGINT NOT NULL,
                    processing_time_s DOUBLE,
                    cache_hit BOOLEAN DEFAULT FALSE,
                    extra_metadata VARCHAR,
                    
                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for fast lookups
            con.execute("CREATE INDEX IF NOT EXISTS idx_clips_player ON clips(player_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_clips_game ON clips(game_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_clips_event ON clips(event_type)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_clips_date ON clips(game_date)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_clips_hash ON clips(clip_hash)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_clips_team ON clips(team_code)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_clips_period ON clips(game_id, period)")
            
            con.commit()
            print("Schema initialized successfully")
        finally:
            con.close()
    
    def insert_clip(self, entry: ClipIndexEntry, block: bool = False) -> None:
        """
        Insert a clip entry (thread-safe with lock)
        
        Args:
            entry: ClipIndexEntry to insert
            block: Ignored (kept for API compatibility)
        """
        with self.write_lock:
            # Retry small transient binder/attach conflicts under parallel loads
            for attempt in range(3):
                con = duckdb.connect(str(self.db_path))
                try:
                    con.execute("""
                        INSERT INTO clips (
                            clip_id, clip_hash, output_path, thumbnail_path,
                            source_video, start_timecode_s, end_timecode_s, duration_s,
                            game_id, game_date, season, period,
                            player_id, player_name, team_code, opponent_code,
                            event_type, outcome, zone,
                            file_size_bytes, processing_time_s, cache_hit, extra_metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (clip_id) DO UPDATE SET updated_at = now()
                    """, entry.to_tuple())
                    con.commit()
                    return
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(0.05 * (attempt + 1))
                finally:
                    try:
                        con.close()
                    except Exception:
                        pass
    
    def batch_insert_clips(self, entries: List[ClipIndexEntry], block: bool = True) -> None:
        """
        Insert multiple clips efficiently (thread-safe with lock)
        
        Args:
            entries: List of ClipIndexEntry to insert
            block: Ignored (kept for API compatibility)
        """
        if not entries:
            return
        
        with self.write_lock:
            tuples = [e.to_tuple() for e in entries]
            for attempt in range(3):
                con = duckdb.connect(str(self.db_path))
                try:
                    con.executemany("""
                        INSERT INTO clips (
                            clip_id, clip_hash, output_path, thumbnail_path,
                            source_video, start_timecode_s, end_timecode_s, duration_s,
                            game_id, game_date, season, period,
                            player_id, player_name, team_code, opponent_code,
                            event_type, outcome, zone,
                            file_size_bytes, processing_time_s, cache_hit, extra_metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (clip_id) DO UPDATE SET updated_at = now()
                    """, tuples)
                    con.commit()
                    return
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(0.05 * (attempt + 1))
                finally:
                    try:
                        con.close()
                    except Exception:
                        pass
    
    def find_by_clip_id(self, clip_id: str) -> Optional[Dict[str, Any]]:
        """Find clip by clip_id (concurrent-safe read)"""
        # Use separate connection without read_only flag to avoid conflicts
        con = duckdb.connect(str(self.db_path))
        try:
            result = con.execute(
                "SELECT * FROM clips WHERE clip_id = ?",
                [clip_id]
            ).fetchone()
            
            if result:
                return self._row_to_dict(result)
            return None
        finally:
            con.close()
    
    def find_by_hash(self, clip_hash: str) -> Optional[Dict[str, Any]]:
        """Check if clip exists by hash (for caching)"""
        con = duckdb.connect(str(self.db_path))
        try:
            result = con.execute(
                "SELECT * FROM clips WHERE clip_hash = ?",
                [clip_hash]
            ).fetchone()
            
            if result:
                return self._row_to_dict(result)
            return None
        finally:
            con.close()
    
    def query_clips(
        self,
        player_ids: Optional[List[str]] = None,
        game_ids: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
        team_codes: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query clips with filters (concurrent-safe read)
        
        Returns:
            List of clip dictionaries
        """
        con = duckdb.connect(str(self.db_path))
        
        try:
            # Build dynamic query
            where_clauses = []
            params = []
            
            if player_ids:
                placeholders = ','.join(['?'] * len(player_ids))
                where_clauses.append(f"player_id IN ({placeholders})")
                params.extend(player_ids)
            
            if game_ids:
                placeholders = ','.join(['?'] * len(game_ids))
                where_clauses.append(f"game_id IN ({placeholders})")
                params.extend(game_ids)
            
            if event_types:
                placeholders = ','.join(['?'] * len(event_types))
                where_clauses.append(f"event_type IN ({placeholders})")
                params.extend(event_types)
            
            if team_codes:
                placeholders = ','.join(['?'] * len(team_codes))
                where_clauses.append(f"team_code IN ({placeholders})")
                params.extend(team_codes)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
                SELECT * FROM clips 
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
            """
            params.append(limit)
            
            results = con.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in results]
        finally:
            con.close()
    
    def get_all_clips(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all clips (for API listing)"""
        con = duckdb.connect(str(self.db_path))
        try:
            results = con.execute(
                "SELECT * FROM clips ORDER BY created_at DESC LIMIT ?",
                [limit]
            ).fetchall()
            return [self._row_to_dict(row) for row in results]
        finally:
            con.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        con = duckdb.connect(str(self.db_path))
        try:
            total = con.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
            total_size = con.execute("SELECT SUM(file_size_bytes) FROM clips").fetchone()[0] or 0
            total_duration = con.execute("SELECT SUM(duration_s) FROM clips").fetchone()[0] or 0
            unique_players = con.execute("SELECT COUNT(DISTINCT player_id) FROM clips").fetchone()[0]
            unique_games = con.execute("SELECT COUNT(DISTINCT game_id) FROM clips").fetchone()[0]
            cache_hits = con.execute("SELECT COUNT(*) FROM clips WHERE cache_hit = TRUE").fetchone()[0]
            
            return {
                'total_clips': total,
                'total_size_bytes': int(total_size),
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'total_duration_s': float(total_duration),
                'total_duration_min': round(total_duration / 60, 2),
                'unique_players': unique_players,
                'unique_games': unique_games,
                'cache_hits': cache_hits,
                'cache_hit_rate': round(cache_hits / total * 100, 1) if total > 0 else 0
            }
        finally:
            con.close()
    
    def export_to_parquet(self, output_path: str) -> None:
        """Export entire index to Parquet for data lake / BigQuery"""
        con = duckdb.connect(str(self.db_path))
        try:
            con.execute(f"""
                COPY clips TO '{output_path}' 
                (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
            """)
            print(f"Exported clips to Parquet: {output_path}")
        finally:
            con.close()
    
    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """Convert DuckDB row tuple to dictionary"""
        if not row:
            return {}
        
        # Column order matches table schema
        return {
            'clip_id': row[0],
            'clip_hash': row[1],
            'output_path': row[2],
            'thumbnail_path': row[3],
            'source_video': row[4],
            'start_timecode_s': row[5],
            'end_timecode_s': row[6],
            'duration_s': row[7],
            'game_id': row[8],
            'game_date': row[9],
            'season': row[10],
            'period': row[11],
            'player_id': row[12],
            'player_name': row[13],
            'team_code': row[14],
            'opponent_code': row[15],
            'event_type': row[16],
            'outcome': row[17],
            'zone': row[18],
            'file_size_bytes': row[19],
            'processing_time_s': row[20],
            'cache_hit': row[21],
            'extra_metadata': row[22],
            'created_at': row[23],
            'updated_at': row[24]
        }
    
    def shutdown(self):
        """No-op for API compatibility (no background threads to clean up)"""
        pass
    
    def migrate_from_json(self, json_path: str) -> int:
        """Migrate clips from old JSON index to DuckDB"""
        json_file = Path(json_path)
        if not json_file.exists():
            return 0
        
        with open(json_file, 'r') as f:
            old_index = json.load(f)
        
        entries = []
        for clip_hash, clip_data in old_index.items():
            metadata = clip_data.get('metadata', {})
            
            # Extract game_date from clip_id or game_id
            game_id = metadata.get('game_id', 'unknown')
            game_date = game_id[:8] if len(game_id) >= 8 else '20250101'
            
            # Extract season
            season = '2025-2026'  # Default
            
            # Create entry
            entry = ClipIndexEntry(
                clip_id=clip_data['clip_id'],
                clip_hash=clip_hash,
                output_path=clip_data['output_path'],
                thumbnail_path=clip_data.get('thumbnail_path', ''),
                source_video='',  # Not available in old index
                start_timecode_s=0.0,
                end_timecode_s=clip_data.get('duration_s', 0.0),
                duration_s=clip_data.get('duration_s', 0.0),
                game_id=game_id,
                game_date=game_date,
                season=season,
                period=metadata.get('period', 1),
                player_id=metadata.get('player_id', ''),
                player_name=None,
                team_code='',
                opponent_code='',
                event_type=metadata.get('event_type', ''),
                outcome=metadata.get('outcome'),
                zone=None,
                file_size_bytes=clip_data.get('file_size_bytes', 0),
                processing_time_s=0.0,
                cache_hit=False,
                extra_metadata=json.dumps(metadata) if metadata else None
            )
            entries.append(entry)
        
        if entries:
            self.batch_insert_clips(entries, block=True)
            print(f"Migrated {len(entries)} clips from JSON to DuckDB")
        
        return len(entries)


# Global instance (singleton pattern)
_global_index: Optional[DuckDBClipIndex] = None
_index_lock = threading.Lock()


def get_clip_index() -> DuckDBClipIndex:
    """Get or create global clip index instance (thread-safe singleton)"""
    global _global_index
    
    if _global_index is None:
        with _index_lock:
            if _global_index is None:  # Double-check locking
                _global_index = DuckDBClipIndex()
    
    return _global_index


def main():
    """Test the DuckDB index"""
    print("\n" + "="*70)
    print("DuckDB Clip Index Test (Direct Writes)")
    print("="*70 + "\n")
    
    # Initialize index
    print("1. Initializing index...")
    index = DuckDBClipIndex()
    
    # Create test entry
    test_entry = ClipIndexEntry(
        clip_id="test_direct_001",
        clip_hash=hashlib.md5(b"test_direct").hexdigest(),
        output_path="/test/clip_direct.mp4",
        thumbnail_path="/test/clip_direct.jpg",
        source_video="/source/p1.mp4",
        start_timecode_s=100.0,
        end_timecode_s=108.0,
        duration_s=8.0,
        game_id="20038",
        game_date="20251012",
        season="2025-2026",
        period=1,
        player_id="8478463",
        player_name="Anthony Beauvillier",
        team_code="WSH",
        opponent_code="NYR",
        event_type="CONTROLLED EXIT FROM DZ",
        outcome="successful",
        zone="dz",
        file_size_bytes=14567890,
        processing_time_s=3.2,
        cache_hit=False,
        extra_metadata=json.dumps({"test": True})
    )
    
    # Insert
    print("\n2. Inserting clip...")
    index.insert_clip(test_entry)
    print("   ✓ Clip inserted")
    
    # Query by clip_id
    print("\n3. Querying by clip_id...")
    result = index.find_by_clip_id("test_direct_001")
    if result:
        print(f"   ✓ Found: {result['player_name']} - {result['event_type']}")
    else:
        print("   ✗ NOT FOUND")
    
    # Get stats
    print("\n4. Getting stats...")
    stats = index.get_stats()
    print(f"   Total clips: {stats['total_clips']}")
    print(f"   Total size: {stats['total_size_mb']} MB")
    
    print("\n✅ DuckDB Index Test Complete!")


if __name__ == "__main__":
    main()

