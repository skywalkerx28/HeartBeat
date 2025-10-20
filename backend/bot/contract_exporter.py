"""
Contract Data CSV Exporter
Exports scraped contract data to CSV files for analysis
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Import player mapper for ID resolution
try:
    from .player_mapper import map_player_name_to_id, get_player_info
except ImportError:
    # Fallback if import fails
    def map_player_name_to_id(name, team=None):
        return None
    def get_player_info(name, team=None):
        return None


def export_contract_data_to_csv(player_data: Dict[str, Any], output_dir: str = 'data/contracts') -> Dict[str, str]:
    """
    Export player contract data to CSV files
    
    Args:
        player_data: Dict containing contracts and contract_details
        output_dir: Directory to save CSV files
    
    Returns:
        Dict with paths to created CSV files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get player name for use in CSV content
    player_name = player_data.get('player_name', 'unknown_player')
    
    # Use last name and player ID for filename (no jersey number)
    if player_data.get('last_name') and player_data.get('player_id'):
        # Format: lastname_playerid (e.g., crosby_8471675)
        safe_name = f"{player_data['last_name'].lower()}_{player_data['player_id']}"
    else:
        # Fallback to original name if mapping failed
        # Remove jersey number from name (e.g., Sidney#87 Crosby -> sidney_crosby)
        import re
        clean_name = re.sub(r'#\d+\w*', '', player_name)
        safe_name = clean_name.replace(' ', '_').replace(',', '').lower().strip('_')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    file_paths = {}
    
    # Export contracts
    if player_data.get('contracts'):
        contracts_file = output_path / f"{safe_name}_contracts_{timestamp}.csv"
        
        with open(contracts_file, 'w', newline='', encoding='utf-8') as f:
            contracts = player_data['contracts']
            if contracts:
                fieldnames = [
                    'player_name', 'contract_type', 'team_code', 'signing_date',
                    'signed_by', 'length_years', 'total_value', 'expiry_status',
                    'cap_hit', 'cap_percent', 'source_url'
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for contract in contracts:
                    row = {k: contract.get(k) for k in fieldnames}
                    writer.writerow(row)
        
        file_paths['contracts'] = str(contracts_file)
        logger.info(f"Exported {len(contracts)} contracts to {contracts_file}")
    
    # Export contract details
    if player_data.get('contract_details'):
        details_file = output_path / f"{safe_name}_contract_details_{timestamp}.csv"
        
        with open(details_file, 'w', newline='', encoding='utf-8') as f:
            details = player_data['contract_details']
            if details:
                fieldnames = [
                    'season', 'clause', 'cap_hit', 'cap_percent', 'aav',
                    'performance_bonuses', 'signing_bonuses', 'base_salary', 'total_salary', 'minors_salary'
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for detail in details:
                    row = {k: detail.get(k) for k in fieldnames}
                    writer.writerow(row)
        
        file_paths['contract_details'] = str(details_file)
        logger.info(f"Exported {len(details)} contract details to {details_file}")
    
    # Career stats export removed - focusing only on contract data
    
    # Create a combined summary CSV
    summary_file = output_path / f"{safe_name}_summary_{timestamp}.csv"
    
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        writer.writerow(['PLAYER CONTRACT SUMMARY'])
        writer.writerow(['Player Name', player_name])
        
        # Add NHL player ID if available
        if player_data.get('player_id'):
            writer.writerow(['NHL Player ID', player_data['player_id']])
        if player_data.get('official_name'):
            writer.writerow(['Official Name', player_data['official_name']])
        if player_data.get('current_team'):
            writer.writerow(['Current Team', player_data['current_team']])
        if player_data.get('position'):
            writer.writerow(['Position', player_data['position']])
        if player_data.get('sweater_number'):
            writer.writerow(['Number', f"#{player_data['sweater_number']}"])
        
        writer.writerow(['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        writer.writerow(['DATA SUMMARY'])
        writer.writerow(['Total Contracts', len(player_data.get('contracts', []))])
        writer.writerow(['Total Contract Details', len(player_data.get('contract_details', []))])
        writer.writerow([])
        
        # Contracts summary
        if player_data.get('contracts'):
            writer.writerow(['CONTRACTS'])
            writer.writerow(['Type', 'Team', 'Signing Date', 'Length (Years)', 'Total Value', 'Cap Hit', 'Expiry Status'])
            
            for contract in player_data['contracts']:
                writer.writerow([
                    contract.get('contract_type'),
                    contract.get('team_code'),
                    contract.get('signing_date'),
                    contract.get('length_years'),
                    contract.get('total_value'),
                    contract.get('cap_hit'),
                    contract.get('expiry_status')
                ])
            writer.writerow([])
        
        # Contract details year-by-year
        if player_data.get('contract_details'):
            writer.writerow(['CONTRACT DETAILS - YEAR BY YEAR'])
            writer.writerow(['Season', 'Clause', 'Cap Hit', 'Cap %', 'AAV', 'Performance Bonuses', 'Signing Bonuses', 'Base Salary', 'Total Salary', 'Minors Salary'])
            
            for detail in player_data['contract_details']:
                writer.writerow([
                    detail.get('season'),
                    detail.get('clause', '-'),
                    f"${detail.get('cap_hit'):,}" if detail.get('cap_hit') else '-',
                    f"{detail.get('cap_percent')}%" if detail.get('cap_percent') else '-',
                    f"${detail.get('aav'):,}" if detail.get('aav') else '-',
                    f"${detail.get('performance_bonuses'):,}" if detail.get('performance_bonuses') else '$0',
                    f"${detail.get('signing_bonuses'):,}" if detail.get('signing_bonuses') else '$0',
                    f"${detail.get('base_salary'):,}" if detail.get('base_salary') else '-',
                    f"${detail.get('total_salary'):,}" if detail.get('total_salary') else '-',
                    f"${detail.get('minors_salary'):,}" if detail.get('minors_salary') else '-'
                ])
            writer.writerow([])
        
        # Career stats section removed - focusing only on contract data
    
    file_paths['summary'] = str(summary_file)
    logger.info(f"Exported summary to {summary_file}")
    
    return file_paths


def export_to_database_and_csv(player_slug: str, output_dir: str = 'data/contracts') -> Dict[str, Any]:
    """
    Scrape player data, save to database, and export to CSV
    
    Args:
        player_slug: Player URL slug (e.g., 'sidney-crosby')
        output_dir: Directory to save CSV files
    
    Returns:
        Dict with database IDs and CSV file paths
    """
    from . import scrapers, db
    
    # Scrape player data
    logger.info(f"Scraping contract data for {player_slug}...")
    player_data = scrapers.scrape_capwages_player_profile(player_slug)
    
    if not player_data.get('player_name'):
        logger.error(f"Failed to scrape data for {player_slug}")
        return {'success': False, 'error': 'No data scraped'}
    
    # Map player name to NHL player ID
    player_name = player_data['player_name']
    team_code = None
    
    # Try to get team from first contract
    if player_data.get('contracts'):
        team_code = player_data['contracts'][0].get('team_code')
    
    # Get NHL player ID and full player info
    nhl_player_id = map_player_name_to_id(player_name, team_code)
    nhl_player_info = get_player_info(player_name, team_code)
    
    if nhl_player_id:
        logger.info(f"Mapped '{player_name}' to NHL Player ID: {nhl_player_id}")
        player_data['player_id'] = nhl_player_id
        
        if nhl_player_info:
            # Enrich with official NHL data
            player_data['official_name'] = nhl_player_info['name']
            player_data['first_name'] = nhl_player_info['firstName']
            player_data['last_name'] = nhl_player_info['lastName']
            player_data['current_team'] = nhl_player_info.get('currentTeam') or nhl_player_info.get('team')
            player_data['position'] = nhl_player_info['position']
            player_data['sweater_number'] = nhl_player_info.get('sweaterNumber')
    else:
        logger.warning(f"Could not map '{player_name}' to NHL Player ID")
        player_data['player_id'] = None
    
    result = {
        'success': True,
        'player_name': player_data['player_name'],
        'player_id': player_data.get('player_id'),
        'official_name': player_data.get('official_name'),
        'contract_ids': [],
        'detail_ids': [],
        'csv_files': {}
    }
    
    # Store in database
    with db.get_connection() as conn:
        # Store contracts
        for contract in player_data.get('contracts', []):
            # Enrich contract with player_id (convert to string for VARCHAR field)
            if nhl_player_id:
                contract['player_id'] = str(nhl_player_id)
            contract_id = db.insert_player_contract(conn, contract)
            if contract_id:
                result['contract_ids'].append(contract_id)
                
                # Store contract details with contract_id
                for detail in player_data.get('contract_details', []):
                    detail['contract_id'] = contract_id
                    detail_id = db.insert_contract_detail(conn, detail)
                    if detail_id:
                        result['detail_ids'].append(detail_id)
        
        # Career stats storage removed - focusing only on contract data
    
    logger.info(f"Stored in database: {len(result['contract_ids'])} contracts, "
                f"{len(result['detail_ids'])} contract details")
    
    # Export to CSV
    csv_files = export_contract_data_to_csv(player_data, output_dir)
    result['csv_files'] = csv_files
    
    logger.info(f"Export complete for {player_data['player_name']}")
    logger.info(f"CSV files: {list(csv_files.values())}")
    
    return result

