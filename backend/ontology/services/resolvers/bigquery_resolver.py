"""
HeartBeat Engine - BigQuery Resolver
NHL Advanced Analytics Platform

Enterprise-grade resolver for Google Cloud BigQuery.
Optimized for relational data with efficient query generation and result caching.
"""

from typing import Dict, Any, List, Optional
import logging

try:
    from google.cloud import bigquery
    from google.api_core.exceptions import GoogleAPIError
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    logging.warning("Google Cloud BigQuery not available, BigQueryResolver will fail at runtime")

from .base import BaseResolver, ResolverError, ResolverConfig

logger = logging.getLogger(__name__)


class BigQueryResolver(BaseResolver):
    """
    Resolver for Google Cloud BigQuery.
    
    Provides enterprise-grade access to relational data with optimized
    query generation, parameterization, and result streaming.
    """
    
    def __init__(
        self,
        project_id: str,
        dataset_id: str,
        config: Optional[ResolverConfig] = None,
        client: Optional[Any] = None
    ):
        """
        Initialize BigQuery resolver.
        
        Args:
            project_id: GCP project ID
            dataset_id: BigQuery dataset ID
            config: Resolver configuration
            client: Optional BigQuery client (creates new if None)
            
        Raises:
            ResolverError: If BigQuery library not available
        """
        if not BIGQUERY_AVAILABLE:
            raise ResolverError(
                "Google Cloud BigQuery not installed. "
                "Install with: pip install google-cloud-bigquery"
            )
        
        super().__init__(config)
        
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = client or bigquery.Client(project=project_id)
        
        logger.info(
            f"BigQueryResolver initialized: {project_id}.{dataset_id}"
        )
    
    def get_by_id(
        self,
        object_type: str,
        object_id: str,
        properties: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve single object by primary key from BigQuery.
        
        Uses parameterized queries for security and performance.
        """
        try:
            table_name, pk_column = self._get_table_and_pk(object_type)
            columns = self._build_column_list(properties)
            
            # Build parameterized query
            query = f"""
                SELECT {columns}
                FROM `{self.project_id}.{self.dataset_id}.{table_name}`
                WHERE {pk_column} = @object_id
                LIMIT 1
            """
            
            # Execute with parameters
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("object_id", "STRING", object_id)
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Return first row or None
            for row in results:
                return dict(row)
            
            return None
            
        except GoogleAPIError as e:
            logger.error(f"BigQuery error for {object_type}/{object_id}: {e}")
            raise ResolverError(f"BigQuery query failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error querying BigQuery: {e}")
            raise ResolverError(f"Failed to query BigQuery: {e}")
    
    def get_by_filter(
        self,
        object_type: str,
        filters: Dict[str, Any],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve objects matching filters from BigQuery.
        
        Builds efficient WHERE clause with parameterized queries.
        """
        try:
            table_name, _ = self._get_table_and_pk(object_type)
            columns = self._build_column_list(properties)
            
            # Build WHERE clause and parameters
            where_clause, query_params = self._build_where_clause(filters)
            
            # Apply limits
            final_limit, final_offset = self._apply_row_limit(limit, offset)
            
            # Build query
            query = f"""
                SELECT {columns}
                FROM `{self.project_id}.{self.dataset_id}.{table_name}`
            """
            
            if where_clause:
                query += f"\nWHERE {where_clause}"
            
            if final_limit:
                query += f"\nLIMIT {final_limit}"
            
            if final_offset > 0:
                query += f"\nOFFSET {final_offset}"
            
            # Execute query
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Convert to list of dicts
            return [dict(row) for row in results]
            
        except GoogleAPIError as e:
            logger.error(f"BigQuery error for {object_type}: {e}")
            raise ResolverError(f"BigQuery query failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error querying BigQuery: {e}")
            raise ResolverError(f"Failed to query BigQuery: {e}")
    
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
        Traverse link using JOIN or foreign key.
        
        Supports:
        - Foreign key links: Simple WHERE filter
        - Join table links: Explicit JOIN query
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
            return self._traverse_join_table_link(
                from_object_id,
                to_object_type,
                link_config,
                properties,
                limit
            )
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
        
        return self.get_by_filter(
            object_type=to_object_type,
            filters={to_field: from_object_id},
            properties=properties,
            limit=limit
        )
    
    def _traverse_join_table_link(
        self,
        from_object_id: str,
        to_object_type: str,
        link_config: Dict[str, Any],
        properties: Optional[List[str]],
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Traverse many-to-many link via join table"""
        join_table = link_config.get("table")
        from_field = link_config.get("from_field")
        to_field = link_config.get("to_field")
        
        if not all([join_table, from_field, to_field]):
            raise ResolverError(
                "Join table link missing required config: table, from_field, to_field"
            )
        
        try:
            to_table_name, to_pk_column = self._get_table_and_pk(to_object_type)
            columns = self._build_column_list(properties, table_alias="t")
            
            final_limit, _ = self._apply_row_limit(limit, None)
            
            # Build JOIN query
            query = f"""
                SELECT {columns}
                FROM `{self.project_id}.{self.dataset_id}.{to_table_name}` t
                INNER JOIN `{self.project_id}.{self.dataset_id}.{join_table}` j
                    ON t.{to_pk_column} = j.{to_field}
                WHERE j.{from_field} = @from_id
            """
            
            if final_limit:
                query += f"\nLIMIT {final_limit}"
            
            # Execute query
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("from_id", "STRING", from_object_id)
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            return [dict(row) for row in results]
            
        except GoogleAPIError as e:
            logger.error(f"BigQuery JOIN error: {e}")
            raise ResolverError(f"BigQuery JOIN failed: {e}")
    
    def _get_table_and_pk(self, object_type: str) -> tuple[str, str]:
        """
        Get BigQuery table name and primary key column.
        
        Conventions:
        - Table: {object_type_snake_case} (e.g., players, prospects)
        - PK: {object_type}Id (e.g., playerId, prospectId)
        """
        # Convert to snake_case
        table_name = self._to_snake_case(object_type) + "s"
        
        # Primary key is object type + "Id"
        pk_column = f"{object_type[0].lower()}{object_type[1:]}Id"
        
        return table_name, pk_column
    
    def _build_column_list(
        self,
        properties: Optional[List[str]],
        table_alias: Optional[str] = None
    ) -> str:
        """Build comma-separated column list for SELECT"""
        if not properties:
            prefix = f"{table_alias}." if table_alias else ""
            return f"{prefix}*"
        
        if table_alias:
            return ", ".join([f"{table_alias}.{p}" for p in properties])
        
        return ", ".join(properties)
    
    def _build_where_clause(
        self,
        filters: Dict[str, Any]
    ) -> tuple[str, List]:
        """
        Build WHERE clause and query parameters.
        
        Returns:
            Tuple of (where_clause: str, parameters: List)
        """
        if not filters:
            return "", []
        
        conditions = []
        parameters = []
        
        for idx, (field, value) in enumerate(filters.items()):
            param_name = f"param_{idx}"
            
            if isinstance(value, (list, tuple)):
                # IN clause
                conditions.append(f"{field} IN UNNEST(@{param_name})")
                parameters.append(
                    bigquery.ArrayQueryParameter(param_name, "STRING", value)
                )
            else:
                # Equality
                conditions.append(f"{field} = @{param_name}")
                param_type = self._infer_param_type(value)
                parameters.append(
                    bigquery.ScalarQueryParameter(param_name, param_type, value)
                )
        
        where_clause = " AND ".join(conditions)
        return where_clause, parameters
    
    def _infer_param_type(self, value: Any) -> str:
        """Infer BigQuery parameter type from Python value"""
        if isinstance(value, bool):
            return "BOOL"
        elif isinstance(value, int):
            return "INT64"
        elif isinstance(value, float):
            return "FLOAT64"
        else:
            return "STRING"
    
    def _to_snake_case(self, text: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _get_backend_name(self) -> str:
        """Get backend name for metrics"""
        return "bigquery"

