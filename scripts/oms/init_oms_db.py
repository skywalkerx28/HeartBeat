#!/usr/bin/env python3
"""
HeartBeat Engine - Initialize OMS Database
Creates all OMS tables in PostgreSQL via SQLAlchemy
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from backend.ontology.models.metadata import Base
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def init_oms_database():
    """Initialize OMS database schema and tables"""
    
    # Get DATABASE_URL
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        logger.error("")
        logger.error("Load your .env file first:")
        logger.error("  export $(cat .env | xargs)")
        logger.error("")
        sys.exit(1)
    
    # Mask password for logging
    masked_url = database_url.split('@')[0].split(':')[0] + ":***@" + database_url.split('@')[1]
    logger.info(f"Database: {masked_url}")
    logger.info("")
    
    try:
        # Create engine
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=False
        )
        
        # Test connection
        logger.info("[1/3] Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"  Connected to: {version.split(',')[0]}")
        
        # Create oms schema
        logger.info("")
        logger.info("[2/3] Creating OMS schema...")
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS oms"))
            conn.commit()
            logger.info("  OMS schema created")
        
        # Create all tables
        logger.info("")
        logger.info("[3/3] Creating OMS tables...")
        Base.metadata.create_all(engine)
        logger.info("  All OMS tables created successfully")
        
        # Verify tables
        logger.info("")
        logger.info("Verifying OMS tables...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'oms' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            for table in tables:
                logger.info(f"  ✓ oms.{table}")
        
        logger.info("")
        logger.info("=" * 50)
        logger.info("OMS DATABASE INITIALIZATION COMPLETE")
        logger.info("=" * 50)
        logger.info("")
        logger.info(f"Schema: oms")
        logger.info(f"Tables: {len(tables)} created")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Load schema: python3 -m backend.ontology.cli load backend/ontology/schemas/v0.1/schema.yaml --user admin")
        logger.info("  2. Start backend: python3 -m uvicorn backend.main:app --reload")
        logger.info("")
        
    except Exception as e:
        logger.error(f"Failed to initialize OMS database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_oms_database()

