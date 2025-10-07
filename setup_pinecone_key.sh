#!/bin/bash

# HeartBeat Engine - Pinecone API Key Setup
echo "=========================================="
echo "PINECONE API KEY SETUP"
echo "=========================================="
echo ""
echo "Get your API key from: https://app.pinecone.io/"
echo ""
read -p "Enter your Pinecone API Key: " PINECONE_KEY
echo ""

# Add to .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << ENVEOF
# HeartBeat Engine Environment Variables
PINECONE_API_KEY=${PINECONE_KEY}
ENVEOF
else
    echo "PINECONE_API_KEY=${PINECONE_KEY}" >> .env
fi

# Also export for current session
export PINECONE_API_KEY="${PINECONE_KEY}"

echo "✅ Pinecone API key configured!"
echo ""
echo "Testing connection..."
python3 << PYEOF
from pinecone.grpc import PineconeGRPC as Pinecone

try:
    pc = Pinecone(api_key="${PINECONE_KEY}")
    indexes = pc.list_indexes()
    print(f"✅ Connection successful!")
    print(f"   Found {len(indexes)} indexes")
    for idx in indexes:
        print(f"   - {idx.name}")
except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
PYEOF

echo ""
echo "To use in future sessions, run:"
echo "  source .env"
