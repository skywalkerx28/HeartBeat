#!/bin/bash

# HeartBeat Engine - Initialize Media Schema in Cloud SQL
# Creates media schema and tables for production video clip management

set -e

echo "=========================================="
echo "MEDIA SCHEMA INITIALIZATION"
echo "=========================================="
echo ""

# Check DATABASE_URL is set
if [[ -z "${DATABASE_URL}" ]]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    echo ""
    echo "For local dev with Cloud SQL proxy:"
    echo "  export DATABASE_URL=\"postgresql+psycopg2://heartbeat:PASSWORD@127.0.0.1:5434/postgres\""
    echo ""
    exit 1
fi

# Parse DATABASE_URL
if [[ $DATABASE_URL =~ postgresql\+psycopg2://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
else
    echo "ERROR: Could not parse DATABASE_URL"
    exit 1
fi

echo "Database: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo ""

# Apply migration
echo "[1/2] Creating media schema and tables..."
PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    -f backend/media/migrations/001_media_schema.sql

echo ""
echo "[2/2] Verifying media tables..."
PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    -c "\dt media.*"

echo ""
echo "=========================================="
echo "MEDIA SCHEMA INITIALIZATION COMPLETE"
echo "=========================================="
echo ""
echo "Media Schema: media"
echo "Tables: clips, clip_assets, clip_tags"
echo ""
echo "Next steps:"
echo "  1. Set MEDIA_GCS_BUCKET env var (default: heartbeat-media)"
echo "  2. Create GCS bucket: gsutil mb -l us-east1 gs://heartbeat-media"
echo "  3. Enable Cloud CDN (optional): Set MEDIA_CDN_DOMAIN"
echo "  4. Test API: curl http://localhost:8000/api/v2/clips/"
echo ""

