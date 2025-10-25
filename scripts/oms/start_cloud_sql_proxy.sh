#!/bin/bash

# HeartBeat Engine - Start Cloud SQL Auth Proxy
# Runs the proxy on localhost:5434 for local development

set -e

PROXY_PORT=5434
INSTANCE_CONNECTION_NAME="heartbeat-474020:us-east1:hb-postgres"

echo "=========================================="
echo "CLOUD SQL AUTH PROXY - STARTING"
echo "=========================================="
echo ""
echo "Instance: $INSTANCE_CONNECTION_NAME"
echo "Local address: 127.0.0.1:$PROXY_PORT"
echo ""
echo "Press Ctrl+C to stop the proxy"
echo ""

cd "$(dirname "$0")/../.."

# Start the proxy
./cloud-sql-proxy \
  --address 127.0.0.1 \
  --port $PROXY_PORT \
  $INSTANCE_CONNECTION_NAME

