"""
HeartBeat Engine - Vector Dimension Audit (Phase 0)

Prints embedding dimensions for current/target models and any configured
index dimensions for Pinecone and Vertex.

Usage:
  python scripts/ops/vector_dimension_audit.py
"""

import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def vertex_dim(model: str) -> int:
    try:
        from vertexai.language_models import TextEmbeddingModel
        m = TextEmbeddingModel.from_pretrained(model)
        # Vertex doesn't expose dimension directly; embed a token to infer length
        vec = m.get_embeddings(["test"])[0].values
        return len(vec)
    except Exception as e:
        logger.warning(f"Vertex embedding check failed: {e}")
        return -1


def pinecone_dim() -> int:
    return -1


def main():
    target_model = os.getenv('VERTEX_EMBEDDING_MODEL', 'text-embedding-005')
    vd = vertex_dim(target_model)
    pd = -1
    print("Vector Dimension Audit:")
    print(f"  Vertex model '{target_model}' dimension: {vd if vd>0 else 'unknown'}")
    # Pinecone deprecated
    if vd>0 and pd>0 and vd != pd:
        print("\n⚠ Dimension mismatch: re-embedding required to migrate.")
    else:
        print("\n✓ Dimensions aligned or unknown (proceed with caution).")


if __name__ == '__main__':
    main()
