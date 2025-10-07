"""
Direct Pinecone Upload using SDK
Uploads all 71 metric contexts to enable expert hockey analysis
"""

import json
from pathlib import Path
import os

# Check if Pinecone SDK is available
try:
    from pinecone.grpc import PineconeGRPC as Pinecone
    from pinecone import ServerlessSpec
except ImportError:
    print("Installing Pinecone SDK...")
    os.system("pip install -q pinecone[grpc]")
    from pinecone.grpc import PineconeGRPC as Pinecone


def main():
    print("="*80)
    print("HEARTBEAT - UPLOADING METRIC CONTEXTS TO PINECONE")
    print("="*80)
    
    # Initialize Pinecone (will use PINECONE_API_KEY from environment)
    api_key = os.getenv("PINECONE_API_KEY")
    
    if not api_key:
        print("\n❌ PINECONE_API_KEY not set!")
        print("Set it with: export PINECONE_API_KEY='your-key-here'")
        return
    
    pc = Pinecone(api_key=api_key)
    
    # Connect to index
    index_name = "heartbeat-unified-index"
    index = pc.Index(index_name)
    
    print(f"\n✓ Connected to index: {index_name}")
    
    # Load contexts
    context_file = Path("/tmp/all_71_contexts.json")
    with open(context_file, 'r') as f:
        contexts = json.load(f)
    
    print(f"✓ Loaded {len(contexts)} contexts\n")
    
    # Upload in batches
    batch_size = 20
    namespace = "context"
    
    for i in range(0, len(contexts), batch_size):
        batch = contexts[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"Uploading batch {batch_num}: {len(batch)} records...")
        
        # Convert to Pinecone format (let Pinecone's inference handle embeddings)
        index.upsert(
            vectors=[],  # Empty - using inference
            namespace=namespace,
            data=batch  # Pinecone auto-embeds using multilingual-e5-large
        )
        
        print(f"  ✓ Batch {batch_num} uploaded")
    
    print(f"\n{'='*80}")
    print(f"✅ UPLOAD COMPLETE - {len(contexts)} contexts in Pinecone!")
    print(f"{'='*80}")
    print(f"\nNamespace: {namespace}")
    print(f"Index: {index_name}")
    print(f"\nModel can now retrieve expert hockey context dynamically!")


if __name__ == "__main__":
    main()

