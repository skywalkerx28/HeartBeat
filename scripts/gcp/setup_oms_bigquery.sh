#!/bin/bash

# HeartBeat Engine - Setup OMS BigQuery Integration
# Creates ontology views in BigQuery and loads OMS schema
#
# This script ensures OMS resolvers query real BigQuery data (not copies).
# Data stays in BigQuery; OMS is metadata-only control plane.

set -e

PROJECT_ID=${GCP_PROJECT:-heartbeat-474020}
DATASET_ONTOLOGY="ontology"

echo "=========================================="
echo "OMS BIGQUERY INTEGRATION SETUP"
echo "=========================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Ontology Dataset: $DATASET_ONTOLOGY"
echo ""

# Step 1: Create ontology dataset if it doesn't exist
echo "[1/3] Creating ontology dataset..."
bq mk --dataset --location=us-east1 --description="Ontology semantic layer for HeartBeat OMS" \
  ${PROJECT_ID}:${DATASET_ONTOLOGY} 2>/dev/null || echo "  Dataset already exists (OK)"

# Step 2: Create ontology views
echo ""
echo "[2/3] Creating ontology views (objects and links)..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/gcp/create_oms_ontology_views.sql

echo ""
echo "Verifying object views..."
bq ls --project_id=$PROJECT_ID ${PROJECT_ID}:${DATASET_ONTOLOGY} | grep objects_

echo ""
echo "Verifying link views..."
bq ls --project_id=$PROJECT_ID ${PROJECT_ID}:${DATASET_ONTOLOGY} | grep links_

# Step 3: Load OMS schema pointing to these views
echo ""
echo "[3/3] Loading OMS schema v0.1..."
cd "$(dirname "$0")/../.."
python3 -m backend.ontology.cli load backend/ontology/schemas/v0.1/schema.yaml --user system

echo ""
echo "=========================================="
echo "OMS BIGQUERY INTEGRATION COMPLETE"
echo "=========================================="
echo ""
echo "✓ Ontology dataset created: ${PROJECT_ID}:${DATASET_ONTOLOGY}"
echo "✓ Object views created (objects_player, objects_team, objects_contract, etc.)"
echo "✓ Link views created (links_team_players, links_player_contracts)"
echo "✓ OMS schema v0.1 loaded and published"
echo ""
echo "Data Location: BigQuery (no data copied)"
echo "OMS Role: Metadata control plane + policy enforcement"
echo "Resolvers: Query ontology.* views with user policies applied"
echo ""
echo "Test OMS API:"
echo "  curl http://localhost:8000/ontology/v1/schema/active"
echo "  curl http://localhost:8000/ontology/v1/meta/objects"
echo ""
echo "Test POC Routes:"
echo "  curl http://localhost:8000/api/v1/oms-demo/teams/MTL/roster -H 'Authorization: Bearer TOKEN'"
echo ""

