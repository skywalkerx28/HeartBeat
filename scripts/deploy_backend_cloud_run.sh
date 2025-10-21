#!/usr/bin/env bash
set -euo pipefail

# Deploy HeartBeat FastAPI backend to Cloud Run

SERVICE_NAME=${SERVICE_NAME:-heartbeat-backend}
REGION=${REGION:-us-east1}
PROJECT_ID=${PROJECT_ID:-${GCP_PROJECT:-heartbeat-474020}}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/heartbeat/${SERVICE_NAME}:$(date +%Y%m%d-%H%M%S)"

echo "Project:   ${PROJECT_ID}"
echo "Region:    ${REGION}"
echo "Service:   ${SERVICE_NAME}"
echo "Image:     ${IMAGE}"

echo "Ensuring Artifact Registry exists..."
gcloud artifacts repositories describe heartbeat \
  --location="${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1 || \
gcloud artifacts repositories create heartbeat \
  --repository-format=docker --location="${REGION}" --project "${PROJECT_ID}"

echo "Building image..."
if command -v docker >/dev/null 2>&1; then
  docker build -f Dockerfile.backend -t "${IMAGE}" .
else
  echo "docker not found; using Cloud Build to build the image"
  gcloud builds submit --project "${PROJECT_ID}" --config cloudbuild.backend.yaml --substitutions=_IMAGE="${IMAGE}" .
fi

if command -v docker >/dev/null 2>&1; then
  echo "Configuring docker auth for Artifact Registry..."
  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --project "${PROJECT_ID}" -q
  echo "Pushing image..."
  docker push "${IMAGE}"
fi

echo "Deploying to Cloud Run..."

# Optional Cloud SQL connection (project:region:instance)
EXTRA_FLAGS=()
if [[ -n "${CLOUDSQL_INSTANCE:-}" ]]; then
  EXTRA_FLAGS+=("--add-cloudsql-instances=${CLOUDSQL_INSTANCE}")
fi

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --port 8000 \
  --max-instances 2 \
  --concurrency 10 \
  --set-env-vars USE_OPENROUTER=true,USE_BIGQUERY_ANALYTICS=true,GCP_PROJECT=${PROJECT_ID},BQ_DATASET_CORE=core,VECTOR_BACKEND=vertex,HEARTBEAT_DB_BACKEND=${HEARTBEAT_DB_BACKEND:-duckdb} \
  --set-env-vars VERTEX_LOCATION=us-east1,VERTEX_EMBEDDING_MODEL=text-embedding-005 \
  "${EXTRA_FLAGS[@]}"

echo "Deployed. URL:"
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" \
  --format 'value(status.url)'
