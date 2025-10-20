"""
HeartBeat Engine - Vertex AI Vector Search: Index and Endpoint Setup

Creates (or reuses) a Vector Search Index and IndexEndpoint, and prints
the resource names to set in environment variables:
  VERTEX_INDEX_ENDPOINT, VERTEX_DEPLOYED_INDEX_ID

Usage:
  python scripts/vertex_index_setup.py \
      --project heartbeat-474020 \
      --location us-east1 \
      --display_name heartbeat-vs-index \
      --dimensions 768 \
      --metric cosine

Requires: google-cloud-aiplatform>=1.49.0 and authenticated gcloud ADC.
"""

from __future__ import annotations

import argparse
import logging
from google.cloud import aiplatform

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_or_get_index(project: str, location: str, display_name: str, dimensions: int, metric: str):
    aiplatform.init(project=project, location=location)
    # Try to find existing index by display name
    for idx in aiplatform.MatchingEngineIndex.list():
        if idx.display_name == display_name:
            logger.info(f"✓ Reusing index: {idx.resource_name}")
            return idx
    logger.info("Creating new Matching Engine index...")
    # Normalize metric name to expected enum string
    metric_norm = metric.upper()
    if metric_norm == 'COSINE':
        metric_norm = 'COSINE_DISTANCE'
    if metric_norm == 'DOT_PRODUCT':
        metric_norm = 'DOT_PRODUCT_DISTANCE'
    # Simpler: brute-force index (good for small/medium corpora and quick setup)
    idx = aiplatform.MatchingEngineIndex.create_brute_force_index(
        display_name=display_name,
        dimensions=dimensions,
        distance_measure_type=metric_norm,
    )
    logger.info(f"✓ Index created: {idx.resource_name}")
    return idx


def create_or_get_endpoint(project: str, location: str, display_name: str):
    aiplatform.init(project=project, location=location)
    for ep in aiplatform.MatchingEngineIndexEndpoint.list():
        if ep.display_name == display_name:
            logger.info(f"✓ Reusing endpoint: {ep.resource_name}")
            return ep
    logger.info("Creating new IndexEndpoint...")
    ep = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=display_name,
        public_endpoint_enabled=True,
    )
    logger.info(f"✓ Endpoint created: {ep.resource_name}")
    return ep


def deploy_index_to_endpoint(index: aiplatform.MatchingEngineIndex, endpoint: aiplatform.MatchingEngineIndexEndpoint):
    logger.info("Deploying index to endpoint (if not already deployed)...")
    # If index already deployed, reuse first deployment
    if endpoint.deployed_indexes:
        deployed = endpoint.deployed_indexes[0]
        logger.info(f"✓ Reusing deployed index: {deployed.id}")
        return deployed.id
    # Provide a generated deployed index id
    import uuid
    dep_id = f"vs_{uuid.uuid4().hex[:8]}"
    endpoint.deploy_index(index=index, deployed_index_id=dep_id)
    logger.info(f"✓ Deployed index id: {dep_id}")
    return dep_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--location', default='us-east1')
    parser.add_argument('--display_name', default='heartbeat-vs-index')
    parser.add_argument('--endpoint_name', default='heartbeat-vs-endpoint')
    parser.add_argument('--dimensions', type=int, default=768)
    parser.add_argument('--metric', default='COSINE')
    args = parser.parse_args()

    idx = create_or_get_index(args.project, args.location, args.display_name, args.dimensions, args.metric)
    ep = create_or_get_endpoint(args.project, args.location, args.endpoint_name)
    deployed_id = deploy_index_to_endpoint(idx, ep)

    print('\nEnvironment settings:')
    print(f"export VERTEX_PROJECT={args.project}")
    print(f"export VERTEX_LOCATION={args.location}")
    print(f"export VERTEX_INDEX_ENDPOINT={ep.resource_name}")
    print(f"export VERTEX_DEPLOYED_INDEX_ID={deployed_id}")
    print("export VECTOR_BACKEND=vertex")


if __name__ == '__main__':
    main()
