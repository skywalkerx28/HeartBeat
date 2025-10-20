"""
HeartBeat Engine - Vector Store Backend Interface
Abstract interface for pluggable vector storage backends (Vertex AI)

Enables switching between vector databases via environment configuration
without changing application code.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VectorStoreBackend(ABC):
    """
    Abstract interface for vector storage backends.
    
    Implementations:
    - VertexBackend: Google Cloud Vertex AI Vector Search
    
    Design Pattern: Strategy Pattern
    Allows runtime selection of vector backend via environment variable.
    """
    
    @abstractmethod
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str
    ) -> Dict[str, Any]:
        """
        Store or update vectors with metadata.
        
        Args:
            vectors: List of vector records with:
                - id: Unique identifier
                - values: Dense vector embedding (List[float])
                - metadata: Associated metadata (Dict)
            namespace: Logical partition for vectors
            
        Returns:
            Operation result with count of upserted vectors
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        namespace: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity.
        
        Args:
            query_vector: Query embedding to search for
            namespace: Namespace to search within
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of matches with:
                - id: Vector ID
                - score: Similarity score (0-1)
                - metadata: Associated metadata
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        namespace: str
    ) -> Dict[str, Any]:
        """
        Delete vectors by ID.
        
        Args:
            ids: List of vector IDs to delete
            namespace: Namespace containing the vectors
            
        Returns:
            Operation result with count of deleted vectors
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get backend statistics and metadata.
        
        Returns:
            Dictionary with:
                - backend_type: Type of backend (vertex)
                - total_vectors: Total vector count
                - namespaces: List of available namespaces
                - dimension: Vector dimension
                - metric: Distance metric used
        """
        pass
    
    @abstractmethod
    def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """
        Get statistics for a specific namespace.
        
        Args:
            namespace: Namespace to get stats for
            
        Returns:
            Dictionary with namespace-specific statistics
        """
        pass
