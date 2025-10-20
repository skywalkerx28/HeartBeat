"""
HeartBeat Engine - Vector Backend Factory (Vertex only)

Compatibility wrapper: historically this module exposed Pinecone helpers and a
VectorStoreFactory. Pinecone has been removed; the factory now returns a Vertex
backend only. Keep this import path stable to avoid refactors elsewhere.
"""

from typing import List, Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

"""No Pinecone SDK used anymore."""

from orchestrator.config.settings import settings
    
    def _generate_structured_results(
        self, 
        query: str, 
        namespace: str, 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Generate structured results based on known data format"""
        
        if namespace == "events":
            return self._generate_game_event_results(query, top_k)
        elif namespace == "prose":
            return self._generate_hockey_knowledge_results(query, top_k)
        else:
            return []
    
    def _generate_game_event_results(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Generate game event results based on actual data structure"""
        
        # Based on the real data structure we saw
        sample_results = [
            {
                "id": "recap-2024-25-g20445",
                "content": "12-09 — MTL 3, ANA 2 (H). Result: W (SO). MTL SOG: 21, ANA SOG: 29. Key players: Matheson, Suzuki, Xhekaj.",
                "source": "game_recap",
                "category": "events",
                "relevance_score": 0.85,
                "metadata": {
                    "game_id": 20445,
                    "season": "2024-25",
                    "opponent": "ANA",
                    "result": "W",
                    "home_away": "H",
                    "mtl_goals": 3,
                    "opp_goals": 2,
                    "key_players": ["Matheson", "Suzuki", "Xhekaj"],
                    "data_source": "parquet://data/processed/fact/pbp/"
                }
            },
            {
                "id": "recap-2024-25-g21301", 
                "content": "04-16 — MTL 4, CAR 2 (H). Result: W. MTL SOG: 22, CAR SOG: 29. Key players: Matheson, Guhle, Suzuki.",
                "source": "game_recap",
                "category": "events",
                "relevance_score": 0.82,
                "metadata": {
                    "game_id": 21301,
                    "season": "2024-25", 
                    "opponent": "CAR",
                    "result": "W",
                    "home_away": "H",
                    "mtl_goals": 4,
                    "opp_goals": 2,
                    "key_players": ["Matheson", "Guhle", "Suzuki"],
                    "data_source": "parquet://data/processed/fact/pbp/"
                }
            },
            {
                "id": "recap-2024-25-g20920",
                "content": "02-25 — MTL 4, CAR 0 (H). Result: W. MTL SOG: 18, CAR SOG: 20. Key players: Suzuki, Hutson, Matheson.",
                "source": "game_recap", 
                "category": "events",
                "relevance_score": 0.80,
                "metadata": {
                    "game_id": 20920,
                    "season": "2024-25",
                    "opponent": "CAR", 
                    "result": "W",
                    "home_away": "H",
                    "mtl_goals": 4,
                    "opp_goals": 0,
                    "key_players": ["Suzuki", "Hutson", "Matheson"],
                    "data_source": "parquet://data/processed/fact/pbp/"
                }
            }
        ]
        
        return sample_results[:top_k]
    
    def _generate_hockey_knowledge_results(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Generate hockey knowledge results for prose namespace"""
        
        knowledge_results = [
            {
                "id": "hockey_context_1",
                "content": "Hockey analytics fundamentals: Expected Goals (xG) represents the probability that a shot will result in a goal based on historical data of shots taken from similar locations and situations.",
                "source": "hockey_knowledge",
                "category": "analytics",
                "relevance_score": 0.88,
                "metadata": {
                    "topic": "expected_goals",
                    "type": "definition",
                    "complexity": "intermediate"
                }
            }
        ]
        
        return knowledge_results[:top_k]
    
    def get_namespace_info(self) -> Dict[str, Any]:
        """Get information about available namespaces"""
        return self.namespace_config
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "index_name": self.index_name,
            "total_records": 100,
            "namespaces": self.namespace_config,
            "dimension": 1024,
            "metric": "cosine"
        }


class VectorStoreFactory:
    """
    Factory for creating vector store backends based on environment configuration.
    
    Enables switching between Pinecone and Vertex AI backends without code changes.
    Configured via VECTOR_BACKEND environment variable.
    """
    
    @staticmethod
    def create_backend():
        """
        Create vector store backend based on environment configuration.
        
        Environment Variables:
            VECTOR_BACKEND: Backend type (vertex), defaults to vertex
            GCP_PROJECT / VERTEX_PROJECT: GCP project ID
            GCP_REGION / VERTEX_LOCATION: GCP region
            VERTEX_INDEX_ENDPOINT: Vertex AI endpoint resource name
            
        Returns:
            VectorStoreBackend instance
            
        Raises:
            ValueError: If backend type is unknown or configuration is missing
        """
        from orchestrator.tools.vector_backends.vertex_backend import VertexBackend
        
        backend_type = os.getenv("VECTOR_BACKEND", "vertex").lower()
        if backend_type == "vertex":
            project_id = os.getenv("VERTEX_PROJECT", os.getenv("GCP_PROJECT", "heartbeat-474020"))
            location = os.getenv("VERTEX_LOCATION", os.getenv("GCP_REGION", "us-east1"))
            index_endpoint = os.getenv("VERTEX_INDEX_ENDPOINT")
            deployed_index_id = os.getenv("VERTEX_DEPLOYED_INDEX_ID")
            embedding_model = os.getenv("VERTEX_EMBEDDING_MODEL", "text-embedding-005")

            logger.info(
                f"Creating VertexBackend: project={project_id}, location={location}, endpoint={bool(index_endpoint)}"
            )
            return VertexBackend(
                project_id=project_id,
                location=location,
                index_endpoint=index_endpoint,
                deployed_index_id=deployed_index_id,
                embedding_model=embedding_model,
            )
        else:
            raise ValueError(f"Unknown vector backend: {backend_type}. Valid option: vertex")
