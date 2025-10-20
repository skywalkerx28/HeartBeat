"""
HeartBeat Engine - Upsert CBA Chunks to Vertex AI Vector Search

Reads chunk Parquet from GCS, generates embeddings (Vertex text-embedding-005
by default), and upserts datapoints to a deployed Vertex index endpoint.

Usage:
  python scripts/gcp/vertex_upsert_from_gcs.py \
      --project heartbeat-474020 \
      --location us-east1 \
      --endpoint $VERTEX_INDEX_ENDPOINT \
      --deployed_index_id $VERTEX_DEPLOYED_INDEX_ID \
      --gcs_uri gs://heartbeat-474020-lake/silver/reference/cba/cba_chunks.parquet \
      --namespace cba:chunks
"""

from __future__ import annotations

import argparse
import tempfile
from typing import List, Dict
import logging

import pandas as pd
from google.cloud import storage, aiplatform
from google.cloud.aiplatform_v1.types import IndexDatapoint
from vertexai.language_models import TextEmbeddingModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def download_to_tmp(gcs_uri: str) -> str:
    assert gcs_uri.startswith('gs://')
    _, rest = gcs_uri.split('gs://', 1)
    bucket_name, blob_name = rest.split('/', 1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    fd, tmp_path = tempfile.mkstemp(suffix='.parquet')
    blob.download_to_filename(tmp_path)
    return tmp_path


def embed_texts(texts: List[str], model_name: str) -> List[List[float]]:
    model = TextEmbeddingModel.from_pretrained(model_name)
    # Batch for throughput
    out: List[List[float]] = []
    batch = 64
    for i in range(0, len(texts), batch):
        chunk = texts[i:i+batch]
        vecs = model.get_embeddings(chunk)
        out.extend([v.values for v in vecs])
    return out


def upsert(df: pd.DataFrame, project: str, location: str, endpoint: str, deployed_index_id: str, namespace: str, model: str) -> int:
    aiplatform.init(project=project, location=location)
    ep = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint)
    texts = df['text'].astype(str).tolist()
    vectors = embed_texts(texts, model)
    datapoints = []
    for (idx, row), vec in zip(df.iterrows(), vectors):
        meta = {
            'namespace': namespace,
            'object_type': 'DocumentChunk',
            'document_id': str(row.get('document_id', '')),
            'section': str(row.get('section', '')),
            'page_start': str(row.get('page_start', '')),
            'page_end': str(row.get('page_end', '')),
        }
        restr = [IndexDatapoint.Restriction(namespace=k, allow_list=[str(v)]) for k, v in meta.items() if v]
        dp = IndexDatapoint(datapoint_id=str(row.get('chunk_id', idx)), feature_vector=vec, restricts=restr)
        datapoints.append(dp)
    op = ep.upsert_datapoints(datapoints=datapoints, deployed_index_id=deployed_index_id)
    op.result()
    return len(datapoints)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project', required=True)
    p.add_argument('--location', default='us-east1')
    p.add_argument('--endpoint', required=True)
    p.add_argument('--deployed_index_id', required=True)
    p.add_argument('--gcs_uri', required=True)
    p.add_argument('--namespace', default='cba:chunks')
    p.add_argument('--embedding_model', default='text-embedding-005')
    args = p.parse_args()

    tmp = download_to_tmp(args.gcs_uri)
    logger.info(f"Downloaded Parquet to {tmp}")
    df = pd.read_parquet(tmp)
    # Ensure required columns
    if 'text' not in df.columns:
        raise RuntimeError("Parquet missing 'text' column")

    count = upsert(df, args.project, args.location, args.endpoint, args.deployed_index_id, args.namespace, args.embedding_model)
    logger.info(f"✓ Upserted {count} chunks to Vertex index")


if __name__ == '__main__':
    main()

