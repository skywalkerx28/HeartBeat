#!/bin/bash

# HeartBeat Engine - Initialize OMS in PostgreSQL
# Creates oms schema and tables in production Postgres database

set -e

echo "=========================================="
echo "OMS POSTGRESQL INITIALIZATION"
echo "=========================================="
echo ""

# Check DATABASE_URL is set
if [[ -z "${DATABASE_URL}" ]]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    echo ""
    echo "Load your .env file first:"
    echo "  export \$(cat .env | xargs)"
    echo ""
    exit 1
fi

# Parse DATABASE_URL (format: postgresql+psycopg2://user:pass@host:port/dbname)
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

# Construct PostgreSQL connection string
PG_CONN="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Apply PostgreSQL migration
echo "[1/2] Creating OMS schema and tables in PostgreSQL..."
PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    -f backend/ontology/migrations/001_initial_schema_postgres.sql

echo ""
echo "[2/2] Verifying OMS tables..."
PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    -c "\dt oms.*"

echo ""
echo "=========================================="
echo "OMS POSTGRESQL INITIALIZATION COMPLETE"
echo "=========================================="
echo ""
echo "OMS Schema: oms"
echo "Tables: schema_versions, object_types, properties, link_types,"
echo "        action_types, security_policies, policy_rules, audit_log"
echo ""
echo "Next steps:"
echo "  1. Load OMS schema: python3 -m backend.ontology.cli load backend/ontology/schemas/v0.1/schema.yaml --user admin"
echo "  2. Start backend: python3 -m uvicorn backend.main:app --reload"
echo ""
