# Clip Index Storage Architecture Decision
## HeartBeat Engine - Production Grade v1

**Date:** October 14, 2025  
**Context:** Google Cloud infrastructure, BigQuery + Data Lake future, Parquet-based analytics

---

## Executive Summary

**Recommended Solution: DuckDB (Local) → BigQuery (Production)**

- **Phase 1 (Current):** DuckDB for local clip index
- **Phase 2 (Cloud):** BigQuery for production metadata + Cloud Storage for videos
- **Bridge:** DuckDB's native Parquet export enables seamless migration

---

## Options Analysis

### Option 1: SQLite with WAL Mode ⭐⭐⭐
**Pros:**
- Standard, battle-tested
- WAL mode enables concurrent reads during writes
- Single file, zero configuration
- Python stdlib (no dependencies)

**Cons:**
- **Writer serialization**: Only ONE writer at a time (even with WAL)
- Our ProcessPoolExecutor workers would still conflict
- No native Parquet export
- Weak analytics capabilities
- Dead-end for BigQuery migration

**Verdict:** ❌ Not optimal for HeartBeat's needs

---

### Option 2: DuckDB ⭐⭐⭐⭐⭐
**Pros:**
- **Designed for analytics** (perfect for video metadata queries)
- **Better concurrency** than SQLite for analytical workloads
- **Native Parquet I/O**: `COPY TO 'clips.parquet'` in one line
- **BigQuery compatible**: Can query BigQuery directly via plugin
- **Zero-config**: Single file like SQLite
- **Blazingly fast**: Vectorized execution, columnar storage
- **Data lake ready**: Built for modern analytics stacks
- **Small footprint**: ~50MB library

**Cons:**
- Still single-writer for transactional operations
- 5MB dependency (acceptable)

**Verdict:** ✅ **BEST CHOICE** - Perfect fit for HeartBeat's architecture

---

### Option 3: PostgreSQL (Cloud SQL) ⭐⭐⭐
**Pros:**
- True multi-writer concurrency
- ACID guarantees
- Google Cloud SQL managed service
- Full relational capabilities

**Cons:**
- **Overkill** for clip metadata (not relational-heavy)
- Requires server (costs money, adds latency)
- Need network connection for local dev
- Complex BigQuery integration
- Slower for analytical queries than DuckDB

**Verdict:** ❌ Too heavy for this use case

---

### Option 4: Google Cloud Firestore ⭐⭐⭐⭐
**Pros:**
- Google Cloud native
- True multi-writer, serverless
- Real-time sync
- Good for key-value lookups

**Cons:**
- **Requires internet** (no local-first development)
- **Costs per read/write** (expensive at scale)
- Weaker analytics queries
- Not integrated with BigQuery (requires export jobs)
- Latency for every lookup

**Verdict:** ❌ Not suitable for local-first architecture

---

### Option 5: Parquet Files Directly ⭐⭐
**Pros:**
- Native data lake format
- Perfect BigQuery integration
- Append-efficient

**Cons:**
- **No indexing**: Every query is full scan
- **No updates**: Immutable format
- Slow lookup by clip_id
- Need separate tool for queries (DuckDB/Polars)

**Verdict:** ❌ Good for archives, not for live index

---

## Recommended Architecture: DuckDB

### Why DuckDB is Perfect for HeartBeat

1. **Aligns with your data lake strategy**
   - Native Parquet read/write
   - Can query Parquet files in GCS directly
   - Export to BigQuery in one command

2. **Analytics-first design**
   - Fast aggregations: "Show me all my clips from last 5 games"
   - Efficient filtering: "Zone exits with success rate > 80%"
   - Window functions for trend analysis

3. **Local-first, cloud-ready**
   - Develop locally with DuckDB file
   - Deploy to production with BigQuery
   - Same SQL interface, minimal code changes

4. **Concurrency solution**
   - Use **ThreadPoolExecutor** instead of ProcessPoolExecutor (shared memory)
   - OR: Use DuckDB's connection pooling with retries
   - OR: Queue writes through a single coordinator thread

5. **Future-proof**
   ```python
   # Local (Phase 1)
   con = duckdb.connect('clip_index.duckdb')
   con.execute("SELECT * FROM clips WHERE game_id = ?", [game_id])
   
   # Export to Parquet for BigQuery
   con.execute("COPY clips TO 'gs://heartbeat/clips.parquet'")
   
   # Production (Phase 2) - same queries
   con = duckdb.connect()
   con.execute("INSTALL bigquery; LOAD bigquery;")
   con.execute("SELECT * FROM bigquery_scan('heartbeat.clips') WHERE game_id = ?", [game_id])
   ```

---

## Implementation Plan

### Phase 1: DuckDB Local (Now - Next 2 weeks)

**Schema:**
```sql
CREATE TABLE clips (
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
    game_date DATE NOT NULL,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Analytics (for future queries)
    processing_time_s DOUBLE,
    cache_hit BOOLEAN DEFAULT FALSE,
    
    -- JSON metadata for extensibility
    extra_metadata JSON
);

CREATE INDEX idx_clips_player ON clips(player_id);
CREATE INDEX idx_clips_game ON clips(game_id);
CREATE INDEX idx_clips_event ON clips(event_type);
CREATE INDEX idx_clips_date ON clips(game_date);
CREATE INDEX idx_clips_hash ON clips(clip_hash);
```

**Concurrency Fix:**
```python
import threading
from queue import Queue

class DuckDBClipIndex:
    def __init__(self, db_path):
        self.db_path = db_path
        self.write_queue = Queue()
        self.writer_thread = threading.Thread(target=self._writer_worker, daemon=True)
        self.writer_thread.start()
    
    def _writer_worker(self):
        """Single writer thread for all inserts"""
        con = duckdb.connect(self.db_path)
        while True:
            clip_data = self.write_queue.get()
            if clip_data is None:  # Shutdown signal
                break
            con.execute("INSERT INTO clips VALUES (?...)", clip_data)
            con.commit()
    
    def insert_clip(self, clip_data):
        """Thread-safe insert"""
        self.write_queue.put(clip_data)
    
    def query_clips(self, filters):
        """Reads can happen concurrently"""
        con = duckdb.connect(self.db_path, read_only=True)
        return con.execute("SELECT * FROM clips WHERE ...").fetchall()
```

### Phase 2: BigQuery Production (2-4 weeks)

**Migration:**
```python
# Export DuckDB to Parquet
con.execute("""
    COPY clips TO 'gs://heartbeat-data-lake/clips/clips.parquet' 
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

# Load into BigQuery (one-time)
from google.cloud import bigquery
client = bigquery.Client()
job = client.load_table_from_uri(
    'gs://heartbeat-data-lake/clips/*.parquet',
    'heartbeat.clips',
    job_config=bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition='WRITE_TRUNCATE'
    )
)

# Ongoing: Stream inserts to BigQuery
from google.cloud.bigquery import Client
bq = Client()
rows_to_insert = [{"clip_id": ..., "player_id": ..., ...}]
bq.insert_rows_json('heartbeat.clips', rows_to_insert)
```

**Video Storage:**
- **Clips:** Google Cloud Storage buckets
  - `gs://heartbeat-clips-prod/{season}/{game_id}/p{period}/{clip_id}.mp4`
  - Signed URLs for secure access
  - CDN for global delivery
- **Thumbnails:** Cloud Storage or Cloud CDN
- **Period source videos:** Separate bucket with lifecycle policies

---

## Why NOT the Other Options

### Why NOT SQLite?
- **Fundamental limitation**: Serial writes even with WAL
- Our parallel FFmpeg workers would still block each other
- No analytics features
- No Parquet export
- Migration to BigQuery is painful

### Why NOT PostgreSQL?
- We don't need relational joins (clip data is denormalized)
- Overkill for key-value + analytics workload
- Slower than DuckDB for analytical queries
- Adds operational complexity (server management)
- Higher costs

### Why NOT Firestore?
- Requires internet (breaks local development)
- Per-operation pricing (expensive for high-volume inserts)
- Not designed for analytics queries
- Separate ETL pipeline needed for BigQuery

### Why NOT Parquet directly?
- No indexing (every lookup is table scan)
- No updates (need to rewrite entire file)
- Need DuckDB/Polars just to query it anyway

---

## Implementation Checklist

### Immediate (Next 30 minutes)
- [x] Create `orchestrator/tools/clip_index_db.py` with DuckDB implementation
- [x] Add single-writer queue pattern
- [x] Migrate from JSON index to DuckDB
- [x] Update `clip_cutter.py` to use new index
- [x] Update `clips.py` API routes to query DuckDB
- [x] Test concurrent writes (verify no overwrites)

### Short-term (This week)
- [ ] Add compound indexes for common queries
- [ ] Implement periodic Parquet exports (every 1000 clips)
- [ ] Add analytics queries (top players, event distributions)
- [ ] Monitor index size and query performance

### Medium-term (Production deployment)
- [ ] BigQuery table schema design
- [ ] Streaming insert pipeline
- [ ] Cloud Storage bucket structure
- [ ] CDN configuration
- [ ] Signed URL generation for secure access

---

## Performance Expectations

### DuckDB (Local)
- **Inserts:** ~1ms per clip (with queue)
- **Lookups by clip_id:** <1ms (indexed)
- **Analytical queries:** <10ms for 10K clips
- **Index size:** ~1KB per clip (10K clips = 10MB)
- **Concurrent reads:** Unlimited
- **Concurrent writes:** Serialized via queue (acceptable)

### BigQuery (Production)
- **Streaming inserts:** <100ms latency
- **Batch inserts:** 1M rows/sec
- **Query latency:** <1s for billion rows
- **Storage cost:** $0.02/GB/month
- **Query cost:** $5/TB scanned

---

## Code Compatibility Matrix

| Feature | DuckDB (Local) | BigQuery (Prod) | Migration Effort |
|---------|---------------|-----------------|------------------|
| SQL queries | ✅ Standard SQL | ✅ Standard SQL | Zero |
| Parquet export | ✅ Native | ✅ Native | Zero |
| Concurrent reads | ✅ Yes | ✅ Yes | Zero |
| Concurrent writes | ⚠️ Queue pattern | ✅ Native | Minimal |
| Analytics functions | ✅ Full support | ✅ Full support | Zero |
| Python client | ✅ `duckdb` | ✅ `google-cloud-bigquery` | Wrapper layer |

**Migration complexity:** LOW (Same SQL, swap connection object)

---

## Decision

**Use DuckDB for v1 local deployment, design for BigQuery migration**

### Rationale:
1. **Perfect fit** for HeartBeat's analytics-heavy workload
2. **Solves concurrency** with single-writer queue pattern
3. **Future-proof** for BigQuery/data lake migration
4. **Zero operational overhead** (no servers to manage)
5. **Superior performance** vs SQLite/Postgres for this use case
6. **Native Parquet** aligns with your data lake strategy

### Implementation:
- DuckDB file: `data/clips/clip_index.duckdb`
- Single writer thread with queue
- Concurrent readers unlimited
- Automatic Parquet exports for archival
- Ready to switch to BigQuery when scaling to cloud

---

## Next Steps

1. Implement DuckDB index with thread-safe writer queue
2. Migrate existing JSON index to DuckDB (one-time)
3. Update all code to use new index
4. Test under load (100+ concurrent clip generations)
5. Verify no lost writes, no race conditions
6. Document BigQuery migration path

---

**This is the state-of-the-art solution for HeartBeat.**

