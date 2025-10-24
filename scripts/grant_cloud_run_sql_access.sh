#!/usr/bin/env bash
set -euo pipefail

# Grant Cloud SQL Client role to the Cloud Run service account

PROJECT_ID=${PROJECT_ID:-${GCP_PROJECT:-heartbeat-474020}}
REGION=${REGION:-us-east1}
SERVICE_NAME=${SERVICE_NAME:-heartbeat-backend}

echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"

SA=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(spec.template.spec.serviceAccountName)')
if [[ -z "$SA" ]]; then
  # Default Cloud Run service account is the Compute Default SA
  PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
fi

echo "Granting roles/cloudsql.client to $SA ..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA}" \
  --role roles/cloudsql.client -q

echo "Done. The service can now connect to Cloud SQL when deployed with --add-cloudsql-instances."

