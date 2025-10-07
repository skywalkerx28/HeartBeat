#!/bin/bash

# HeartBeat Engine - Complete Pinecone Sync
# Syncs rosters and data catalog to Pinecone for optimal RAG performance

echo "=========================================="
echo "HEARTBEAT PINECONE SYNC"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check environment
if [ -z "$PINECONE_API_KEY" ]; then
    echo -e "${RED}Error: PINECONE_API_KEY not set${NC}"
    echo "Run: source .env"
    exit 1
fi

# Activate venv
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: venv not found${NC}"
    exit 1
fi

source venv/bin/activate

# Sync rosters
echo -e "${YELLOW}[1/2] Syncing NHL rosters...${NC}"
python3 scripts/sync_rosters_to_pinecone.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Rosters synced${NC}"
else
    echo -e "${RED}✗ Roster sync failed${NC}"
    exit 1
fi

echo ""

# Sync data catalog
echo -e "${YELLOW}[2/2] Syncing data catalog...${NC}"
python3 scripts/sync_data_catalog_to_pinecone.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Catalog synced${NC}"
else
    echo -e "${RED}✗ Catalog sync failed${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}SYNC COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Pinecone Index Updated:"
echo "  - rosters: ~853 NHL players"
echo "  - catalog: Data source metadata"
echo "  - events: Game recaps (existing)"
echo "  - context: Metric definitions (existing)"
echo ""
echo "Test with queries like:"
echo "  - 'What team is Ivan Demidov on?'"
echo "  - 'Show me MTL roster'"
echo "  - 'What data do you have about power play?'"
echo ""

