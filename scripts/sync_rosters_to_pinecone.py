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
    from pinecone_plugins.inference.models import EmbedModel
    PINECONE_AVAILABLE = True
    INFERENCE_AVAILABLE = True
except ImportError:
    try:
        from pinecone.grpc import PineconeGRPC as Pinecone
        PINECONE_AVAILABLE = True
        INFERENCE_AVAILABLE = False
    except ImportError:
        logger.error("Pinecone SDK not available")
        PINECONE_AVAILABLE = False
        INFERENCE_AVAILABLE = False

def load_roster_data() -> pd.DataFrame:
    """Load latest NHL roster data"""
    roster_path = "data/processed/rosters/nhl_rosters_latest.parquet"
    
    if not os.path.exists(roster_path):
        raise FileNotFoundError(f"Roster file not found: {roster_path}")
    
    df = pd.read_parquet(roster_path)
    logger.info(f"Loaded {len(df)} players from roster data")
    return df

def _make_aliases(row: pd.Series) -> List[str]:
    """Generate alias strings to improve typo and nickname recall."""
    import re
    first = str(row.get('first_name', '') or '').strip()
    last = str(row.get('last_name', '') or '').strip()
    full = str(row.get('full_name', '') or '').strip()
    team = str(row.get('team_abbrev', '') or '').strip()
    sweater = str(row.get('sweater')) if pd.notna(row.get('sweater')) else ''

    aliases = set()
    def norm(s: str) -> str:
        s = re.sub(r"[^A-Za-z\s]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s
    def slug(s: str) -> str:
        return re.sub(r"[^a-z]", "", s.lower())

    if full:
        aliases.add(norm(full))
        aliases.add(slug(full))
    if first and last:
        aliases.add(norm(f"{first} {last}"))
        aliases.add(slug(f"{first}{last}"))
        aliases.add(norm(f"{first[0]} {last}"))
        aliases.add(slug(f"{first[0]}{last}"))
        aliases.add(norm(last))
    if sweater and last:
        aliases.add(norm(f"{last} #{sweater}"))
    if team and last:
        aliases.add(norm(f"{last} {team}"))

    # Common nickname mapping (extensible)
    nickmap = {
        'nicholas': 'nick',
        'michael': 'mike',
        'jonathan': 'john',
    }
    low_first = first.lower()
    if low_first in nickmap:
        nn = nickmap[low_first]
        aliases.add(norm(f"{nn} {last}"))
        aliases.add(slug(f"{nn}{last}"))

    return [a for a in aliases if a]


def prepare_roster_vectors(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert roster data to Pinecone-ready vectors"""
    vectors = []
    
    for _, row in df.iterrows():
        # Create rich text content for semantic search
        aliases = _make_aliases(row)
        content_parts = [
            f"{row['full_name']} plays for {row['team_abbrev']}",
            f"Position: {row['position']}",
            f"Number: {row['sweater']}" if pd.notna(row['sweater']) else "",
            f"Status: {row['status']}" if pd.notna(row['status']) else "",
            f"Aliases: {'; '.join(aliases)}" if aliases else ""
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
            "sync_date": row['sync_date'],
            "aliases": aliases,
            "slug": (row['first_name'] + row['last_name']).lower() if pd.notna(row['first_name']) and pd.notna(row['last_name']) else ""
        }
        
        vectors.append(vector)
    
    logger.info(f"Prepared {len(vectors)} roster vectors")
    return vectors

def sync_to_pinecone(vectors: List[Dict[str, Any]], namespace: str = "rosters"):
    """Upload roster vectors to Pinecone using Pinecone library directly"""
    
    if not PINECONE_AVAILABLE:
        logger.error("Pinecone library not installed")
        return False
    
    try:
        # Initialize Pinecone client
        api_key = os.getenv("PINECONE_API_KEY", "pcsk_44JqgP_2oVeUVWd9Lk8MRrinaoKoZEYjJueDm1kEXhpJQiWCruWvJ58oyQVWSq5h7Cd3po")
        pc = Pinecone(api_key=api_key)
        
        # Get the index
        index_name = "heartbeat-unified-index"
        index = pc.Index(index_name)
        
        logger.info(f"Connected to Pinecone index: {index_name}")
        
        # Use Pinecone's embed endpoint for integrated inference
        from pinecone import Pinecone as PineconeREST
        pc_rest = PineconeREST(api_key=api_key)
        
        logger.info(f"Starting embedding and sync process...")
        
        # Upsert in batches of 90 (multilingual-e5-large has 96 input limit, use 90 for safety)
        batch_size = 90
        total_synced = 0
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            
            # Generate embeddings for this batch
            batch_contents = [v["content"] for v in batch]
            embeddings_response = pc_rest.inference.embed(
                model="multilingual-e5-large",
                inputs=batch_contents,
                parameters={"input_type": "passage", "truncate": "END"}
            )
            
            # Prepare records with embeddings and metadata
            records = []
            for idx, v in enumerate(batch):
                embedding_vector = embeddings_response.data[idx].values
                
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
                    "sync_date": v["sync_date"],
                    "aliases": v["aliases"],  # Include aliases in metadata
                    "slug": v["slug"]  # Include slug for fast matching
                }
                
                records.append({
                    "id": v["id"],
                    "values": embedding_vector,
                    "metadata": metadata
                })
            
            # Upsert batch to Pinecone
            index.upsert(
                vectors=records,
                namespace=namespace
            )
            
            total_synced += len(batch)
            logger.info(f"Synced batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1} ({total_synced}/{len(vectors)} players)")
        
        logger.info(f"Successfully synced {len(vectors)} players to Pinecone namespace '{namespace}'")
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
