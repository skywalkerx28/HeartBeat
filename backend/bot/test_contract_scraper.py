#!/usr/bin/env python3
"""
Test Contract Scraper
Test the CapWages contract scraper with Sidney Crosby's profile
"""

import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.contract_exporter import export_to_database_and_csv
from bot import db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_sidney_crosby_scrape():
    """Test scraping Sidney Crosby's contract data"""
    
    logger.info("=" * 80)
    logger.info("TESTING CONTRACT SCRAPER WITH SIDNEY CROSBY")
    logger.info("=" * 80)
    
    player_slug = "sidney-crosby"
    output_dir = "data/contracts"
    
    # Run the scraper
    result = export_to_database_and_csv(player_slug, output_dir)
    
    if result.get('success'):
        logger.info("\n" + "=" * 80)
        logger.info("SCRAPE SUCCESSFUL")
        logger.info("=" * 80)
        
        logger.info(f"\nPlayer: {result.get('player_name')}")
        logger.info(f"Contracts stored: {len(result.get('contract_ids', []))}")
        logger.info(f"Contract details stored: {len(result.get('detail_ids', []))}")
        logger.info(f"Career stats stored: {len(result.get('stat_ids', []))}")
        
        logger.info("\nCSV Files Generated:")
        for file_type, file_path in result.get('csv_files', {}).items():
            logger.info(f"  - {file_type}: {file_path}")
        
        # Query and display some data from database
        logger.info("\n" + "=" * 80)
        logger.info("DATABASE VERIFICATION")
        logger.info("=" * 80)
        
        with db.get_connection() as conn:
            # Get contracts
            contracts = db.get_player_contracts(conn, result.get('player_name'))
            logger.info(f"\nContracts found in database: {len(contracts)}")
            
            for i, contract in enumerate(contracts, 1):
                logger.info(f"\n  Contract {i}:")
                logger.info(f"    Type: {contract.get('contract_type')}")
                logger.info(f"    Team: {contract.get('team_code')}")
                logger.info(f"    Signing Date: {contract.get('signing_date')}")
                logger.info(f"    Length: {contract.get('length_years')} years")
                logger.info(f"    Total Value: ${contract.get('total_value'):,}" if contract.get('total_value') else "    Total Value: N/A")
                logger.info(f"    Cap Hit: ${contract.get('cap_hit'):,}" if contract.get('cap_hit') else "    Cap Hit: N/A")
                logger.info(f"    Expiry Status: {contract.get('expiry_status')}")
                
                # Get contract details for this contract
                if contract.get('id'):
                    details = db.get_contract_details(conn, contract['id'])
                    logger.info(f"    Yearly Details: {len(details)} seasons")
            
            # Get career stats
            career_stats = db.get_player_career_stats(conn, result.get('player_name'))
            logger.info(f"\nCareer stats entries: {len(career_stats)}")
            
            if career_stats:
                logger.info("\n  Sample stats (last 5 seasons):")
                for stat in career_stats[-5:]:
                    logger.info(f"    {stat.get('season')} {stat.get('team_code')}: "
                              f"{stat.get('games_played')}GP, {stat.get('goals')}G, "
                              f"{stat.get('assists')}A, {stat.get('points')}P"
                              f"{' (Playoffs)' if stat.get('is_playoffs') else ''}")
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        return True
        
    else:
        logger.error("\n" + "=" * 80)
        logger.error("SCRAPE FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {result.get('error')}")
        return False


if __name__ == "__main__":
    try:
        success = test_sidney_crosby_scrape()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception(f"Test failed with exception: {e}")
        sys.exit(1)

