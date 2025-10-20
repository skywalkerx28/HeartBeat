#!/bin/bash

# HeartBeat Engine - Create BigLake Tables and Connection
# Sets up BigLake connection and external tables over GCS Parquet

set -e

PROJECT_ID="heartbeat-474020"
# Use multi‑region US so it matches dataset locations
REGION="US"
CONNECTION_NAME="lake-connection"
BUCKET_NAME="heartbeat-474020-lake"

echo "=========================================="
echo "BIGLAKE SETUP"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Create BigLake connection
echo -e "${YELLOW}[1/3]${NC} Creating BigLake connection..."
if bq show --connection --location=$REGION --project_id=$PROJECT_ID $CONNECTION_NAME > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connection already exists${NC}"
else
    bq mk --connection \
        --location=$REGION \
        --project_id=$PROJECT_ID \
        --connection_type=CLOUD_RESOURCE \
        $CONNECTION_NAME
    echo -e "${GREEN}✓ Connection created${NC}"
fi

# Step 2: Grant GCS permissions to BigLake service account
echo -e "${YELLOW}[2/3]${NC} Granting GCS permissions to BigLake service account..."
# Robust JSON parsing for service account id
BQ_SA=$(bq show --connection --location=$REGION --project_id=$PROJECT_ID $CONNECTION_NAME --format=json | jq -r '.cloudResource.serviceAccountId')
if [ -z "$BQ_SA" ] || [ "$BQ_SA" = "null" ]; then
  echo -e "${RED}Error: Could not retrieve BigLake service account${NC}"
  exit 1
fi
echo "  BigLake service account: $BQ_SA"
gsutil iam ch serviceAccount:$BQ_SA:objectViewer gs://$BUCKET_NAME
echo -e "${GREEN}✓ Permissions granted${NC}"

# Step 3: Create external tables
echo -e "${YELLOW}[3/3]${NC} Creating BigLake external tables..."

# Execute SQL file with BigQuery CLI
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/create_biglake_tables.sql

echo -e "${GREEN}✓ External tables created${NC}"

# Verify tables
echo ""
echo "Verifying external tables..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID --format=pretty \
  "SELECT table_name, table_type 
   FROM \`$PROJECT_ID.raw.INFORMATION_SCHEMA.TABLES\`
   WHERE table_type = 'EXTERNAL'
   ORDER BY table_name"

echo ""
echo "=========================================="
echo -e "${GREEN}BIGLAKE SETUP COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run: python3 scripts/load_core_tables.py"
echo "2. Run: python3 scripts/test_phase1_deployment.py"
echo ""
