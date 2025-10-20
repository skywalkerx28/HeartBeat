"""
HeartBeat Engine - Daily Ontology Refresh Tasks
Celery Beat tasks for keeping ontology fresh

Daily sequence:
1. Ingest new data (pbp, transactions, depth charts)
2. Extract/aggregate (per-game -> season profiles)
3. Sync to lake (bronze -> silver)
4. Rebuild ontology indexes (embeddings)
5. Update freshness metadata
"""

from celery import shared_task
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@shared_task(name="ontology.daily_refresh")
def daily_ontology_refresh() -> Dict[str, Any]:
    """
    Master task: orchestrate daily ontology refresh.
    
    Runs as single Celery Beat task, chains subtasks.
    """
    
    logger.info("=" * 60)
    logger.info("DAILY ONTOLOGY REFRESH STARTED")
    logger.info("=" * 60)
    
    start_time = datetime.utcnow()
    results = {}
    
    # Step 1: Ingest new data
    try:
        logger.info("[1/5] Ingesting new data...")
        results['ingest'] = ingest_new_data()
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        results['ingest'] = {'error': str(e)}
    
    # Step 2: Extract and aggregate
    try:
        logger.info("[2/5] Extracting and aggregating...")
        results['extract'] = extract_and_aggregate()
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        results['extract'] = {'error': str(e)}
    
    # Step 3: Sync to GCS lake
    try:
        logger.info("[3/5] Syncing to GCS lake...")
        results['sync'] = sync_to_gcs_lake()
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        results['sync'] = {'error': str(e)}
    
    # Step 4: Rebuild embeddings
    try:
        logger.info("[4/5] Rebuilding ontology embeddings...")
        results['embeddings'] = rebuild_ontology_embeddings()
    except Exception as e:
        logger.error(f"Embedding rebuild failed: {e}")
        results['embeddings'] = {'error': str(e)}
    
    # Step 5: Update freshness
    try:
        logger.info("[5/5] Updating freshness metadata...")
        results['freshness'] = update_freshness_metadata()
    except Exception as e:
        logger.error(f"Freshness update failed: {e}")
        results['freshness'] = {'error': str(e)}
    
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info("=" * 60)
    logger.info(f"DAILY ONTOLOGY REFRESH COMPLETED in {elapsed:.1f}s")
    logger.info("=" * 60)
    
    return {
        'completed_at': datetime.utcnow().isoformat(),
        'elapsed_seconds': elapsed,
        'results': results
    }


def ingest_new_data() -> Dict[str, Any]:
    """
    Step 1: Ingest new data from sources.
    
    - Fetch latest play-by-play from NHL API
    - Scrape depth charts
    - Fetch transactions
    - Update player profiles
    """
    
    logger.info("Ingesting new data sources...")
    
    results = {
        'pbp_games': 0,
        'depth_charts': 0,
        'transactions': 0,
        'player_profiles': 0
    }
    
    try:
        # Import scraper functions
        from backend.bot.scrapers import scrape_nhl_games, scrape_depth_charts
        from backend.bot.tasks import fetch_transactions
        
        # Scrape yesterday's games (avoid in-progress games)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Play-by-play
        try:
            games = scrape_nhl_games(date=yesterday)
            results['pbp_games'] = len(games) if games else 0
            logger.info(f"  Ingested {results['pbp_games']} games")
        except Exception as e:
            logger.warning(f"  PBP ingestion failed: {e}")
        
        # Depth charts (all teams)
        try:
            depth_charts = scrape_depth_charts()
            results['depth_charts'] = len(depth_charts) if depth_charts else 0
            logger.info(f"  Ingested {results['depth_charts']} depth charts")
        except Exception as e:
            logger.warning(f"  Depth chart ingestion failed: {e}")
        
        # Transactions (last 24 hours)
        try:
            transactions = fetch_transactions(days=1)
            results['transactions'] = len(transactions) if transactions else 0
            logger.info(f"  Ingested {results['transactions']} transactions")
        except Exception as e:
            logger.warning(f"  Transaction ingestion failed: {e}")
        
    except ImportError:
        logger.warning("Scraper modules not available, skipping ingestion")
    
    return results


def extract_and_aggregate() -> Dict[str, Any]:
    """
    Step 2: Extract metrics and aggregate to season profiles.
    
    - Process per-game stats -> season profiles
    - Update team season profiles
    - Calculate advanced metrics (xG, Corsi, etc.)
    """
    
    logger.info("Extracting and aggregating data...")
    
    results = {
        'player_profiles_updated': 0,
        'team_profiles_updated': 0
    }
    
    try:
        # Run aggregation scripts
        data_root = Path(__file__).parent.parent.parent / "data"
        processed_root = data_root / "processed"
        
        # Update league player stats (aggregate from PBP)
        # This would be a separate aggregation script
        logger.info("  Aggregating player season stats...")
        # TODO: Call aggregation function
        results['player_profiles_updated'] = 0
        
        # Update team profiles
        logger.info("  Aggregating team season stats...")
        # TODO: Call team aggregation function
        results['team_profiles_updated'] = 0
        
    except Exception as e:
        logger.error(f"Aggregation error: {e}")
    
    return results


def sync_to_gcs_lake() -> Dict[str, Any]:
    """
    Step 3: Sync processed data to GCS silver tier.
    
    - Upload new Parquet files
    - Update BigLake external tables
    - Maintain partitioning structure
    """
    
    logger.info("Syncing to GCS lake...")
    
    results = {
        'files_uploaded': 0,
        'bytes_uploaded': 0
    }
    
    try:
        # Check if GCS is enabled
        if not os.getenv("USE_BIGQUERY_ANALYTICS", "false").lower() == "true":
            logger.info("  BigQuery analytics disabled, skipping GCS sync")
            return results
        
        # Import sync client
        import subprocess
        script_path = Path(__file__).parent.parent.parent / "scripts" / "sync_parquet_to_gcs.py"
        
        if script_path.exists():
            logger.info(f"  Running sync script: {script_path}")
            result = subprocess.run(
                ["python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout
            )
            
            if result.returncode == 0:
                logger.info(f"  Sync completed successfully")
                # Parse output for stats
                results['files_uploaded'] = result.stdout.count("Uploading")
            else:
                logger.error(f"  Sync failed: {result.stderr}")
        else:
            logger.warning(f"  Sync script not found: {script_path}")
    
    except Exception as e:
        logger.error(f"GCS sync error: {e}")
    
    return results


def rebuild_ontology_embeddings() -> Dict[str, Any]:
    """
    Step 4: Rebuild embeddings for changed objects.
    
    - Embed new/updated players, teams, games
    - Upsert to vector backend (Pinecone/Vertex)
    - Use object_ref (type, id) as metadata
    """
    
    logger.info("Rebuilding ontology embeddings...")
    
    results = {
        'embeddings_created': 0,
        'embeddings_updated': 0,
        'vector_backend': os.getenv("VECTOR_BACKEND", "vertex")
    }
    
    try:
        # Get changed objects (last 24 hours)
        changed_objects = get_changed_objects(hours=24)
        
        logger.info(f"  Found {len(changed_objects)} changed objects")
        
        # Generate embeddings
        embeddings = generate_object_embeddings(changed_objects)
        
        # Upsert to vector backend
        if embeddings:
            upsert_count = upsert_to_vector_backend(embeddings)
            results['embeddings_created'] = upsert_count
            logger.info(f"  Upserted {upsert_count} embeddings")
        
    except Exception as e:
        logger.error(f"Embedding rebuild error: {e}")
    
    return results


def get_changed_objects(hours: int = 24) -> List[Dict[str, Any]]:
    """Get objects that changed in the last N hours."""
    
    from google.cloud import bigquery
    
    project_id = os.getenv("GCP_PROJECT", "heartbeat-474020")
    
    try:
        client = bigquery.Client(project=project_id)
        
        # Query for recently updated players
        query = f"""
        SELECT 
            'Player' AS object_type,
            CAST(nhl_player_id AS STRING) AS object_id,
            full_name AS title,
            CONCAT(full_name, ' - ', position, ' - ', current_team) AS summary
        FROM `{project_id}.raw.objects_player`
        WHERE last_updated >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        
        UNION ALL
        
        SELECT 
            'Team' AS object_type,
            team_abbrev AS object_id,
            team_name AS title,
            CONCAT(team_name, ' (', division, ' Division)') AS summary
        FROM `{project_id}.raw.objects_team`
        WHERE last_updated >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        
        UNION ALL
        
        SELECT 
            'Game' AS object_type,
            CAST(game_id AS STRING) AS object_id,
            CONCAT(away_team, ' @ ', home_team) AS title,
            CONCAT(away_team, ' @ ', home_team, ' (', CAST(game_date AS STRING), ')') AS summary
        FROM `{project_id}.raw.objects_game`
        WHERE last_updated >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        """
        
        df = client.query(query).to_dataframe()
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"Failed to get changed objects: {e}")
        return []


def generate_object_embeddings(objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate embeddings for objects using summary text."""
    
    # Placeholder: in production, use OpenAI embeddings or Vertex AI
    # For now, return objects with mock embeddings
    
    embeddings = []
    
    for obj in objects:
        embeddings.append({
            'id': f"{obj['object_type']}:{obj['object_id']}",
            'values': [0.0] * 1536,  # Mock 1536-dim embedding
            'metadata': {
                'object_type': obj['object_type'],
                'object_id': obj['object_id'],
                'title': obj['title'],
                'summary': obj['summary']
            }
        })
    
    return embeddings


def upsert_to_vector_backend(embeddings: List[Dict[str, Any]]) -> int:
    """Upsert embeddings to vector backend."""
    
    try:
        from orchestrator.tools.pinecone_mcp_client import VectorStoreFactory
        
        backend = VectorStoreFactory.create_backend()
        
        # Upsert to ontology namespace
        # Note: This would need to be async in real implementation
        # backend.upsert_vectors(embeddings, namespace="ontology")
        
        logger.info(f"Would upsert {len(embeddings)} vectors to {backend.__class__.__name__}")
        return len(embeddings)
        
    except Exception as e:
        logger.error(f"Vector upsert failed: {e}")
        return 0


def update_freshness_metadata() -> Dict[str, Any]:
    """
    Step 5: Update freshness metadata in BigQuery.
    
    Mark objects with last_updated timestamps so LLM/UI
    can prioritize fresh data.
    """
    
    logger.info("Updating freshness metadata...")
    
    results = {
        'tables_updated': 0
    }
    
    try:
        from google.cloud import bigquery
        
        project_id = os.getenv("GCP_PROJECT", "heartbeat-474020")
        client = bigquery.Client(project=project_id)
        
        # Update freshness table (simple key-value store)
        freshness_query = f"""
        CREATE TABLE IF NOT EXISTS `{project_id}.raw.ontology_freshness` (
            object_type STRING,
            last_refresh TIMESTAMP,
            record_count INT64,
            refresh_status STRING
        );
        
        MERGE `{project_id}.raw.ontology_freshness` AS target
        USING (
            SELECT 'Player' AS object_type, CURRENT_TIMESTAMP() AS last_refresh, 
                   COUNT(*) AS record_count, 'success' AS refresh_status
            FROM `{project_id}.raw.objects_player`
        ) AS source
        ON target.object_type = source.object_type
        WHEN MATCHED THEN
            UPDATE SET 
                last_refresh = source.last_refresh,
                record_count = source.record_count,
                refresh_status = source.refresh_status
        WHEN NOT MATCHED THEN
            INSERT (object_type, last_refresh, record_count, refresh_status)
            VALUES (source.object_type, source.last_refresh, source.record_count, source.refresh_status);
        """
        
        client.query(freshness_query).result()
        results['tables_updated'] = 1
        logger.info("  Freshness metadata updated")
        
    except Exception as e:
        logger.error(f"Freshness update error: {e}")
    
    return results


# Celery Beat schedule configuration
# Add this to your main Celery config:
"""
from celery.schedules import crontab

beat_schedule = {
    'daily-ontology-refresh': {
        'task': 'ontology.daily_refresh',
        'schedule': crontab(hour=4, minute=0),  # Run at 4 AM daily
        'options': {'expires': 3600}
    }
}
"""
