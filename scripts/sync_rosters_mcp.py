"""
HeartBeat Engine - Roster Sync to Pinecone via MCP
Syncs NHL roster data to Pinecone using MCP upsert-records tool
"""

import pandas as pd
import os
import logging
import json
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def load_roster_data() -> pd.DataFrame:
    """Load latest NHL roster data"""
    roster_path = "data/processed/rosters/nhl_rosters_latest.parquet"
    
    if not os.path.exists(roster_path):
        raise FileNotFoundError(f"Roster file not found: {roster_path}")
    
    df = pd.read_parquet(roster_path)
    logger.info(f"Loaded {len(df)} players from roster data")
    return df

def prepare_roster_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert roster data to MCP-ready records"""
    records = []
    
    for _, row in df.iterrows():
        # Create rich text content for semantic search
        content_parts = [
            f"{row['full_name']} plays for {row['team_abbrev']}",
            f"Position: {row['position']}",
            f"Number: {row['sweater']}" if pd.notna(row['sweater']) else "",
            f"Status: {row['status']}" if pd.notna(row['status']) else ""
        ]
        
        content = ". ".join(filter(None, content_parts))
        
        record = {
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
        
        records.append(record)
    
    logger.info(f"Prepared {len(records)} roster records")
    return records

def main():
    """Main execution - output JSON for MCP consumption"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("========================================")
    print("ROSTER SYNC - MCP FORMAT")
    print("========================================\n")
    
    try:
        # Load roster data
        print("[1/2] Loading roster data...")
        df = load_roster_data()
        print(f"✓ Loaded {len(df)} players\n")
        
        # Prepare records
        print("[2/2] Preparing MCP records...")
        records = prepare_roster_records(df)
        print(f"✓ Prepared {len(records)} records\n")
        
        # Write to JSON files in batches
        batch_size = 100
        num_batches = (len(records) + batch_size - 1) // batch_size
        
        output_dir = "data/mcp_sync"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Writing {num_batches} batch files to {output_dir}/")
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            output_file = f"{output_dir}/roster_batch_{batch_num:03d}.json"
            with open(output_file, 'w') as f:
                json.dump(batch, f, indent=2)
            
            print(f"  - Batch {batch_num}/{num_batches}: {len(batch)} records")
        
        print(f"\n✓ All roster data prepared!")
        print(f"\nTo sync to Pinecone, use the MCP tool mcp_pinecone_upsert-records")
        print(f"with each batch file from {output_dir}/")
        
        print("\n========================================")
        return 0
        
    except Exception as e:
        logger.error(f"Preparation failed: {str(e)}")
        print(f"\n✗ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())

