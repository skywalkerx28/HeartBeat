#!/usr/bin/env bash
set -euo pipefail

# Deploy Cloud Run Jobs + Cloud Scheduler for HeartBeat.bot (Path B)
# Schedules articles/transactions/injuries/news collection without Celery.

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

PROJECT_ID=${PROJECT_ID:-${GCP_PROJECT:-heartbeat-474020}}
REGION=${REGION:-us-east1}
SERVICE_NAME=${SERVICE_NAME:-heartbeat-backend}

echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Service:  ${SERVICE_NAME} (source for image)"

echo "Ensuring required APIs..."
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com --project "${PROJECT_ID}" >/dev/null

echo "Resolving backend service image..."
IMAGE=$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" \
  --format='value(spec.template.spec.containers[0].image)')
if [[ -z "${IMAGE}" ]]; then
  echo "Could not resolve image from service ${SERVICE_NAME}. Set IMAGE env or deploy service first." >&2
  exit 1
fi
echo "Image: ${IMAGE}"

# Upsert helper for Cloud Run Job
upsert_job() {
  local NAME="$1"; shift
  local TASK_CMD=("python" "-m" "bot.runner" "$@")

  # Enforce Postgres only
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "ERROR: DATABASE_URL must be set (postgres DSN) before deploying jobs." >&2
    exit 2
  fi
  local CHOSEN_DB_BACKEND="postgres"

  local ENV_VARS=(
    "PYTHONPATH=/app/backend:/app"
    "GCP_PROJECT=${PROJECT_ID}"
    "USE_BIGQUERY_ANALYTICS=${USE_BIGQUERY_ANALYTICS:-true}"
    "BQ_DATASET_CORE=${BQ_DATASET_CORE:-core}"
    "HEARTBEAT_DB_BACKEND=${CHOSEN_DB_BACKEND}"
  )
  # DuckDB is no longer supported; no conditional vars needed
  if [[ -n "${DATABASE_URL:-}" ]]; then ENV_VARS+=("DATABASE_URL=${DATABASE_URL}"); fi
  if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then ENV_VARS+=("OPENROUTER_API_KEY=${OPENROUTER_API_KEY}"); fi
  if [[ -n "${VERTEX_INDEX_ENDPOINT:-}" ]]; then ENV_VARS+=("VERTEX_INDEX_ENDPOINT=${VERTEX_INDEX_ENDPOINT}"); fi
  if [[ -n "${VERTEX_DEPLOYED_INDEX_ID:-}" ]]; then ENV_VARS+=("VERTEX_DEPLOYED_INDEX_ID=${VERTEX_DEPLOYED_INDEX_ID}"); fi
  if [[ -n "${VERTEX_LOCATION:-}" ]]; then ENV_VARS+=("VERTEX_LOCATION=${VERTEX_LOCATION}"); fi
  if [[ -n "${VERTEX_EMBEDDING_MODEL:-}" ]]; then ENV_VARS+=("VERTEX_EMBEDDING_MODEL=${VERTEX_EMBEDDING_MODEL}"); fi
  if [[ -n "${GCS_LAKE_BUCKET:-}" ]]; then ENV_VARS+=("GCS_LAKE_BUCKET=${GCS_LAKE_BUCKET}"); fi

  local JOINED
  JOINED=$(IFS=,; echo "${ENV_VARS[*]}")

  local EXTRA_J_FLAGS=()
  if [[ -n "${CLOUDSQL_INSTANCE:-}" ]]; then
    EXTRA_J_FLAGS+=("--add-cloudsql-instances=${CLOUDSQL_INSTANCE}")
  fi

  # Build repeated --args flags for gcloud (one per arg after command)
  local ARGS_FLAGS=()
  for a in "${TASK_CMD[@]:1}"; do
    ARGS_FLAGS+=("--args=$a")
  done

  if gcloud run jobs describe "${NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Updating job ${NAME} ..."
    gcloud run jobs update "${NAME}" \
      --image "${IMAGE}" \
      --region "${REGION}" \
      --project "${PROJECT_ID}" \
      --tasks 1 \
      --max-retries 1 \
      --set-env-vars "${JOINED}" \
      --command "${TASK_CMD[0]}" "${ARGS_FLAGS[@]}" \
      ${EXTRA_J_FLAGS[@]+"${EXTRA_J_FLAGS[@]}"} >/dev/null
  else
    echo "Creating job ${NAME} ..."
    gcloud run jobs create "${NAME}" \
      --image "${IMAGE}" \
      --region "${REGION}" \
      --project "${PROJECT_ID}" \
      --tasks 1 \
      --max-retries 1 \
      --memory 1Gi \
      --cpu 1 \
      --set-env-vars "${JOINED}" \
      --command "${TASK_CMD[0]}" "${ARGS_FLAGS[@]}" \
      ${EXTRA_J_FLAGS[@]+"${EXTRA_J_FLAGS[@]}"} >/dev/null
  fi
}

# Scheduler helper that triggers job runs via authorized HTTP call
ensure_scheduler_job() {
  local NAME="$1"; shift
  local CRON="$1"; shift

  local SA_EMAIL="${SCHEDULER_SA:-scheduler@${PROJECT_ID}.iam.gserviceaccount.com}"
  # Create SA if missing and grant minimal roles to run jobs
  gcloud iam service-accounts describe "${SA_EMAIL}" --project "${PROJECT_ID}" >/dev/null 2>&1 || \
    gcloud iam service-accounts create scheduler --project "${PROJECT_ID}" --display-name "Cloud Scheduler for HeartBeat"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member "serviceAccount:${SA_EMAIL}" --role roles/run.admin >/dev/null
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member "serviceAccount:${SA_EMAIL}" --role roles/iam.serviceAccountTokenCreator >/dev/null

  local JOB_URL="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${NAME}:run"

  if gcloud scheduler jobs describe "${NAME}" --project "${PROJECT_ID}" --location "${REGION}" >/dev/null 2>&1; then
    echo "Updating scheduler ${NAME} (${CRON}) ..."
    gcloud scheduler jobs update http "${NAME}" \
      --project "${PROJECT_ID}" --location "${REGION}" \
      --schedule "${CRON}" --http-method POST \
      --uri "${JOB_URL}" \
      --oauth-service-account-email "${SA_EMAIL}" \
      --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform" >/dev/null
  else
    echo "Creating scheduler ${NAME} (${CRON}) ..."
    gcloud scheduler jobs create http "${NAME}" \
      --project "${PROJECT_ID}" --location "${REGION}" \
      --schedule "${CRON}" --http-method POST \
      --uri "${JOB_URL}" \
      --oauth-service-account-email "${SA_EMAIL}" \
      --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform" >/dev/null
  fi
}

echo "Upserting Cloud Run Jobs..."
upsert_job hb-collect-transactions collect-transactions
upsert_job hb-collect-injuries collect-injury-reports
upsert_job hb-collect-team-news collect-team-news
upsert_job hb-collect-game-summaries collect-game-summaries
upsert_job hb-aggregate-news aggregate-news
upsert_job hb-generate-daily-article generate-daily-article
upsert_job hb-ontology-refresh ontology-refresh

echo "Upserting Cloud Scheduler entries..."
ensure_scheduler_job hb-collect-transactions "*/30 * * * *"
ensure_scheduler_job hb-collect-injuries "0 */6 * * *"
ensure_scheduler_job hb-collect-team-news "0 6 * * *"
ensure_scheduler_job hb-collect-game-summaries "0 1 * * *"
ensure_scheduler_job hb-aggregate-news "0 */6 * * *"
ensure_scheduler_job hb-generate-daily-article "0 7 * * *"
ensure_scheduler_job hb-ontology-refresh "0 4 * * *"

echo "Done. To run a job immediately:"
echo "  gcloud run jobs run hb-collect-transactions --region ${REGION} --project ${PROJECT_ID}"
echo "Check job executions:"
echo "  gcloud run jobs executions list --job hb-collect-transactions --region ${REGION} --project ${PROJECT_ID}"
