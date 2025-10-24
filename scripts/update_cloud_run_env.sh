#!/usr/bin/env bash
set -euo pipefail

# Update Cloud Run service environment variables for HeartBeat backend

# 1) Load env file if present to avoid repeated manual exports
#    Priority: $CLOUD_RUN_ENV_FILE -> .env.cloudrun -> .env (repo root)
ENV_FILE="${CLOUD_RUN_ENV_FILE:-}"
if [[ -z "${ENV_FILE}" ]]; then
  if [[ -f .env.cloudrun ]]; then
    ENV_FILE=.env.cloudrun
  elif [[ -f .env ]]; then
    ENV_FILE=.env
  fi
fi

if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
  echo "Loading variables from ${ENV_FILE} ..."
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

SERVICE_NAME=${SERVICE_NAME:-heartbeat-backend}
REGION=${REGION:-us-east1}
PROJECT_ID=${PROJECT_ID:-${GCP_PROJECT:-heartbeat-474020}}

# Optional variables to set (leave empty to skip setting)
DB_BACKEND=${HEARTBEAT_DB_BACKEND:-}
DB_URL=${DATABASE_URL:-}
VERTEX_ENDPOINT=${VERTEX_INDEX_ENDPOINT:-}
VERTEX_DEPLOYED_ID=${VERTEX_DEPLOYED_INDEX_ID:-}

echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"
echo "Vertex endpoint: ${VERTEX_ENDPOINT:-<not set>}"
echo "Deployed index: ${VERTEX_DEPLOYED_ID:-<not set>}"

SET_ARGS=(
  "USE_OPENROUTER=true"
  "USE_BIGQUERY_ANALYTICS=true"
  "GCP_PROJECT=${PROJECT_ID}"
  "BQ_DATASET_CORE=core"
  "VECTOR_BACKEND=vertex"
)

if [[ -n "$DB_BACKEND" ]]; then
  SET_ARGS+=("HEARTBEAT_DB_BACKEND=${DB_BACKEND}")
fi
if [[ -n "$DB_URL" ]]; then
  SET_ARGS+=("DATABASE_URL=${DB_URL}")
fi
if [[ -n "$VERTEX_ENDPOINT" ]]; then
  SET_ARGS+=("VERTEX_INDEX_ENDPOINT=${VERTEX_ENDPOINT}")
fi
if [[ -n "$VERTEX_DEPLOYED_ID" ]]; then
  SET_ARGS+=("VERTEX_DEPLOYED_INDEX_ID=${VERTEX_DEPLOYED_ID}")
fi

# Always set Vertex defaults
SET_ARGS+=("VERTEX_LOCATION=us-east1")
SET_ARGS+=("VERTEX_EMBEDDING_MODEL=text-embedding-005")

JOINED=$(IFS=,; echo "${SET_ARGS[*]}")

echo "Updating service env..."
gcloud run services update "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --set-env-vars "$JOINED"

echo "Done. Verify:"
echo "  gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(spec.template.spec.containers[0].env)'"
echo "  Then hit your service /api/v1/health and confirm 'vertex_configured: true'"

echo "\nUsage: export VERTEX_INDEX_ENDPOINT=projects/.../locations/.../indexEndpoints/XXXX"
echo "       export VERTEX_DEPLOYED_INDEX_ID=DEPLOYED_INDEX_ID"
echo "       ./scripts/update_cloud_run_env.sh"

# Convenience: print the service URL and ready-to-run curl command
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
echo "\nService URL: ${SERVICE_URL}"
echo "Health check: curl -s ${SERVICE_URL}/api/v1/health | jq"
