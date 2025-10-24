"""
HeartBeat Engine - Base Resolver
NHL Advanced Analytics Platform

Abstract base resolver interface for ontology data access.
Provides caching, error handling, and performance monitoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ResolverError(Exception):
    """Base exception for resolver errors"""
    pass


@dataclass
class ResolverConfig:
    """Configuration for resolver behavior"""
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Performance limits
    max_rows: int = 10000
    max_batch_size: int = 1000


@dataclass
class ResolverMetrics:
    """Performance metrics for resolver operations"""
    query_time_ms: int
    rows_returned: int
    cache_hit: bool
    backend: str
    timestamp: datetime


class BaseResolver(ABC, Generic[T]):
    """
    Abstract base resolver for ontology data access.
    
    Provides standard interface for all data backend resolvers with
    built-in caching, error handling, and performance monitoring.
    """
    
    def __init__(self, config: Optional[ResolverConfig] = None):
        """
        Initialize resolver with configuration.
        
        Args:
            config: Resolver configuration (uses defaults if not provided)
        """
        self.config = config or ResolverConfig()
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._metrics: List[ResolverMetrics] = []
        
        logger.info(f"{self.__class__.__name__} initialized with cache_ttl={self.config.cache_ttl_seconds}s")
    
    @abstractmethod
    def get_by_id(
        self,
        object_type: str,
        object_id: str,
        properties: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve single object by primary key.
        
        Args:
            object_type: Object type name
            object_id: Primary key value
            properties: Optional list of properties to retrieve (all if None)
            
        Returns:
            Object data dictionary or None if not found
            
        Raises:
            ResolverError: If query fails
        """
        pass
    
    @abstractmethod
    def get_by_filter(
        self,
        object_type: str,
        filters: Dict[str, Any],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve objects matching filters.
        
        Args:
            object_type: Object type name
            filters: Filter conditions (field: value pairs)
            properties: Optional list of properties to retrieve
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching objects
            
        Raises:
            ResolverError: If query fails
        """
        pass
    
    @abstractmethod
    def traverse_link(
        self,
        from_object_type: str,
        from_object_id: str,
        link_type: str,
        to_object_type: str,
        link_config: Dict[str, Any],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Traverse link from source object to related objects.
        
        Args:
            from_object_type: Source object type
            from_object_id: Source object ID
            link_type: Link type name
            to_object_type: Target object type
            link_config: Link resolver configuration
            properties: Optional list of properties to retrieve
            limit: Maximum number of results
            
        Returns:
            List of related objects
            
        Raises:
            ResolverError: If traversal fails
        """
        pass
    
    def get_by_id_cached(
        self,
        object_type: str,
        object_id: str,
        properties: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get object by ID with caching"""
        if not self.config.cache_enabled:
            return self.get_by_id(object_type, object_id, properties)
        
        cache_key = self._generate_cache_key(object_type, object_id, properties)
        
        # Check cache
        if cache_key in self._cache:
            data, cached_at = self._cache[cache_key]
            ttl = timedelta(seconds=self.config.cache_ttl_seconds)
            
            if datetime.utcnow() - cached_at < ttl:
                logger.debug(f"Cache hit: {cache_key}")
                return data
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
        
        # Cache miss, fetch from backend
        start_time = time.perf_counter()
        data = self.get_by_id(object_type, object_id, properties)
        query_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Cache result
        if data:
            self._cache[cache_key] = (data, datetime.utcnow())
        
        # Record metrics
        self._record_metric(
            query_time_ms=query_time_ms,
            rows_returned=1 if data else 0,
            cache_hit=False,
            backend=self._get_backend_name()
        )
        
        return data
    
    def clear_cache(self, object_type: Optional[str] = None) -> None:
        """
        Clear resolver cache.
        
        Args:
            object_type: Clear only entries for this object type (all if None)
        """
        if object_type:
            # Clear specific object type
            keys_to_delete = [
                k for k in self._cache.keys()
                if k.startswith(f"{object_type}:")
            ]
            for key in keys_to_delete:
                del self._cache[key]
            logger.info(f"Cleared cache for {object_type}: {len(keys_to_delete)} entries")
        else:
            # Clear all
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared all cache: {count} entries")
    
    def get_metrics(self) -> List[ResolverMetrics]:
        """Get resolver performance metrics"""
        return self._metrics.copy()
    
    def clear_metrics(self) -> None:
        """Clear performance metrics"""
        self._metrics.clear()
    
    def _generate_cache_key(
        self,
        object_type: str,
        object_id: str,
        properties: Optional[List[str]] = None
    ) -> str:
        """Generate cache key for object"""
        props_key = ",".join(sorted(properties)) if properties else "all"
        return f"{object_type}:{object_id}:{props_key}"
    
    def _record_metric(
        self,
        query_time_ms: int,
        rows_returned: int,
        cache_hit: bool,
        backend: str
    ) -> None:
        """Record performance metric"""
        metric = ResolverMetrics(
            query_time_ms=query_time_ms,
            rows_returned=rows_returned,
            cache_hit=cache_hit,
            backend=backend,
            timestamp=datetime.utcnow()
        )
        self._metrics.append(metric)
        
        # Keep only last 1000 metrics
        if len(self._metrics) > 1000:
            self._metrics = self._metrics[-1000:]
    
    def _apply_row_limit(
        self,
        limit: Optional[int],
        offset: Optional[int] = None
    ) -> tuple[int, int]:
        """
        Apply and validate row limits.
        
        Returns:
            Tuple of (limit, offset) with max limits applied
        """
        # Apply max row limit
        final_limit = min(
            limit or self.config.max_rows,
            self.config.max_rows
        )
        
        final_offset = offset or 0
        
        return final_limit, final_offset
    
    @abstractmethod
    def _get_backend_name(self) -> str:
        """Get backend name for metrics"""
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(cache_enabled={self.config.cache_enabled})>"

