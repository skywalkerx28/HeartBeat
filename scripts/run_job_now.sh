#!/usr/bin/env bash
set -euo pipefail

JOB=${1:?"Usage: $0 <job-name>"}
REGION=${REGION:-us-east1}
PROJECT_ID=${PROJECT_ID:-${GCP_PROJECT:-heartbeat-474020}}

echo "Running job: ${JOB} (region=${REGION}, project=${PROJECT_ID})"
gcloud run jobs execute "${JOB}" --region "${REGION}" --project "${PROJECT_ID}"

echo "Executions:"
gcloud run jobs executions list --job "${JOB}" --region "${REGION}" --project "${PROJECT_ID}" --limit 5
