#!/bin/bash

# HeartBeat Engine - Upload CBA PDFs to GCS
# Upload CBA documents to bronze/reference/cba/ tier

set -e

PROJECT_ID="heartbeat-474020"
BUCKET_NAME="heartbeat-474020-lake"
LOCAL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "UPLOAD CBA PDFS TO GCS"
echo "=========================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Bucket:  gs://$BUCKET_NAME"
echo "Local:   $LOCAL_ROOT"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if PDFs exist
echo -e "${YELLOW}[1/3]${NC} Checking for CBA PDFs..."
if [ ! -f "$LOCAL_ROOT/nhl_cba_2012.pdf" ]; then
    echo -e "${RED}Error: nhl_cba_2012.pdf not found in $LOCAL_ROOT${NC}"
    exit 1
fi

if [ ! -f "$LOCAL_ROOT/nhl_mou_2020.pdf" ]; then
    echo -e "${RED}Error: nhl_mou_2020.pdf not found in $LOCAL_ROOT${NC}"
    exit 1
fi

if [ ! -f "$LOCAL_ROOT/nhl_mou_2025.pdf" ]; then
    echo -e "${RED}Error: nhl_mou_2025.pdf not found in $LOCAL_ROOT${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All CBA PDFs found${NC}"
echo ""

# Check if bucket exists
echo -e "${YELLOW}[2/3]${NC} Checking GCS bucket..."
if ! gsutil ls gs://$BUCKET_NAME > /dev/null 2>&1; then
    echo -e "${RED}Error: Bucket gs://$BUCKET_NAME not found${NC}"
    echo "Run: gsutil mb -p $PROJECT_ID -l us-east1 gs://$BUCKET_NAME"
    exit 1
fi
echo -e "${GREEN}✓ Bucket accessible${NC}"
echo ""

# Upload PDFs
echo -e "${YELLOW}[3/3]${NC} Uploading CBA PDFs..."

echo "  Uploading nhl_cba_2012.pdf..."
gsutil cp "$LOCAL_ROOT/nhl_cba_2012.pdf" \
    gs://$BUCKET_NAME/bronze/reference/cba/nhl_cba_2012.pdf

echo "  Uploading nhl_mou_2020.pdf..."
gsutil cp "$LOCAL_ROOT/nhl_mou_2020.pdf" \
    gs://$BUCKET_NAME/bronze/reference/cba/nhl_mou_2020.pdf

echo "  Uploading nhl_mou_2025.pdf..."
gsutil cp "$LOCAL_ROOT/nhl_mou_2025.pdf" \
    gs://$BUCKET_NAME/bronze/reference/cba/nhl_mou_2025.pdf

echo -e "${GREEN}✓ Upload complete${NC}"
echo ""

# Verify uploads
echo "Verifying uploads..."
gsutil ls -lh gs://$BUCKET_NAME/bronze/reference/cba/

echo ""
echo "=========================================="
echo "UPLOAD COMPLETE"
echo "=========================================="
echo ""
echo "PDFs available at:"
echo "  gs://$BUCKET_NAME/bronze/reference/cba/nhl_cba_2012.pdf"
echo "  gs://$BUCKET_NAME/bronze/reference/cba/nhl_mou_2020.pdf"
echo "  gs://$BUCKET_NAME/bronze/reference/cba/nhl_mou_2025.pdf"
echo ""
echo "Next: python scripts/sync_cba_to_gcs.py"

