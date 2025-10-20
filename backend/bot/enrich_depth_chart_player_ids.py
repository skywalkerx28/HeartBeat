"""
Enrich depth chart player IDs from contract database

This script:
1. Reads all depth chart CSVs
2. Identifies players without player_id
3. Matches them with contract database by name
4. Updates depth chart CSVs and database with found player_ids

Usage:
    python -m backend.bot.enrich_depth_chart_player_ids
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import re

from . import db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_player_name(name: str) -> str:
    """
    Normalize player name for matching
    
    Examples:
        "Beck, Owen" -> "owen beck"
        "O'Reilly, Ryan" -> "oreilly ryan"
    """
    # Handle "Last, First" format
    if ',' in name:
        parts = name.split(',')
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ''
        name = f"{first_name} {last_name}"
    
    # Lowercase
    name = name.lower()
    
    # Remove special characters
    name = re.sub(r"['\-\.]", '', name)
    
    # Normalize whitespace
    name = ' '.join(name.split())
    
    return name


def get_player_id_from_contracts(player_name: str, team_code: str = None) -> Tuple[int, str]:
    """
    Look up player ID from contract database
    
    Args:
        player_name: Player name from depth chart
        team_code: Optional team filter
    
    Returns:
        (player_id, source) tuple or (None, None)
    """
    with db.get_connection(read_only=True) as conn:
        normalized_search = normalize_player_name(player_name)
        
        # Try exact match first
        query = """
            SELECT DISTINCT player_id, player_name
            FROM player_contracts
            WHERE LOWER(REPLACE(REPLACE(REPLACE(player_name, '-', ''), '.', ''), '''', '')) = ?
                AND player_id IS NOT NULL
                AND player_id != ''
        """
        params = [normalized_search]
        
        if team_code:
            query += " AND team_code = ?"
            params.append(team_code)
        
        result = conn.execute(query, params).fetchone()
        
        if result and result[0]:
            return int(result[0]) if result[0].isdigit() else result[0], 'contract_exact'
        
        # Try fuzzy match on last name
        name_parts = normalized_search.split()
        if len(name_parts) >= 2:
            last_name = name_parts[-1]
            
            query = """
                SELECT DISTINCT player_id, player_name
                FROM player_contracts
                WHERE LOWER(REPLACE(REPLACE(REPLACE(player_name, '-', ''), '.', ''), '''', '')) LIKE ?
                    AND player_id IS NOT NULL
                    AND player_id != ''
            """
            params = [f'%{last_name}%']
            
            if team_code:
                query += " AND team_code = ?"
                params.append(team_code)
            
            results = conn.execute(query, params).fetchall()
            
            # Check for best match
            for row in results:
                contract_name_normalized = normalize_player_name(row[1])
                if normalized_search in contract_name_normalized or contract_name_normalized in normalized_search:
                    return int(row[0]) if str(row[0]).isdigit() else row[0], 'contract_fuzzy'
    
    return None, None


def enrich_depth_charts_from_contracts() -> Dict:
    """
    Enrich all depth chart CSVs with player IDs from contract database
    
    Returns:
        Summary dict with statistics
    """
    depth_charts_dir = Path('data/depth_charts')
    
    if not depth_charts_dir.exists():
        logger.error(f"Depth charts directory not found: {depth_charts_dir}")
        return {'success': False, 'error': 'Directory not found'}
    
    stats = {
        'total_files': 0,
        'total_players': 0,
        'players_without_id': 0,
        'players_enriched': 0,
        'players_still_missing': 0,
        'by_team': {}
    }
    
    # Process each team's depth chart
    csv_files = sorted(depth_charts_dir.glob('*_depth_chart_*.csv'))
    
    for csv_file in csv_files:
        team_code = csv_file.stem.split('_')[0]
        logger.info(f"Processing {team_code}...")
        
        stats['total_files'] += 1
        team_stats = {
            'total': 0,
            'without_id': 0,
            'enriched': 0,
            'still_missing': 0
        }
        
        # Read CSV
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            for row in reader:
                stats['total_players'] += 1
                team_stats['total'] += 1
                
                player_name = row.get('player_name', '')
                player_id = row.get('player_id', '').strip()
                
                # If no player_id, try to find it in contracts
                if not player_id and player_name:
                    stats['players_without_id'] += 1
                    team_stats['without_id'] += 1
                    
                    # Look up in contract database
                    found_id, source = get_player_id_from_contracts(player_name, team_code)
                    
                    if found_id:
                        row['player_id'] = str(found_id)
                        stats['players_enriched'] += 1
                        team_stats['enriched'] += 1
                        logger.info(f"  ✓ {player_name}: {found_id} (source: {source})")
                        
                        # Update database as well
                        update_database_player_id(team_code, player_name, found_id)
                    else:
                        stats['players_still_missing'] += 1
                        team_stats['still_missing'] += 1
                        logger.debug(f"  ✗ {player_name}: No match found")
                
                rows.append(row)
        
        # Write updated CSV
        if team_stats['enriched'] > 0:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"  Updated {csv_file.name} with {team_stats['enriched']} new player IDs")
        
        stats['by_team'][team_code] = team_stats
    
    return stats


def update_database_player_id(team_code: str, player_name: str, player_id: int):
    """
    Update player_id in the depth chart database
    
    Args:
        team_code: Team code (e.g., 'MTL')
        player_name: Player name to match
        player_id: NHL player ID to set
    """
    try:
        with db.get_connection() as conn:
            # Update all matching records (including historical snapshots)
            conn.execute("""
                UPDATE team_rosters
                SET player_id = ?
                WHERE team_code = ?
                    AND player_name = ?
                    AND (player_id IS NULL OR player_id = '')
            """, [str(player_id), team_code, player_name])
            
            conn.commit()
            logger.debug(f"  Updated database: {player_name} -> {player_id}")
    except Exception as e:
        logger.warning(f"  Failed to update database for {player_name}: {e}")


def main():
    logger.info("="*80)
    logger.info("Depth Chart Player ID Enrichment from Contracts")
    logger.info("="*80)
    logger.info("")
    
    # Run enrichment
    stats = enrich_depth_charts_from_contracts()
    
    if not stats.get('success', True):
        logger.error(f"Enrichment failed: {stats.get('error')}")
        return
    
    # Print summary
    logger.info("="*80)
    logger.info("ENRICHMENT COMPLETE")
    logger.info("="*80)
    logger.info(f"Files processed: {stats['total_files']}")
    logger.info(f"Total players: {stats['total_players']}")
    logger.info(f"Players without ID initially: {stats['players_without_id']}")
    logger.info(f"Players enriched from contracts: {stats['players_enriched']}")
    logger.info(f"Players still missing ID: {stats['players_still_missing']}")
    logger.info("")
    
    if stats['players_enriched'] > 0:
        logger.info("Top teams with enriched players:")
        enriched_teams = sorted(
            [(k, v['enriched']) for k, v in stats['by_team'].items() if v['enriched'] > 0],
            key=lambda x: x[1],
            reverse=True
        )
        for team, count in enriched_teams[:10]:
            logger.info(f"  {team}: {count} players")
    
    if stats['players_still_missing'] > 0:
        logger.info("")
        logger.info(f"Note: {stats['players_still_missing']} players still don't have IDs")
        logger.info("These are likely unsigned prospects or very recent additions")


if __name__ == '__main__':
    main()

