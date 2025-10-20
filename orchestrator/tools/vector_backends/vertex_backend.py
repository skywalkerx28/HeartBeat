"""
HeartBeat Engine - Vertex AI Vector Store Backend

Production-ready backend for Google Cloud Vertex AI Vector Search
(Matching Engine). Provides upsert/search/delete operations behind the
VectorStoreBackend interface.
"""

from typing import List, Dict, Any, Optional
import logging

from orchestrator.tools.vector_store_backend import VectorStoreBackend

logger = logging.getLogger(__name__)

_AIP_AVAILABLE = True
try:
    from google.cloud import aiplatform
    from google.cloud.aiplatform_v1.types import IndexDatapoint
except Exception:
    _AIP_AVAILABLE = False
    logger.warning("google-cloud-aiplatform not available; Vertex backend will be inactive")


class VertexBackend(VectorStoreBackend):
    def __init__(
        self,
        project_id: str,
        location: str = "us-east1",
        index_endpoint: Optional[str] = None,
        deployed_index_id: Optional[str] = None,
        embedding_model: str = "text-embedding-005",
    ):
        self.project_id = project_id
        self.location = location
        self.index_endpoint = index_endpoint
        self.deployed_index_id = deployed_index_id
        self.embedding_model = embedding_model

        if _AIP_AVAILABLE:
            aiplatform.init(project=project_id, location=location)
            logger.info(
                f"VertexBackend ready: project={project_id}, location={location}, endpoint={index_endpoint}, deployed={deployed_index_id}"
            )
        else:
            logger.error("Vertex backend inactive: google-cloud-aiplatform not installed")

    def _endpoint(self):
        if not _AIP_AVAILABLE:
            raise RuntimeError("Vertex AI SDK not available")
        if not self.index_endpoint:
            raise RuntimeError("VERTEX_INDEX_ENDPOINT not configured")
        return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=self.index_endpoint)

    def _datapoint(self, vec: Dict[str, Any], namespace: str) -> IndexDatapoint:
        feature_vector = vec.get("values") or vec.get("vector")
        if feature_vector is None:
            text = vec.get("text") or (vec.get("metadata") or {}).get("text")
            if text is None:
                raise ValueError("Vector item missing 'values' and 'text' for embedding")
            # Embed on the fly using Vertex embeddings
            try:
                from vertexai.preview.generative_models import GenerativeModel  # ensure vertexai installed
            except Exception:
                pass
            try:
                from vertexai.language_models import TextEmbeddingModel
                em = TextEmbeddingModel.from_pretrained(self.embedding_model)
                feature_vector = em.get_embeddings([text])[0].values
            except Exception as e:
                raise RuntimeError(f"Failed to embed text with {self.embedding_model}: {e}")
        meta = vec.get("metadata", {})
        restricts = []
        # Map key metadata into restricts for filtering
        for k in ["namespace", "object_type", "document_id", "rule_id", "article_number"]:
            v = meta.get(k) or (namespace if k == "namespace" else None)
            if v:
                restricts.append(IndexDatapoint.Restriction(namespace=k, allow_list=[str(v)]))
        return IndexDatapoint(datapoint_id=str(vec.get("id")), feature_vector=feature_vector, restricts=restricts)

    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str
    ) -> Dict[str, Any]:
        ep = self._endpoint()
        if not self.deployed_index_id:
            raise RuntimeError("VERTEX_DEPLOYED_INDEX_ID not configured")
        datapoints = [self._datapoint(v, namespace) for v in vectors]
        op = ep.upsert_datapoints(datapoints=datapoints, deployed_index_id=self.deployed_index_id)
        op.result()  # wait
        return {"success": True, "upserted": len(datapoints)}

    async def search(
        self,
        query_vector: List[float],
        namespace: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        ep = self._endpoint()
        if not self.deployed_index_id:
            raise RuntimeError("VERTEX_DEPLOYED_INDEX_ID not configured")
        restricts = []
        if filters:
            for k, v in filters.items():
                restricts.append(IndexDatapoint.Restriction(namespace=k, allow_list=[str(v)]))
        # Always include namespace
        restricts.append(IndexDatapoint.Restriction(namespace="namespace", allow_list=[namespace]))
        queries = [IndexDatapoint(datapoint_id="q", feature_vector=query_vector, restricts=restricts)]
        res = ep.find_neighbors(deployed_index_id=self.deployed_index_id, queries=queries, neighbor_count=top_k)
        out = []
        for nn in res.nearest_neighbors[0].neighbors:
            out.append({
                "id": nn.datapoint.datapoint_id,
                "score": nn.distance,  # Vertex returns distance; convert to similarity if needed
                "metadata": {"namespace": namespace}
            })
        return out

    async def delete(
        self,
        ids: List[str],
        namespace: str
    ) -> Dict[str, Any]:
        ep = self._endpoint()
        if not self.deployed_index_id:
            raise RuntimeError("VERTEX_DEPLOYED_INDEX_ID not configured")
        op = ep.remove_datapoints(datapoint_ids=ids, deployed_index_id=self.deployed_index_id)
        op.result()
        return {"success": True, "deleted": len(ids)}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "backend_type": "vertex",
            "project_id": self.project_id,
            "location": self.location,
            "endpoint": self.index_endpoint,
            "deployed_index_id": self.deployed_index_id,
            "available": _AIP_AVAILABLE,
        }

    def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        return {"namespace": namespace, "available": _AIP_AVAILABLE}
