#!/usr/bin/env bash
set -euo pipefail

# Deploy HeartBeat FastAPI backend to Cloud Run

# Load env file (priority: $CLOUD_RUN_ENV_FILE -> .env.cloudrun -> .env)
ENV_FILE="${CLOUD_RUN_ENV_FILE:-}"
if [[ -z "${ENV_FILE}" ]]; then
  if [[ -f .env.cloudrun ]]; then ENV_FILE=.env.cloudrun; elif [[ -f .env ]]; then ENV_FILE=.env; fi
fi
if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
  echo "Loading variables from ${ENV_FILE} ..."
  set -a; # export all
  # shellcheck disable=SC1090
  source "${ENV_FILE}"; set +a
fi

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

# Enforce Postgres-only: require DATABASE_URL
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL must be set (postgres DSN) before deploying backend." >&2
  exit 2
fi
EXTRA_FLAGS+=("--set-env-vars=DATABASE_URL=${DATABASE_URL}")

# Add lake bucket and optional roster path for Cloud Run search endpoint
if [[ -n "${GCS_LAKE_BUCKET:-}" ]]; then
  EXTRA_FLAGS+=("--set-env-vars=GCS_LAKE_BUCKET=${GCS_LAKE_BUCKET}")
fi
if [[ -n "${ROSTER_UNIFIED_PATH:-}" ]]; then
  EXTRA_FLAGS+=("--set-env-vars=ROSTER_UNIFIED_PATH=${ROSTER_UNIFIED_PATH}")
fi

# Optional OpenRouter API key for orchestrator
if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
  EXTRA_FLAGS+=("--set-env-vars=OPENROUTER_API_KEY=${OPENROUTER_API_KEY}")
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
  --set-env-vars USE_OPENROUTER=true,USE_BIGQUERY_ANALYTICS=true,GCP_PROJECT=${PROJECT_ID},BQ_DATASET_CORE=core,VECTOR_BACKEND=vertex,HEARTBEAT_DB_BACKEND=postgres \
  --set-env-vars VERTEX_LOCATION=us-east1,VERTEX_EMBEDDING_MODEL=text-embedding-005 \
  ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}

echo "Deployed. URL:"
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" \
  --format 'value(status.url)'
