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

# Database configuration
DATABASE_URL = os.getenv("OMS_DATABASE_URL", "sqlite:///./oms_metadata.db")

# Create engine and session factory
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Resolver instances cache
_resolver_cache: Dict[str, BaseResolver] = {}


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
    if "bigquery" not in _resolver_cache:
        project_id = os.getenv("GCP_PROJECT", "heartbeat-474020")
        dataset_id = os.getenv("BQ_DATASET_CORE", "core")
        _resolver_cache["bigquery"] = BigQueryResolver(project_id, dataset_id)
        logger.info("BigQueryResolver initialized and cached")
    
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

