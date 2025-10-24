"""
HeartBeat Engine - Parquet Resolver
NHL Advanced Analytics Platform

High-performance resolver for Parquet data files.
Optimized for analytics workloads with efficient filtering and column selection.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

try:
    import pandas as pd
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    logging.warning("PyArrow not available, ParquetResolver will fail at runtime")

from .base import BaseResolver, ResolverError, ResolverConfig

logger = logging.getLogger(__name__)


class ParquetResolver(BaseResolver):
    """
    Resolver for Parquet data files.
    
    Provides high-performance access to analytics data stored in Parquet format
    with optimized column selection and predicate pushdown.
    """
    
    def __init__(
        self,
        data_directory: Path,
        config: Optional[ResolverConfig] = None
    ):
        """
        Initialize Parquet resolver.
        
        Args:
            data_directory: Base directory containing Parquet files
            config: Resolver configuration
            
        Raises:
            ResolverError: If PyArrow not available
        """
        if not PARQUET_AVAILABLE:
            raise ResolverError("PyArrow/Pandas not installed. Install with: pip install pyarrow pandas")
        
        super().__init__(config)
        self.data_directory = Path(data_directory)
        
        if not self.data_directory.exists():
            logger.warning(f"Data directory does not exist: {self.data_directory}")
        
        logger.info(f"ParquetResolver initialized with directory: {self.data_directory}")
    
    def get_by_id(
        self,
        object_type: str,
        object_id: str,
        properties: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve single object by primary key from Parquet.
        
        Uses efficient filtering with predicate pushdown where possible.
        """
        try:
            # Determine file path and primary key column
            file_path, pk_column = self._get_file_path_and_pk(object_type)
            
            if not file_path.exists():
                logger.warning(f"Parquet file not found: {file_path}")
                return None
            
            # Read with column selection for efficiency
            columns = self._get_columns_to_read(properties, pk_column)
            
            # Read Parquet with filter
            df = pd.read_parquet(
                file_path,
                columns=columns,
                filters=[(pk_column, '==', object_id)]
            )
            
            if df.empty:
                return None
            
            # Return first row as dict
            return df.iloc[0].to_dict()
            
        except Exception as e:
            logger.error(f"Error reading Parquet for {object_type}/{object_id}: {e}")
            raise ResolverError(f"Failed to read from Parquet: {e}")
    
    def get_by_filter(
        self,
        object_type: str,
        filters: Dict[str, Any],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve objects matching filters from Parquet.
        
        Uses Pandas query for efficient filtering.
        """
        try:
            file_path, pk_column = self._get_file_path_and_pk(object_type)
            
            if not file_path.exists():
                logger.warning(f"Parquet file not found: {file_path}")
                return []
            
            # Read with column selection
            columns = self._get_columns_to_read(properties, pk_column)
            
            # Build PyArrow filter expression
            arrow_filters = self._build_arrow_filters(filters)
            
            # Read Parquet
            df = pd.read_parquet(
                file_path,
                columns=columns,
                filters=arrow_filters
            )
            
            # Apply additional filters if needed (for complex conditions)
            if filters:
                for field, value in filters.items():
                    if field in df.columns:
                        if isinstance(value, (list, tuple)):
                            df = df[df[field].isin(value)]
                        else:
                            df = df[df[field] == value]
            
            # Apply limit and offset
            final_limit, final_offset = self._apply_row_limit(limit, offset)
            
            if final_offset > 0:
                df = df.iloc[final_offset:]
            
            if final_limit:
                df = df.head(final_limit)
            
            # Convert to list of dicts
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error querying Parquet for {object_type}: {e}")
            raise ResolverError(f"Failed to query Parquet: {e}")
    
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
        Traverse link using foreign key or join table.
        
        Supports:
        - Foreign key links: Filter by foreign key value
        - Join table links: Not yet implemented for Parquet
        """
        resolver_type = link_config.get("type", "foreign_key")
        
        if resolver_type == "foreign_key":
            return self._traverse_foreign_key_link(
                from_object_id,
                to_object_type,
                link_config,
                properties,
                limit
            )
        elif resolver_type == "join_table":
            # Join tables not efficient in Parquet, should use BigQuery
            logger.warning(f"Join table link {link_type} not supported in Parquet, use BigQuery")
            return []
        else:
            raise ResolverError(f"Unknown link resolver type: {resolver_type}")
    
    def _traverse_foreign_key_link(
        self,
        from_object_id: str,
        to_object_type: str,
        link_config: Dict[str, Any],
        properties: Optional[List[str]],
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Traverse foreign key link"""
        to_field = link_config.get("to_field")
        
        if not to_field:
            raise ResolverError("Foreign key link missing 'to_field' in config")
        
        # Query target object type filtered by foreign key
        return self.get_by_filter(
            object_type=to_object_type,
            filters={to_field: from_object_id},
            properties=properties,
            limit=limit
        )
    
    def _get_file_path_and_pk(self, object_type: str) -> tuple[Path, str]:
        """
        Get Parquet file path and primary key column for object type.
        
        Conventions:
        - File: analytics/{object_type_snake_case}.parquet
        - PK: {object_type}Id (camelCase)
        """
        # Convert object type to snake_case for file name
        snake_case = self._to_snake_case(object_type)
        file_path = self.data_directory / "analytics" / f"{snake_case}.parquet"
        
        # Primary key is object type + "Id"
        pk_column = f"{object_type[0].lower()}{object_type[1:]}Id"
        
        return file_path, pk_column
    
    def _get_columns_to_read(
        self,
        properties: Optional[List[str]],
        pk_column: str
    ) -> Optional[List[str]]:
        """
        Get list of columns to read from Parquet.
        
        Always includes primary key column.
        Returns None to read all columns if properties not specified.
        """
        if not properties:
            return None
        
        columns = list(properties)
        if pk_column not in columns:
            columns.append(pk_column)
        
        return columns
    
    def _build_arrow_filters(
        self,
        filters: Dict[str, Any]
    ) -> Optional[List[tuple]]:
        """
        Build PyArrow filter expressions.
        
        Returns list of (column, operator, value) tuples.
        """
        if not filters:
            return None
        
        arrow_filters = []
        for field, value in filters.items():
            if not isinstance(value, (list, tuple)):
                arrow_filters.append((field, '==', value))
            # Lists handled separately in get_by_filter
        
        return arrow_filters if arrow_filters else None
    
    def _to_snake_case(self, text: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _get_backend_name(self) -> str:
        """Get backend name for metrics"""
        return "parquet"

