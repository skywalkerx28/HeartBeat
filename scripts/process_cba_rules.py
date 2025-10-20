"""
HeartBeat Engine - Process CBA Structured Rules
Convert CBA rule CSVs to Parquet and prepare for BigQuery ingestion

This implements Option D: structured rules extraction first, deferring RAG chunking.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_REF = PROJECT_ROOT / "data" / "reference"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed" / "reference"

PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)


def process_cba_documents():
    """Convert CBA documents metadata to Parquet."""
    logger.info("Processing CBA documents metadata...")
    
    csv_path = DATA_REF / "cba_documents.csv"
    if not csv_path.exists():
        logger.error(f"CBA documents CSV not found: {csv_path}")
        return None
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Convert date columns
    df['effective_date'] = pd.to_datetime(df['effective_date'])
    df['expiration_date'] = pd.to_datetime(df['expiration_date'])
    df['last_updated'] = datetime.now()
    df['uploaded_by'] = 'system'
    
    # Output path
    output_path = PROCESSED_ROOT / "cba_documents.parquet"
    
    # Write Parquet with ZSTD compression
    df.to_parquet(
        output_path,
        compression='zstd',
        compression_level=3,
        index=False
    )
    
    logger.info(f"  Created: {output_path} ({len(df)} documents)")
    return output_path


def process_cba_rules():
    """Convert CBA structured rules to Parquet with temporal validation."""
    logger.info("Processing CBA structured rules...")
    
    csv_path = DATA_REF / "cba_structured_rules.csv"
    if not csv_path.exists():
        logger.error(f"CBA rules CSV not found: {csv_path}")
        return None
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Convert date columns
    df['effective_from'] = pd.to_datetime(df['effective_from'])
    df['effective_to'] = pd.to_datetime(df['effective_to'])
    
    # Add metadata
    df['last_updated'] = datetime.now()
    df['verified_by'] = 'manual_extraction'
    
    # Validate temporal consistency
    logger.info("Validating temporal consistency...")
    for idx, row in df.iterrows():
        if pd.notna(row['effective_to']):
            if row['effective_from'] >= row['effective_to']:
                logger.warning(
                    f"  Rule {row['rule_id']}: effective_from >= effective_to"
                )
    
    # Check for supersession chains
    supersession_map = df[df['supersedes_rule_id'].notna()][
        ['rule_id', 'supersedes_rule_id']
    ].set_index('rule_id')['supersedes_rule_id'].to_dict()
    
    logger.info(f"  Supersession chains found: {len(supersession_map)}")
    for new_rule, old_rule in supersession_map.items():
        logger.info(f"    {new_rule} -> {old_rule}")
    
    # Identify current rules
    current_rules = df[df['is_current_version'] == True]
    logger.info(f"  Current active rules: {len(current_rules)}")
    
    # Output paths
    output_all = PROCESSED_ROOT / "cba_rules_all.parquet"
    output_current = PROCESSED_ROOT / "cba_rules_current.parquet"
    
    # Write all rules
    df.to_parquet(
        output_all,
        compression='zstd',
        compression_level=3,
        index=False
    )
    logger.info(f"  Created: {output_all} ({len(df)} rules)")
    
    # Write current-only rules
    current_rules.to_parquet(
        output_current,
        compression='zstd',
        compression_level=3,
        index=False
    )
    logger.info(f"  Created: {output_current} ({len(current_rules)} current rules)")
    
    return output_all, output_current


def generate_summary_report():
    """Generate human-readable summary of CBA rules."""
    logger.info("\n" + "=" * 70)
    logger.info("CBA RULES SUMMARY")
    logger.info("=" * 70)
    
    csv_path = DATA_REF / "cba_structured_rules.csv"
    df = pd.read_csv(csv_path)
    
    # Group by category
    categories = df.groupby('rule_category').size().sort_values(ascending=False)
    
    logger.info("\nRules by Category:")
    for category, count in categories.items():
        logger.info(f"  {category}: {count} rules")
    
    # Current rules
    current = df[df['is_current_version'] == True]
    logger.info(f"\nCurrent Active Rules: {len(current)} / {len(df)} total")
    
    # Document sources
    sources = df.groupby('source_document').size()
    logger.info("\nRules by Source Document:")
    for source, count in sources.items():
        logger.info(f"  {source}: {count} rules")
    
    # Key rules
    logger.info("\nKey Current Rules:")
    for _, row in current.iterrows():
        if row['value_numeric'] and pd.notna(row['value_numeric']):
            logger.info(
                f"  {row['rule_name']}: ${row['value_numeric']:,.0f}"
                if row['rule_category'] == 'Salary Cap'
                else f"  {row['rule_name']}: {row['value_numeric']}"
            )
        elif row['value_text']:
            logger.info(f"  {row['rule_name']}: {row['value_text']}")
    
    logger.info("=" * 70)


def main():
    """Run full CBA processing pipeline."""
    logger.info("=" * 70)
    logger.info("HEARTBEAT CBA RULES PROCESSING")
    logger.info("=" * 70)
    logger.info("")
    
    # Process documents
    doc_path = process_cba_documents()
    
    # Process rules
    rules_paths = process_cba_rules()
    
    # Generate summary
    generate_summary_report()
    
    logger.info("\n" + "=" * 70)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 70)
    logger.info("\nNext steps:")
    logger.info("1. Upload PDFs to GCS: scripts/upload_cba_pdfs.sh")
    logger.info("2. Sync Parquet to GCS: python scripts/sync_cba_to_gcs.py")
    logger.info("3. Create BigQuery views: bq query < scripts/create_cba_views.sql")
    logger.info("4. Test retrieval: python scripts/test_cba_retrieval.py")


if __name__ == "__main__":
    main()

