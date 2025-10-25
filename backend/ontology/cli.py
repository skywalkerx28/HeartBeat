"""
HeartBeat Engine - OMS Management CLI
NHL Advanced Analytics Platform

Command-line interface for managing ontology schemas.
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ontology.models.metadata import Base
from backend.ontology.services.registry import SchemaRegistry
from backend.ontology.api.dependencies import DATABASE_URL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_session():
    """Create database session"""
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def load_and_publish_schema(schema_path: Path, created_by: str = "system"):
    """
    Load schema from YAML and publish as active version.
    
    Args:
        schema_path: Path to schema YAML file
        created_by: User identifier loading the schema
    """
    session = get_session()
    
    try:
        registry = SchemaRegistry(session, schema_path.parent)
        
        # Load schema
        logger.info(f"Loading schema from {schema_path}")
        schema_version = registry.load_schema_from_yaml(
            schema_path,
            created_by=created_by,
            auto_publish=False
        )
        
        logger.info(f"Schema {schema_version.version} loaded successfully")
        
        # Publish schema
        logger.info(f"Publishing schema {schema_version.version}")
        registry.publish_schema(schema_version.version, created_by)
        
        logger.info(f"Schema {schema_version.version} published and activated")
        
        # Display summary
        object_types = registry.get_all_object_types()
        link_types = registry.get_all_link_types()
        
        logger.info("Schema Summary:")
        logger.info(f"  Version: {schema_version.version}")
        logger.info(f"  Namespace: {schema_version.namespace}")
        logger.info(f"  Object Types: {len(object_types)}")
        logger.info(f"  Link Types: {len(link_types)}")
        logger.info(f"  Status: {schema_version.status}")
        logger.info(f"  Active: {schema_version.is_active}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load and publish schema: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def list_versions():
    """List all schema versions"""
    session = get_session()
    
    try:
        registry = SchemaRegistry(session)
        versions = registry.list_versions()
        
        if not versions:
            logger.info("No schema versions found")
            return
        
        logger.info("Schema Versions:")
        logger.info("-" * 80)
        logger.info(f"{'Version':<15} {'Status':<12} {'Active':<8} {'Created':<20} {'Namespace'}")
        logger.info("-" * 80)
        
        for v in versions:
            logger.info(
                f"{v.version:<15} {v.status:<12} {'✓' if v.is_active else '':<8} "
                f"{v.created_at.strftime('%Y-%m-%d %H:%M'):<20} {v.namespace}"
            )
        
    finally:
        session.close()


def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="HeartBeat OMS Management CLI"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Load and publish command
    load_parser = subparsers.add_parser(
        "load",
        help="Load and publish schema from YAML"
    )
    load_parser.add_argument(
        "schema_file",
        type=str,
        help="Path to schema YAML file"
    )
    load_parser.add_argument(
        "--user",
        type=str,
        default="system",
        help="User identifier (default: system)"
    )
    
    # List versions command
    list_parser = subparsers.add_parser(
        "list",
        help="List all schema versions"
    )
    
    args = parser.parse_args()
    
    if args.command == "load":
        schema_path = Path(args.schema_file)
        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            sys.exit(1)
        
        success = load_and_publish_schema(schema_path, args.user)
        sys.exit(0 if success else 1)
    
    elif args.command == "list":
        list_versions()
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

