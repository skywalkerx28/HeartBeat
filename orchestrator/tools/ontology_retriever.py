"""
HeartBeat Engine - Ontology Retriever
Semantic search + relational expansion = LLM-ready context packs

Implements Palantir-style object retrieval:
1. Vector search returns object_refs (type, id)
2. Hydrate objects from BigQuery ontology views
3. Expand relationships (Player -> Contracts -> Games)
4. Return typed JSON context the LLM can reason over
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from google.cloud import bigquery
import logging
import os
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ObjectRef:
    """Reference to an object in the ontology."""
    object_type: str  # Player, Team, Game, etc.
    object_id: str  # Primary key value
    score: float = 0.0  # Relevance score from vector search
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OntologyObject:
    """Hydrated object from ontology views."""
    object_type: str
    object_id: str
    fields: Dict[str, Any]
    relationships: Dict[str, List[ObjectRef]]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "fields": self.fields,
            "relationships": {
                k: [r.to_dict() for r in v] 
                for k, v in self.relationships.items()
            },
            "metadata": self.metadata
        }


@dataclass
class ContextPack:
    """Complete context package for LLM consumption."""
    query: str
    primary_objects: List[OntologyObject]
    related_objects: List[OntologyObject]
    summary: str
    total_objects: int
    retrieval_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "primary_objects": [obj.to_dict() for obj in self.primary_objects],
            "related_objects": [obj.to_dict() for obj in self.related_objects],
            "summary": self.summary,
            "total_objects": self.total_objects,
            "retrieval_time_ms": self.retrieval_time_ms
        }


class OntologyRetriever:
    """
    Retrieve and hydrate objects from the ontology.
    
    Core workflow:
    1. retrieve_objects(query) -> semantic search
    2. hydrate_objects(refs) -> SQL fetch from object views
    3. expand_relationships(objects) -> follow foreign keys
    4. build_context_pack() -> assemble LLM-ready JSON
    """
    
    def __init__(
        self,
        project_id: str = "heartbeat-474020",
        dataset: str = "raw",
        vector_backend = None,
        schema_path: Optional[str] = None
    ):
        self.project_id = project_id
        self.dataset = dataset
        self.bq_client = bigquery.Client(project=project_id)
        self.vector_backend = vector_backend
        
        # Load ontology schema
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "ontology" / "schema.yaml"
        
        with open(schema_path, 'r') as f:
            self.schema = yaml.safe_load(f)['ontology']
        
        # Special-case view overrides where object_type -> view name isn't 1:1 lower() mapping
        self._view_overrides = {
            "GameMetrics": "objects_game_metrics",
            "TeamGameMetrics": "objects_team_game_metrics",
        }
        logger.info(f"OntologyRetriever initialized: {project_id}.{dataset}")
    
    async def retrieve_objects(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        expand_relationships: bool = True
    ) -> ContextPack:
        """
        Main entry point: semantic search + hydration + expansion.
        
        Args:
            query: Natural language query
            filters: Optional filters (e.g., {"object_type": "Player", "team": "MTL"})
            top_k: Number of primary objects to return
            expand_relationships: Whether to fetch related objects
        
        Returns:
            ContextPack ready for LLM consumption
        """
        import time
        start_time = time.time()
        
        # Step 1: Vector search (if backend available)
        object_refs = []
        if self.vector_backend:
            try:
                object_refs = await self._vector_search(query, filters, top_k)
                logger.info(f"Vector search returned {len(object_refs)} object refs")
            except Exception as e:
                logger.warning(f"Vector search failed, using SQL fallback: {e}")
                object_refs = await self._sql_search_fallback(query, filters, top_k)
        else:
            # Fallback to SQL search
            object_refs = await self._sql_search_fallback(query, filters, top_k)
        
        # Step 2: Hydrate primary objects
        primary_objects = await self.hydrate_objects(object_refs)
        
        # Step 3: Expand relationships
        related_objects = []
        if expand_relationships and primary_objects:
            related_objects = await self._expand_relationships(primary_objects)
        
        # Step 4: Build context pack
        elapsed_ms = (time.time() - start_time) * 1000
        summary = self._generate_summary(primary_objects, related_objects)
        
        context_pack = ContextPack(
            query=query,
            primary_objects=primary_objects,
            related_objects=related_objects,
            summary=summary,
            total_objects=len(primary_objects) + len(related_objects),
            retrieval_time_ms=round(elapsed_ms, 2)
        )
        
        logger.info(f"Context pack built: {context_pack.total_objects} objects in {elapsed_ms:.0f}ms")
        return context_pack
    
    async def _vector_search(
        self,
        query: str,
        filters: Optional[Dict],
        top_k: int
    ) -> List[ObjectRef]:
        """Perform vector search via backend (Pinecone/Vertex)."""
        
        if not self.vector_backend:
            return []
        
        # Default namespace for ontology objects
        namespace = filters.get("namespace", "ontology") if filters else "ontology"
        
        # Construct vector search filters
        vector_filters = {}
        if filters and "object_type" in filters:
            vector_filters["object_type"] = filters["object_type"]
        
        # Execute search
        results = await self.vector_backend.search(
            query_vector=None,  # TODO: Embed query text
            namespace=namespace,
            top_k=top_k,
            filters=vector_filters
        )
        
        # Convert to ObjectRefs
        object_refs = []
        for result in results:
            metadata = result.get("metadata", {})
            object_refs.append(ObjectRef(
                object_type=metadata.get("object_type", "Unknown"),
                object_id=metadata.get("object_id", ""),
                score=result.get("score", 0.0)
            ))
        
        return object_refs
    
    async def _sql_search_fallback(
        self,
        query: str,
        filters: Optional[Dict],
        top_k: int
    ) -> List[ObjectRef]:
        """
        Fallback: SQL-based search when vector backend unavailable.
        Uses LIKE matching on player/team names.
        """
        
        query_lower = query.lower()
        object_refs = []
        
        # Try to match players
        if not filters or filters.get("object_type") in [None, "Player"]:
            player_query = f"""
            SELECT 
                'Player' AS object_type,
                CAST(nhl_player_id AS STRING) AS object_id,
                full_name,
                1.0 AS score
            FROM `{self.project_id}.{self.dataset}.objects_player`
            WHERE LOWER(full_name) LIKE @query
            LIMIT {top_k}
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query", "STRING", f"%{query_lower}%")
                ]
            )
            
            try:
                df = self.bq_client.query(player_query, job_config=job_config).to_dataframe()
                for _, row in df.iterrows():
                    object_refs.append(ObjectRef(
                        object_type=row['object_type'],
                        object_id=str(row['object_id']),
                        score=float(row['score'])
                    ))
            except Exception as e:
                logger.error(f"Player search failed: {e}")
        
        # Try to match teams
        if not filters or filters.get("object_type") in [None, "Team"]:
            team_query = f"""
            SELECT 
                'Team' AS object_type,
                team_abbrev AS object_id,
                team_name,
                1.0 AS score
            FROM `{self.project_id}.{self.dataset}.objects_team`
            WHERE LOWER(team_name) LIKE @query 
               OR LOWER(team_abbrev) LIKE @query
            LIMIT {top_k}
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query", "STRING", f"%{query_lower}%")
                ]
            )
            
            try:
                df = self.bq_client.query(team_query, job_config=job_config).to_dataframe()
                for _, row in df.iterrows():
                    object_refs.append(ObjectRef(
                        object_type=row['object_type'],
                        object_id=str(row['object_id']),
                        score=float(row['score'])
                    ))
            except Exception as e:
                logger.error(f"Team search failed: {e}")
        
        return object_refs[:top_k]
    
    async def hydrate_objects(
        self,
        object_refs: List[ObjectRef]
    ) -> List[OntologyObject]:
        """Fetch full object data from BigQuery object views."""
        
        if not object_refs:
            return []
        
        hydrated = []
        
        for ref in object_refs:
            try:
                obj = await self._hydrate_single_object(ref)
                if obj:
                    hydrated.append(obj)
            except Exception as e:
                logger.warning(f"Failed to hydrate {ref.object_type}:{ref.object_id}: {e}")
        
        return hydrated
    
    async def _hydrate_single_object(
        self,
        ref: ObjectRef
    ) -> Optional[OntologyObject]:
        """Hydrate a single object from its view."""
        
        # Map object type to view name
        view_name = self._view_overrides.get(ref.object_type) or f"objects_{ref.object_type.lower()}"
        
        # Get primary key field from schema
        obj_schema = self.schema['objects'].get(ref.object_type, {})
        identity = obj_schema.get('identity', {})
        pk_field = identity.get('primary_key', 'id')
        
        # Handle composite keys
        if isinstance(pk_field, list):
            # For now, skip composite key objects in hydration
            logger.warning(f"Composite key objects not yet supported: {ref.object_type}")
            return None
        
        # Query the object view
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset}.{view_name}`
        WHERE CAST({pk_field} AS STRING) = @object_id
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("object_id", "STRING", ref.object_id)
            ]
        )
        
        try:
            df = self.bq_client.query(query, job_config=job_config).to_dataframe()
            
            if df.empty:
                logger.warning(f"Object not found: {ref.object_type}:{ref.object_id}")
                return None
            
            # Convert row to dict
            row_dict = df.iloc[0].to_dict()
            
            # Separate metadata fields
            metadata_fields = ['last_updated', 'data_source', 'profile_uri', 'source_uri', 
                             'extraction_time', 'model_version', 'feature_set_ref']
            
            metadata = {
                k: str(v) if v is not None else None 
                for k, v in row_dict.items() 
                if k in metadata_fields
            }
            
            # Core fields (excluding metadata and relationship keys)
            fields = {
                k: str(v) if v is not None else None
                for k, v in row_dict.items()
                if k not in metadata_fields and not k.startswith('rel_')
            }
            
            return OntologyObject(
                object_type=ref.object_type,
                object_id=ref.object_id,
                fields=fields,
                relationships={},  # Filled by expand_relationships
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Hydration query failed for {ref.object_type}: {e}")
            return None
    
    async def _expand_relationships(
        self,
        objects: List[OntologyObject],
        max_related: int = 3
    ) -> List[OntologyObject]:
        """
        Expand relationships for objects (fetch related entities).
        
        For example: Player -> Contracts, Player -> Recent Games
        """
        
        related_objects = []
        
        for obj in objects:
            obj_schema = self.schema['objects'].get(obj.object_type, {})
            relationships = obj_schema.get('relationships', [])
            
            for rel in relationships:
                try:
                    # Fetch related objects
                    related = await self._fetch_related_objects(
                        obj, rel, max_related
                    )
                    
                    if related:
                        # Add refs to parent object
                        rel_refs = [
                            ObjectRef(r.object_type, r.object_id, 1.0) 
                            for r in related
                        ]
                        obj.relationships[rel['type']] = rel_refs
                        
                        # Add to related objects list
                        related_objects.extend(related)
                
                except Exception as e:
                    logger.warning(f"Failed to expand {rel['type']}: {e}")
        
        return related_objects
    
    async def _fetch_related_objects(
        self,
        obj: OntologyObject,
        relationship: Dict,
        limit: int
    ) -> List[OntologyObject]:
        """Fetch related objects via foreign key join."""
        
        # Support one_to_many, many_to_one, and one_to_one expansions (limit controls size)
        card = (relationship.get('cardinality') or '').lower()
        if card not in ("one_to_many", "many_to_one", "one_to_one"):
            return []
        
        target_type = relationship['target']
        join_key = relationship['join_key']
        
        # Parse join key (e.g., "nhl_player_id -> player_id")
        parts = join_key.split('->')
        if len(parts) != 2:
            return []
        
        source_field = parts[0].strip()
        target_field = parts[1].strip()
        
        # Get source value
        source_value = obj.fields.get(source_field)
        if not source_value:
            return []
        
        # Query related objects
        view_name = self._view_overrides.get(target_type) or f"objects_{target_type.lower()}"
        
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset}.{view_name}`
        WHERE CAST({target_field} AS STRING) = @source_value
        LIMIT {limit}
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("source_value", "STRING", str(source_value))
            ]
        )
        
        try:
            df = self.bq_client.query(query, job_config=job_config).to_dataframe()
            
            related = []
            for _, row in df.iterrows():
                # Get primary key
                target_schema = self.schema['objects'].get(target_type, {})
                pk_field = target_schema.get('identity', {}).get('primary_key', 'id')
                
                if isinstance(pk_field, list):
                    continue  # Skip composite keys
                
                object_id = str(row.get(pk_field, ''))
                
                # Create OntologyObject
                row_dict = row.to_dict()
                metadata_fields = ['last_updated', 'data_source', 'profile_uri', 'source_uri']
                
                related.append(OntologyObject(
                    object_type=target_type,
                    object_id=object_id,
                    fields={k: str(v) if v is not None else None for k, v in row_dict.items() if k not in metadata_fields},
                    relationships={},
                    metadata={k: str(v) if v is not None else None for k, v in row_dict.items() if k in metadata_fields}
                ))
            
            return related
            
        except Exception as e:
            logger.error(f"Failed to fetch {target_type}: {e}")
            return []
    
    def _generate_summary(
        self,
        primary: List[OntologyObject],
        related: List[OntologyObject]
    ) -> str:
        """Generate human-readable summary of retrieved objects."""
        
        if not primary:
            return "No objects found."
        
        # Count by type
        primary_types = {}
        for obj in primary:
            primary_types[obj.object_type] = primary_types.get(obj.object_type, 0) + 1
        
        related_types = {}
        for obj in related:
            related_types[obj.object_type] = related_types.get(obj.object_type, 0) + 1
        
        # Build summary
        parts = ["Retrieved:"]
        for obj_type, count in primary_types.items():
            parts.append(f"{count} {obj_type}(s)")
        
        if related_types:
            parts.append("with related:")
            for obj_type, count in related_types.items():
                parts.append(f"{count} {obj_type}(s)")
        
        return " ".join(parts)


# Convenience function for quick retrieval
async def retrieve_hockey_context(
    query: str,
    filters: Optional[Dict] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Quick helper to retrieve hockey context.
    
    Usage:
        context = await retrieve_hockey_context("Cole Caufield stats")
        # Returns typed object dict ready for LLM
    """
    
    retriever = OntologyRetriever()
    context_pack = await retriever.retrieve_objects(query, filters, top_k)
    return context_pack.to_dict()
