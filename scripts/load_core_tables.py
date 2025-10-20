"""
HeartBeat Engine - Load Native BigQuery Core Tables
Load hot facts from external tables into native BigQuery for performance
"""

from google.cloud import bigquery
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = "heartbeat-474020"
DATASET_RAW = "raw"
DATASET_CORE = "core"


def create_core_tables(client: bigquery.Client):
    """Create native core tables with partitioning and clustering."""
    
    # NOTE: These are placeholder schemas - actual schemas depend on your Parquet structure
    # Adjust field names and types based on actual data
    
    logger.info("Creating core.snap_roster_scd2...")
    
    roster_query = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_CORE}.snap_roster_scd2`
    CLUSTER BY team_abbrev, nhl_player_id
    AS
    SELECT 
      *,
      CURRENT_DATE() AS valid_from,
      DATE('9999-12-31') AS valid_to,
      TRUE AS is_current
    FROM `{PROJECT_ID}.{DATASET_RAW}.rosters_parquet`
    WHERE snapshot_date = (
      SELECT MAX(snapshot_date) 
      FROM `{PROJECT_ID}.{DATASET_RAW}.rosters_parquet`
    )
    """
    
    try:
        query_job = client.query(roster_query)
        result = query_job.result()
        logger.info(f"✓ Created core.snap_roster_scd2 ({query_job.total_bytes_processed / 1024 / 1024:.2f} MB processed)")
    except Exception as e:
        logger.error(f"Failed to create roster table: {e}")
        logger.info("  This may be due to missing snapshot_date column - check your Parquet schema")
    
    # Note: Play-by-play table creation requires knowledge of date column structure
    # Commenting out for now - uncomment when schema is confirmed
    
    logger.info("Core tables creation attempted")
    logger.info("Note: Adjust schemas in load_core_tables.py based on your actual Parquet structure")


def verify_tables(client: bigquery.Client):
    """Verify core tables were created successfully."""
    
    logger.info("\nVerifying core tables...")
    
    query = f"""
    SELECT 
      table_name,
      table_type,
      ROUND(size_bytes / 1024 / 1024, 2) as size_mb,
      row_count
    FROM `{PROJECT_ID}.{DATASET_CORE}.__TABLES__`
    ORDER BY table_name
    """
    
    try:
        query_job = client.query(query)
        results = query_job.result()
        
        print("\nCore Tables:")
        print("-" * 60)
        for row in results:
            print(f"  {row.table_name:30} {row.size_mb:10.2f} MB  {row.row_count:10} rows")
        print("-" * 60)
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")


def main():
    """Load native BigQuery core tables."""
    
    print("HeartBeat Engine - Load Core Tables")
    print("=" * 50)
    print(f"Project:  {PROJECT_ID}")
    print(f"Dataset:  {DATASET_CORE}")
    print("")
    
    client = bigquery.Client(project=PROJECT_ID)
    
    # Create core tables
    create_core_tables(client)
    
    # Verify
    verify_tables(client)
    
    print("")
    print("=" * 50)
    print("✓ Core table loading complete")
    print("=" * 50)
    print("")
    print("NOTE: Review table schemas and adjust load_core_tables.py")
    print("      as needed based on your actual Parquet structure.")
    print("")
    
    return 0


if __name__ == "__main__":
    exit(main())

