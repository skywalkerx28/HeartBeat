"""
HeartBeat Engine - Sync CBA Parquet Files to GCS
Upload processed CBA structured rules to silver tier
"""

from google.cloud import storage
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = "heartbeat-474020"
BUCKET_NAME = "heartbeat-474020-lake"
LOCAL_ROOT = Path(__file__).parent.parent / "data" / "processed" / "reference"


def sync_cba_files():
    """Upload CBA Parquet files to GCS silver/reference/cba/"""
    logger.info("=" * 60)
    logger.info("SYNC CBA PARQUET TO GCS")
    logger.info("=" * 60)
    logger.info(f"Local:  {LOCAL_ROOT}")
    logger.info(f"Remote: gs://{BUCKET_NAME}/silver/reference/cba/")
    logger.info("")
    
    # Initialize storage client
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    
    # Files to upload
    files_to_upload = [
        ("cba_documents.parquet", "silver/reference/cba/cba_documents.parquet"),
        ("cba_rules_all.parquet", "silver/reference/cba/cba_rules_all.parquet"),
        ("cba_rules_current.parquet", "silver/reference/cba/cba_rules_current.parquet"),
        # Full-document ingestion artifacts (optional)
        ("cba_document_text.parquet", "silver/reference/cba/cba_document_text.parquet"),
        ("cba_articles.parquet", "silver/reference/cba/cba_articles.parquet"),
        ("cba_chunks.parquet", "silver/reference/cba/cba_chunks.parquet"),
    ]
    
    uploaded = 0
    skipped = 0
    
    for local_file, gcs_path in files_to_upload:
        local_path = LOCAL_ROOT / local_file
        
        if not local_path.exists():
            logger.warning(f"  Skipping {local_file} (not found locally)")
            continue
        
        blob = bucket.blob(gcs_path)
        
        # Check if already exists
        if blob.exists():
            logger.info(f"  Overwriting: {local_file}")
        else:
            logger.info(f"  Uploading:   {local_file}")
        
        # Upload
        blob.upload_from_filename(str(local_path))
        uploaded += 1
        
        # Get file size
        file_size = local_path.stat().st_size / 1024  # KB
        logger.info(f"    Size: {file_size:.1f} KB")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"SYNC COMPLETE: {uploaded} files uploaded, {skipped} skipped")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Files available at:")
    for _, gcs_path in files_to_upload:
        logger.info(f"  gs://{BUCKET_NAME}/{gcs_path}")
    logger.info("")
    logger.info("Next: bq query < scripts/cba/create_cba_views.sql")


if __name__ == "__main__":
    sync_cba_files()
