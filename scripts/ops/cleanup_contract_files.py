#!/usr/bin/env python3
"""
Contract Files Cleanup
Remove individual contracts and contract_details files, keeping only summaries
"""

import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def cleanup_contract_files(contracts_dir: Path):
    """Remove contracts and contract_details files, keep only summaries"""
    
    stats = {
        'contracts_deleted': 0,
        'details_deleted': 0,
        'summaries_kept': 0,
        'errors': 0
    }
    
    # Get all team folders
    team_folders = [d for d in contracts_dir.iterdir() if d.is_dir()]
    
    logger.info(f"Processing {len(team_folders)} team folders...")
    
    for team_dir in sorted(team_folders):
        team_code = team_dir.name
        
        # Find files to delete
        contracts_files = list(team_dir.glob('*_contracts_*.csv'))
        details_files = list(team_dir.glob('*_contract_details_*.csv'))
        summary_files = list(team_dir.glob('*_summary_*.csv'))
        
        # Delete contracts files
        for file_path in contracts_files:
            try:
                file_path.unlink()
                stats['contracts_deleted'] += 1
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
                stats['errors'] += 1
        
        # Delete contract_details files
        for file_path in details_files:
            try:
                file_path.unlink()
                stats['details_deleted'] += 1
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
                stats['errors'] += 1
        
        # Count summaries kept
        stats['summaries_kept'] += len(summary_files)
        
        logger.info(f"{team_code}: Deleted {len(contracts_files)} contracts, {len(details_files)} details, kept {len(summary_files)} summaries")
    
    return stats


def main():
    """Main execution"""
    logger.info("=" * 70)
    logger.info("CONTRACT FILES CLEANUP")
    logger.info("=" * 70)
    logger.info("Removing individual contracts and contract_details files...")
    logger.info("Keeping only comprehensive summary files")
    logger.info("=" * 70)
    
    contracts_dir = Path('data/contracts')
    
    # Run cleanup
    stats = cleanup_contract_files(contracts_dir)
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("CLEANUP COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Contracts Files Deleted: {stats['contracts_deleted']}")
    logger.info(f"Contract Details Files Deleted: {stats['details_deleted']}")
    logger.info(f"Summary Files Kept: {stats['summaries_kept']}")
    logger.info(f"Errors: {stats['errors']}")
    
    total_deleted = stats['contracts_deleted'] + stats['details_deleted']
    total_kept = stats['summaries_kept']
    
    logger.info(f"\nTotal Files Deleted: {total_deleted}")
    logger.info(f"Total Files Kept: {total_kept}")
    logger.info(f"Space Saved: ~{total_deleted / (total_deleted + total_kept) * 100:.1f}% reduction")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()

