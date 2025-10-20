#!/bin/bash

# HeartBeat Engine - Create Ontology Views
# Applies semantic layer views in BigQuery `raw` dataset (objects_*)

set -e

PROJECT_ID=${GCP_PROJECT:-heartbeat-474020}

echo "=========================================="
echo "ONTOLOGY VIEWS SETUP"
echo "=========================================="

echo "Project: $PROJECT_ID"

echo "Applying views..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/gcp/create_ontology_views.sql

echo "\nListing object views in dataset 'raw':"
bq ls --project_id=$PROJECT_ID ${PROJECT_ID}:raw | grep objects_

echo "\nDone."
