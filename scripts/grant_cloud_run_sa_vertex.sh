#!/usr/bin/env bash
set -euo pipefail

# Grant Vertex AI permissions to the Cloud Run service account
# Ensures the backend can call Matching Engine (Vertex Vector Search)

SERVICE_NAME=${SERVICE_NAME:-heartbeat-backend}
REGION=${REGION:-us-east1}
PROJECT_ID=${PROJECT_ID:-${GCP_PROJECT:-heartbeat-474020}}

echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"

# Ensure API is enabled
echo "Enabling Vertex AI API (if not already enabled)..."
gcloud services enable aiplatform.googleapis.com --project "$PROJECT_ID" >/dev/null 2>&1 || true

echo "Resolving Cloud Run service account..."
SA=$(gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format='value(spec.template.spec.serviceAccountName)' || true)

if [[ -z "${SA}" ]]; then
  echo "No explicit service account on the service; using default Compute Engine SA"
  PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

echo "Service Account: ${SA}"

ROLE="roles/aiplatform.user"
echo "Granting role: ${ROLE}"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA}" \
  --role "${ROLE}" >/dev/null

echo "Verifying grant..."
gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --format='table(bindings.role:label=ROLE, bindings.members:label=MEMBER)' \
  --filter="bindings.members:serviceAccount:${SA} AND bindings.role:${ROLE}"

echo "Done. The Cloud Run service account can now call Vertex Matching Engine."

# Optional (uncomment if needed for your environment):
# gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA}" --role roles/storage.objectViewer
# gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA}" --role roles/bigquery.dataViewer
# gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA}" --role roles/bigquery.readSessionUser
# gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA}" --role roles/logging.logWriter
# gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA}" --role roles/monitoring.metricWriter

