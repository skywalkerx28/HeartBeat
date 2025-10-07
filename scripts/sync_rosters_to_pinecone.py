"""
HeartBeat Engine - Roster Sync to Pinecone
Syncs NHL roster data to Pinecone for fast player-team lookups
"""

import pandas as pd
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

try:
    from pinecone.grpc import PineconeGRPC as Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    logger.error("Pinecone SDK not available")
    PINECONE_AVAILABLE = False

def load_roster_data() -> pd.DataFrame:
    """Load latest NHL roster data"""
    roster_path = "data/processed/rosters/nhl_rosters_latest.parquet"
    
    if not os.path.exists(roster_path):
        raise FileNotFoundError(f"Roster file not found: {roster_path}")
    
    df = pd.read_parquet(roster_path)
    logger.info(f"Loaded {len(df)} players from roster data")
    return df

def prepare_roster_vectors(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert roster data to Pinecone-ready vectors"""
    vectors = []
    
    for _, row in df.iterrows():
        # Create rich text content for semantic search
        content_parts = [
            f"{row['full_name']} plays for {row['team_abbrev']}",
            f"Position: {row['position']}",
            f"Number: {row['sweater']}" if pd.notna(row['sweater']) else "",
            f"Status: {row['status']}" if pd.notna(row['status']) else ""
        ]
        
        content = ". ".join(filter(None, content_parts))
        
        vector = {
            "id": f"player-{row['nhl_player_id']}",
            "content": content,
            "full_name": row['full_name'],
            "first_name": row['first_name'],
            "last_name": row['last_name'],
            "team_abbrev": row['team_abbrev'],
            "position": row['position'],
            "sweater": str(row['sweater']) if pd.notna(row['sweater']) else "",
            "nhl_player_id": str(row['nhl_player_id']),
            "status": str(row['status']) if pd.notna(row['status']) else "active",
            "season": row['season'],
            "type": "player_roster",
            "sync_date": row['sync_date']
        }
        
        vectors.append(vector)
    
    logger.info(f"Prepared {len(vectors)} roster vectors")
    return vectors

def sync_to_pinecone(vectors: List[Dict[str, Any]], namespace: str = "rosters"):
    """Upload roster vectors to Pinecone using MCP upsert-records"""
    
    # Use MCP client directly
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from orchestrator.tools.pinecone_mcp_client import PineconeMCPClient
        
        # Initialize MCP client
        client = PineconeMCPClient()
        
        if not client.pinecone_index:
            logger.error("Pinecone client not initialized")
            return False
        
        # Upsert in batches of 100
        batch_size = 100
        total_synced = 0
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            
            # Prepare records with metadata
            records = []
            for v in batch:
                # Content goes in metadata for integrated embedding
                metadata = {
                    "content": v["content"],
                    "full_name": v["full_name"],
                    "first_name": v["first_name"],
                    "last_name": v["last_name"],
                    "team_abbrev": v["team_abbrev"],
                    "position": v["position"],
                    "sweater": v["sweater"],
                    "nhl_player_id": v["nhl_player_id"],
                    "status": v["status"],
                    "season": v["season"],
                    "type": v["type"],
                    "sync_date": v["sync_date"]
                }
                
                records.append({
                    "id": v["id"],
                    "metadata": metadata
                })
            
            # Upsert batch
            client.pinecone_index.upsert(
                vectors=records,
                namespace=namespace
            )
            
            total_synced += len(batch)
            logger.info(f"Synced batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1} ({total_synced}/{len(vectors)} players)")
        
        logger.info(f"✓ Successfully synced {len(vectors)} players to Pinecone namespace '{namespace}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync to Pinecone: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("========================================")
    print("ROSTER SYNC TO PINECONE")
    print("========================================\n")
    
    try:
        # Load roster data
        print("[1/3] Loading roster data...")
        df = load_roster_data()
        print(f"✓ Loaded {len(df)} players\n")
        
        # Prepare vectors
        print("[2/3] Preparing vectors...")
        vectors = prepare_roster_vectors(df)
        print(f"✓ Prepared {len(vectors)} vectors\n")
        
        # Sync to Pinecone
        print("[3/3] Syncing to Pinecone...")
        success = sync_to_pinecone(vectors)
        
        if success:
            print("\n✓ Roster sync complete!")
            print(f"  - {len(vectors)} players indexed")
            print(f"  - Namespace: 'rosters'")
            print(f"  - Index: 'heartbeat-unified-index'")
        else:
            print("\n✗ Roster sync failed - check logs")
            return 1
        
        print("\n========================================")
        return 0
        
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        print(f"\n✗ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())

