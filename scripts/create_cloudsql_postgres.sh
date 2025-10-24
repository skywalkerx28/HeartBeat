#!/usr/bin/env bash
set -euo pipefail

# Create a Cloud SQL for PostgreSQL instance, database, and user for HeartBeat

PROJECT_ID=${PROJECT_ID:-${GCP_PROJECT:-heartbeat-474020}}
REGION=${REGION:-us-east1}
INSTANCE=${INSTANCE:-hb-postgres}
DB_VERSION=${DB_VERSION:-POSTGRES_15}
CPU=${CPU:-1}
MEMORY=${MEMORY:-3840MiB} # 3.75 GiB
DB_NAME=${DB_NAME:-heartbeat}
DB_USER=${DB_USER:-heartbeat}
DB_PASSWORD=${DB_PASSWORD:-}

echo "Project:   $PROJECT_ID"
echo "Region:    $REGION"
echo "Instance:  $INSTANCE"
echo "DB:        $DB_NAME (user: $DB_USER)"

if [[ -z "$DB_PASSWORD" ]]; then
  echo "Generating random DB password..."
  DB_PASSWORD=$(python3 - <<'PY'
import secrets,string
alphabet = string.ascii_letters+string.digits
print(''.join(secrets.choice(alphabet) for _ in range(24)))
PY
)
fi

echo "Enabling Cloud SQL Admin API..."
gcloud services enable sqladmin.googleapis.com --project "$PROJECT_ID" -q

echo "Creating Cloud SQL Postgres instance (this can take several minutes)..."
gcloud sql instances create "$INSTANCE" \
  --project "$PROJECT_ID" \
  --database-version "$DB_VERSION" \
  --region "$REGION" \
  --cpu "$CPU" \
  --memory "$MEMORY" \
  --no-assign-ip \
  --storage-auto-increase \
  --quiet

echo "Creating database '$DB_NAME'..."
gcloud sql databases create "$DB_NAME" --instance "$INSTANCE" --project "$PROJECT_ID" -q

echo "Creating user '$DB_USER'..."
gcloud sql users create "$DB_USER" --instance "$INSTANCE" --password "$DB_PASSWORD" --project "$PROJECT_ID" -q

CONN_NAME=$(gcloud sql instances describe "$INSTANCE" --project "$PROJECT_ID" --format 'value(connectionName)')
echo "\nConnection name: $CONN_NAME"

echo "\nRecommended Cloud Run config:"
echo "  export CLOUDSQL_INSTANCE='$CONN_NAME'"
echo "  export HEARTBEAT_DB_BACKEND=postgres"
echo "  export DATABASE_URL='postgresql+psycopg2://$DB_USER:$DB_PASSWORD@/$DB_NAME?host=/cloudsql/$CONN_NAME'"

echo "\nTo grant Cloud Run service account access to Cloud SQL, run:"
echo "  scripts/grant_cloud_run_sql_access.sh"

