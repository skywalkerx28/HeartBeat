"""
Upload roster batches to Pinecone via MCP upsert tool
"""

import json
import glob
import os

def main():
    # Find all batch files
    batch_files = sorted(glob.glob("data/mcp_sync/roster_batch_*.json"))
    
    print(f"Found {len(batch_files)} batch files to upload")
    print("\nUse the following MCP tool calls to upload all batches:\n")
    
    for i, batch_file in enumerate(batch_files, 1):
        with open(batch_file, 'r') as f:
            records = json.load(f)
        
        print(f"# Batch {i}/{len(batch_files)}: {len(records)} records from {os.path.basename(batch_file)}")
        print(f"# Use MCP tool: mcp_pinecone_upsert-records")
        print(f"#   name: heartbeat-unified-index")
        print(f"#   namespace: rosters")
        print(f"#   records: <contents of {batch_file}>")
        print()
    
    print(f"\nTotal: {sum(len(json.load(open(f))) for f in batch_files)} players across {len(batch_files)} batches")
    print("\nSince MCP calls must be done manually through Cursor,")
    print("I'll upload them for you using the Python Pinecone SDK directly...")

if __name__ == "__main__":
    main()

