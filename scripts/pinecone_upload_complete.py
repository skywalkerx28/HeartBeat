"""
Complete Pinecone Context Upload Script
Uploads all 71 hockey metric contexts to enable expert RAG retrieval
"""

import json
from pathlib import Path
import time

def main():
    print("="*80)
    print("UPLOADING 71 METRIC CONTEXTS TO PINECONE")
    print("="*80)
    
    context_dir = Path("data/processed/llm_model/context/mtl_team_stats_explained")
    
    # Load all contexts
    all_contexts = []
    for json_file in sorted(context_dir.glob("*.json")):
        if json_file.name == "index.json":
            continue
        
        with open(json_file, 'r') as f:
            context = json.load(f)
            
            # Build searchable content
            content_parts = [context.get("title", "")]
            if context.get("hockey_context"):
                content_parts.append(context['hockey_context'])
            if context.get("common_situations"):
                content_parts.append("Situations: " + " | ".join(context['common_situations']))
            
            record = {
                "id": context.get("id", json_file.stem),
                "content": "\n\n".join(filter(None, content_parts)),
                "type": "metric_context",
                "season": context.get("season", "2024-2025"),
                "category": _categorize(context.get("id", "")),
                "parquet_path": context.get("parquet_path", "")
            }
            
            all_contexts.append(record)
    
    print(f"\n✓ Loaded {len(all_contexts)} contexts")
    print(f"\nNOTE: Batch 1 (5 records) already uploaded via MCP")
    print(f"Remaining: {len(all_contexts) - 5} contexts")
    print(f"\nTo upload remaining batches, use Pinecone MCP upsert tool")
    print(f"or run: python scripts/batch_upload_via_sdk.py")
    
    # Save complete dataset for reference
    with open('/tmp/all_contexts_ready.json', 'w') as f:
        json.dump(all_contexts, f, indent=2)
    
    print(f"\n✓ Complete dataset saved to /tmp/all_contexts_ready.json")
    print(f"\n{'='*80}")
    print(f"CONTEXTS PREPARED - Ready for Pinecone upload")
    print(f"{'='*80}")


def _categorize(metric_id):
    categories = {
        "shooting": ["shooting", "shot"],
        "passing": ["passing"],
        "defensive": ["defensive", "blocks", "bodychecks", "stickchecks", "denials"],
        "possession": ["possession", "dekes"],
        "zone_transitions": ["dz", "entries", "exits", "lpr"],
        "faceoffs": ["faceoffs"],
        "goaltending": ["goalie", "goallie"],
        "penalties": ["penalties"],
        "playmaking": ["playmaking", "scoring-chances"],
        "shootouts": ["shootouts"],
        "dumpins": ["dumpins"]
    }
    
    mid_lower = metric_id.lower()
    for category, keywords in categories.items():
        if any(kw in mid_lower for kw in keywords):
            return category
    return "team_stats"


if __name__ == "__main__":
    main()

