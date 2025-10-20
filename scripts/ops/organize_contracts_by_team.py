#!/usr/bin/env python3
"""
Organize Contract Files by Team
Move all contract files into team-specific subdirectories
"""

import json
import shutil
import logging
from pathlib import Path
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_roster_mappings(roster_path: str = 'data/processed/rosters/unified_roster_20252026.json'):
    """Load player ID to team mappings from unified roster"""
    with open(roster_path, 'r') as f:
        data = json.load(f)
    
    # Create mapping: player_id -> team_code
    player_to_team = {}
    
    for player in data['players']:
        player_id = str(player['id'])
        team_code = player['team']
        player_to_team[player_id] = team_code
    
    logger.info(f"Loaded mappings for {len(player_to_team)} players")
    
    return player_to_team, data['teams']


def create_team_folders(contracts_dir: Path, teams: list):
    """Create subdirectories for each team"""
    for team in teams:
        team_code = team['code']
        team_dir = contracts_dir / team_code
        team_dir.mkdir(exist_ok=True)
        logger.info(f"Created folder: {team_code}/")
    
    logger.info(f"Created {len(teams)} team folders")


def organize_contract_files(contracts_dir: Path, player_to_team: dict):
    """Move contract files into team-specific folders"""
    
    # Find all contract CSV files (not batch summaries or logs)
    contract_files = [
        f for f in contracts_dir.glob('*.csv') 
        if not f.name.startswith('batch_')
    ]
    
    logger.info(f"Found {len(contract_files)} contract files to organize")
    
    stats = {
        'moved': 0,
        'skipped': 0,
        'errors': 0,
        'by_team': defaultdict(int)
    }
    
    for file_path in contract_files:
        try:
            filename = file_path.name
            
            # Extract player ID from filename
            # Format: lastname_playerid_type_timestamp.csv
            parts = filename.split('_')
            
            if len(parts) < 2:
                logger.warning(f"Skipping file with unexpected format: {filename}")
                stats['skipped'] += 1
                continue
            
            # Player ID is the second part
            player_id = parts[1]
            
            # Look up team
            team_code = player_to_team.get(player_id)
            
            if not team_code:
                logger.warning(f"No team found for player ID {player_id} in {filename}")
                stats['skipped'] += 1
                continue
            
            # Move file to team folder
            team_dir = contracts_dir / team_code
            destination = team_dir / filename
            
            if destination.exists():
                logger.debug(f"File already exists: {destination.name}")
            
            shutil.move(str(file_path), str(destination))
            stats['moved'] += 1
            stats['by_team'][team_code] += 1
            
            if stats['moved'] % 100 == 0:
                logger.info(f"Progress: {stats['moved']} files organized...")
        
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            stats['errors'] += 1
    
    return stats


def main():
    """Main execution"""
    logger.info("=" * 70)
    logger.info("ORGANIZING CONTRACT FILES BY TEAM")
    logger.info("=" * 70)
    
    # Load roster mappings
    player_to_team, teams = load_roster_mappings()
    
    # Setup directories
    contracts_dir = Path('data/contracts')
    
    # Create team folders
    create_team_folders(contracts_dir, teams)
    
    # Organize files
    logger.info("\nOrganizing contract files...")
    stats = organize_contract_files(contracts_dir, player_to_team)
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("ORGANIZATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Files Moved: {stats['moved']}")
    logger.info(f"Files Skipped: {stats['skipped']}")
    logger.info(f"Errors: {stats['errors']}")
    
    logger.info("\nFILES PER TEAM:")
    logger.info("-" * 70)
    
    for team_code in sorted(stats['by_team'].keys()):
        count = stats['by_team'][team_code]
        logger.info(f"{team_code:5s}: {count:4d} files")
    
    logger.info("=" * 70)
    logger.info("All contract files organized into team folders!")


if __name__ == '__main__':
    main()

