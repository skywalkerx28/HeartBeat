"""
HeartBeat Engine - OMS API Dependencies
NHL Advanced Analytics Platform

FastAPI dependency injection for OMS services.
Provides database sessions, resolvers, and service instances.
"""

from typing import Generator, Dict, Any
from fastapi import Depends, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from pathlib import Path
import logging
import os

from ..models.metadata import Base
from ..services.registry import SchemaRegistry
from ..services.policy_engine import PolicyEngine
from ..services.resolvers import ParquetResolver, BigQueryResolver, BaseResolver
from orchestrator.utils.state import UserContext
from backend.api.dependencies import get_current_user_context

logger = logging.getLogger(__name__)

# Database configuration - Production PostgreSQL only
# OMS shares the same Postgres instance as the bot/conversations store
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. OMS requires production PostgreSQL. "
        "Set DATABASE_URL environment variable to postgres connection string."
    )

# Create engine and session factory
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Resolver instances cache
_resolver_cache: Dict[str, BaseResolver] = {}
# Guard to avoid re-registering mappings repeatedly
_bq_mappings_loaded: bool = False


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Yields:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_schema_registry(db: Session = Depends(get_db)) -> SchemaRegistry:
    """
    Schema registry service dependency.
    
    Args:
        db: Database session
        
    Returns:
        SchemaRegistry instance
    """
    schema_dir = Path(__file__).parent.parent / "schemas" / "v0.1"
    return SchemaRegistry(db, schema_dir)


def get_policy_engine() -> PolicyEngine:
    """
    Policy enforcement engine dependency.
    
    Returns:
        PolicyEngine instance
    """
    return PolicyEngine()


def get_parquet_resolver() -> ParquetResolver:
    """
    Parquet data resolver dependency.
    
    Returns:
        ParquetResolver instance (cached)
    """
    if "parquet" not in _resolver_cache:
        data_dir = Path(os.getenv("DATA_DIRECTORY", "data/processed"))
        _resolver_cache["parquet"] = ParquetResolver(data_dir)
        logger.info("ParquetResolver initialized and cached")
    
    return _resolver_cache["parquet"]


def get_bigquery_resolver() -> BigQueryResolver:
    """
    BigQuery data resolver dependency.
    
    Returns:
        BigQueryResolver instance (cached)
    """
    global _bq_mappings_loaded
    if "bigquery" not in _resolver_cache:
        project_id = os.getenv("GCP_PROJECT", "heartbeat-474020")
        # Default to ontology dataset for semantic layer unless explicitly overridden
        dataset_id = os.getenv("BQ_DATASET_ONTOLOGY", os.getenv("BQ_DATASET_CORE", "ontology"))
        bq = BigQueryResolver(project_id, dataset_id)
        _resolver_cache["bigquery"] = bq
        logger.info("BigQueryResolver initialized and cached")
    
    # Lazily register per-object table mappings from active schema once
    if not _bq_mappings_loaded:
        try:
            db = SessionLocal()
            registry = SchemaRegistry(db, Path(__file__).parent.parent / "schemas" / "v0.1")
            object_types = registry.get_all_object_types()
            bq: BigQueryResolver = _resolver_cache["bigquery"]  # type: ignore
            count = 0
            for obj in object_types:
                rc = obj.resolver_config or {}
                table = rc.get("table") or rc.get("view")
                if table and obj.primary_key:
                    bq.register_object_mapping(obj.name, table, obj.primary_key)
                    count += 1
            _bq_mappings_loaded = True
            logger.info(f"Registered {count} BigQuery object mappings from OMS schema")
        except Exception as e:
            logger.warning(f"Could not register BigQuery mappings: {e}")
        finally:
            try:
                db.close()
            except Exception:
                pass
    
    return _resolver_cache["bigquery"]


def get_resolver(
    backend: str,
    parquet: ParquetResolver = Depends(get_parquet_resolver),
    bigquery: BigQueryResolver = Depends(get_bigquery_resolver)
) -> BaseResolver:
    """
    Get resolver for specified backend.
    
    Args:
        backend: Backend type (parquet or bigquery)
        parquet: Parquet resolver instance
        bigquery: BigQuery resolver instance
        
    Returns:
        Appropriate resolver instance
        
    Raises:
        HTTPException: If backend not supported
    """
    if backend == "parquet":
        return parquet
    elif backend == "bigquery":
        return bigquery
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported backend: {backend}"
        )


def init_database() -> None:
    """
    Initialize OMS database schema.
    
    Creates all tables if they don't exist.
    """
    logger.info("Initializing OMS database schema")
    Base.metadata.create_all(bind=engine)
    logger.info("OMS database schema initialized")


def clear_resolver_cache() -> None:
    """Clear resolver cache (for testing or manual refresh)"""
    global _resolver_cache
    count = len(_resolver_cache)
    _resolver_cache.clear()
    logger.info(f"Cleared resolver cache: {count} resolvers")

