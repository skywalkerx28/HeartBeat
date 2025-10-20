#!/bin/bash

# HeartBeat Engine - GCP Phase 1 Infrastructure Setup
# Establishes GCS data lake and BigQuery datasets

set -e

PROJECT_ID="heartbeat-474020"
BUCKET_NAME="heartbeat-474020-lake"
# Use multi‑region US for datasets to align with BigLake connection
REGION="US"

echo "=========================================="
echo "HEARTBEAT GCP PHASE 1 SETUP"
echo "=========================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Bucket:  $BUCKET_NAME"
echo "Region:  $REGION"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if gcloud is authenticated
echo -e "${YELLOW}[1/6]${NC} Checking Google Cloud authentication..."
if ! gcloud auth application-default print-access-token > /dev/null 2>&1; then
    echo -e "${RED}Error: Not authenticated with Google Cloud${NC}"
    echo "Run: gcloud auth application-default login"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated${NC}"

# Enable required APIs
echo -e "${YELLOW}[2/6]${NC} Enabling required GCP APIs..."
gcloud services enable storage.googleapis.com \
  bigquery.googleapis.com \
  biglake.googleapis.com \
  aiplatform.googleapis.com \
  --project=$PROJECT_ID \
  --quiet

echo -e "${GREEN}✓ APIs enabled${NC}"

# Create GCS bucket
echo -e "${YELLOW}[3/6]${NC} Creating GCS data lake bucket..."
if gsutil ls -b gs://$BUCKET_NAME > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Bucket already exists${NC}"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l us-east1 gs://$BUCKET_NAME
    gsutil versioning set on gs://$BUCKET_NAME
    echo -e "${GREEN}✓ Bucket created with versioning${NC}"
fi

# Create directory structure (placeholders via .keep files)
echo -e "${YELLOW}[4/6]${NC} Creating bucket directory structure..."
create_prefix() {
  local prefix=$1
  if ! gsutil -q stat gs://$BUCKET_NAME/$prefix/.keep >/dev/null 2>&1; then
    echo "  Initializing gs://$BUCKET_NAME/$prefix"
    echo "placeholder" | gsutil cp - gs://$BUCKET_NAME/$prefix/.keep >/dev/null 2>&1 || true
  fi
}

create_prefix "bronze"
create_prefix "silver"
create_prefix "silver/fact/pbp"
create_prefix "silver/fact/player_game_stats"
create_prefix "silver/fact/league_player_stats"
create_prefix "silver/dim/rosters"
create_prefix "silver/dim/depth_charts"
create_prefix "silver/dim/player_profiles"
create_prefix "silver/market/contracts"
create_prefix "gold"
create_prefix "gold/analytics"
create_prefix "gold/ontology"
create_prefix "rag"
create_prefix "rag/embeddings"

echo -e "${GREEN}✓ Directory structure created${NC}"

# Create BigQuery datasets
echo -e "${YELLOW}[5/6]${NC} Creating BigQuery datasets..."
bq mk --location=$REGION --dataset --description="External tables over silver Parquet" $PROJECT_ID:raw 2>/dev/null || echo "  raw dataset exists"
bq mk --location=$REGION --dataset --description="Core native tables (hot facts)" $PROJECT_ID:core 2>/dev/null || echo "  core dataset exists"
bq mk --location=$REGION --dataset --description="Analytics materialized views" $PROJECT_ID:analytics 2>/dev/null || echo "  analytics dataset exists"
bq mk --location=$REGION --dataset --description="Ontology semantic layer" $PROJECT_ID:ontology 2>/dev/null || echo "  ontology dataset exists"
bq mk --location=$REGION --dataset --description="CBA documents, rules, and helpers" $PROJECT_ID:cba 2>/dev/null || echo "  cba dataset exists"
echo -e "${GREEN}✓ BigQuery datasets ready${NC}"

# Configure IAM permissions
echo -e "${YELLOW}[6/6]${NC} Configuring IAM permissions..."
SA_EMAIL=$(gcloud config get-value account)

echo "  Granting BigQuery roles to $SA_EMAIL..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:$SA_EMAIL" \
  --role="roles/bigquery.dataEditor" \
  --condition=None \
  --quiet > /dev/null 2>&1 || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:$SA_EMAIL" \
  --role="roles/bigquery.jobUser" \
  --condition=None \
  --quiet > /dev/null 2>&1 || true

echo "  Granting GCS permissions..."
gsutil iam ch user:$SA_EMAIL:objectAdmin gs://$BUCKET_NAME 2>/dev/null || true

echo -e "${GREEN}✓ IAM permissions configured${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}GCP PHASE 1 SETUP COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run: python3 scripts/gcp/sync_parquet_to_gcs.py"
echo "2. Run: bash scripts/gcp/create_biglake_tables.sh"
echo "3. Run: python3 scripts/gcp/test_phase1_deployment.py"
echo ""
