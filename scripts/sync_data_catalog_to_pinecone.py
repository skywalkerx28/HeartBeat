"""
HeartBeat Engine - Data Catalog Sync to Pinecone
Creates a searchable catalog of available data sources and schemas
"""

import os
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from pinecone.grpc import PineconeGRPC as Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    logger.error("Pinecone SDK not available")
    PINECONE_AVAILABLE = False

def create_catalog_entries() -> List[Dict[str, Any]]:
    """Create data catalog entries for Pinecone"""
    
    catalog = [
        {
            "id": "catalog-rosters",
            "content": "NHL player rosters with current team affiliations. Use for questions about what team a player is on, player positions, jersey numbers, and roster status. Query rosters namespace in Pinecone or data/processed/rosters/nhl_rosters_latest.parquet",
            "data_source": "rosters",
            "query_types": ["player_team", "roster_lookup", "position_info"],
            "example_queries": [
                "What team is X on?",
                "Show me Montreal's roster",
                "What position does X play?"
            ],
            "type": "data_catalog"
        },
        {
            "id": "catalog-pbp",
            "content": "Play-by-play events with shot coordinates, xG values, player on-ice, zone info. Use for detailed event analysis, shot charts, possession analysis. Query data/processed/fact/pbp/unified_pbp_2024-25.parquet with filters for game_id, player_id, event_type",
            "data_source": "play_by_play",
            "query_types": ["event_analysis", "shot_charts", "possession"],
            "parquet_path": "data/processed/fact/pbp/",
            "key_columns": ["game_id", "player_id", "event_type", "x_coord", "y_coord", "xg", "period", "strength", "zone"],
            "type": "data_catalog"
        },
        {
            "id": "catalog-team-stats",
            "content": "Montreal Canadiens team statistics including shooting, passing, zone entries/exits, defensive metrics. Use for team performance analysis. Multiple parquet files organized by category in data/processed/analytics/mtl_team_stats/",
            "data_source": "team_stats",
            "query_types": ["team_performance", "tactical_analysis"],
            "parquet_path": "data/processed/analytics/mtl_team_stats/",
            "categories": ["shooting", "passing", "dz", "oz", "nz", "playmaking"],
            "type": "data_catalog"
        },
        {
            "id": "catalog-matchup-reports",
            "content": "Head-to-head matchup analysis between Montreal and opponents. Use for opponent analysis, tactical comparisons. Query data/processed/analytics/mtl_matchup_reports/unified_matchup_reports_2024_2025.parquet",
            "data_source": "matchup_reports",
            "query_types": ["opponent_analysis", "head_to_head"],
            "parquet_path": "data/processed/analytics/mtl_matchup_reports/",
            "type": "data_catalog"
        },
        {
            "id": "catalog-game-recaps",
            "content": "Game summaries with final scores, key players, shot totals, and pointers to detailed play-by-play data. Use for quick game results and navigation to detailed analysis. Available in Pinecone 'events' namespace",
            "data_source": "game_recaps",
            "query_types": ["game_results", "season_summary"],
            "namespace": "events",
            "type": "data_catalog"
        },
        {
            "id": "routing-simple-lookups",
            "content": "For simple lookup questions (player teams, metric definitions, game results), use Pinecone RAG only. Fast retrieval under 100ms. No need for Parquet queries.",
            "routing_rule": "rag_only",
            "applies_to": ["player_team", "metric_definition", "game_result_simple"],
            "type": "routing_hint"
        },
        {
            "id": "routing-detailed-stats",
            "content": "For detailed statistics and aggregations (player averages, team trends, zone analysis), use Parquet queries after RAG lookup identifies relevant players/games. Expected latency 200-500ms.",
            "routing_rule": "rag_then_parquet",
            "applies_to": ["player_stats", "team_trends", "aggregation_queries"],
            "type": "routing_hint"
        },
        {
            "id": "routing-complex-analysis",
            "content": "For complex multi-step analysis (comparative analysis, trend identification, tactical insights), combine RAG context + multiple Parquet queries + LLM synthesis. Expected latency 2-5s.",
            "routing_rule": "hybrid_complex",
            "applies_to": ["tactical_analysis", "multi_player_comparison", "strategic_insights"],
            "type": "routing_hint"
        },
        {
            "id": "season-info-2024-25",
            "content": "2024-25 NHL season. Montreal Canadiens games available. Use game_id range 20001-21312 for season. Season started October 2024.",
            "season": "2024-25",
            "game_count": 82,
            "type": "season_metadata"
        },
        {
            "id": "team-mtl-info",
            "content": "Montreal Canadiens team abbreviation: MTL. Home arena: Bell Centre. Use team_abbrev='MTL' in queries. Key players include Suzuki (captain), Caufield, Slafkovsky, Hutson, Matheson, Demidov (prospect).",
            "team": "Montreal Canadiens",
            "abbrev": "MTL",
            "type": "team_metadata"
        }
    ]
    
    return catalog

def sync_catalog_to_pinecone(catalog: List[Dict[str, Any]], namespace: str = "catalog"):
    """Upload catalog to Pinecone"""
    
    if not PINECONE_AVAILABLE:
        logger.error("Cannot sync - Pinecone SDK not available")
        return False
    
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        logger.error("PINECONE_API_KEY not set")
        return False
    
    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index("heartbeat-unified-index")
        
        # Prepare records
        records = []
        for entry in catalog:
            metadata = {k: v for k, v in entry.items() if k not in ['id', 'content']}
            records.append({
                "_id": entry["id"],
                **metadata
            })
        
        # Upsert to Pinecone
        index.upsert(vectors=records, namespace=namespace)
        
        logger.info(f"✓ Synced {len(catalog)} catalog entries to namespace '{namespace}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync catalog: {str(e)}")
        return False

def main():
    """Main execution"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("========================================")
    print("DATA CATALOG SYNC TO PINECONE")
    print("========================================\n")
    
    try:
        print("[1/2] Creating catalog entries...")
        catalog = create_catalog_entries()
        print(f"✓ Created {len(catalog)} catalog entries\n")
        
        print("[2/2] Syncing to Pinecone...")
        success = sync_catalog_to_pinecone(catalog)
        
        if success:
            print("\n✓ Catalog sync complete!")
            print(f"  - {len(catalog)} entries indexed")
            print(f"  - Namespace: 'catalog'")
            print(f"  - Includes: data sources, routing hints, metadata")
        else:
            print("\n✗ Catalog sync failed")
            return 1
        
        print("\n========================================")
        return 0
        
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        print(f"\n✗ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())

