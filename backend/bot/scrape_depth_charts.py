"""
Manual script to scrape NHL team depth charts from CapWages
Run this script directly to populate team rosters in the database

Usage:
    # Scrape a single team
    python -m backend.bot.scrape_depth_charts --team VGK
    
    # Scrape all 32 teams
    python -m backend.bot.scrape_depth_charts --all
    
    # Scrape specific teams
    python -m backend.bot.scrape_depth_charts --teams VGK MTL TOR
"""

import argparse
import logging
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import scrapers, db, player_enrichment
from .config import NHL_TEAMS, CAPWAGES_TEAM_SLUGS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def export_roster_to_csv(team_code: str, output_dir: str = 'data/depth_charts') -> str:
    """
    Export team roster to CSV file
    
    Args:
        team_code: 3-letter team code
        output_dir: Directory to save CSV files
    
    Returns:
        Path to created CSV file
    """
    team_code = team_code.upper()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get roster data
    with db.get_connection(read_only=True) as conn:
        roster = db.get_team_roster(conn, team_code, latest_only=True)
    
    if not roster:
        logger.warning(f"No roster data found for {team_code}")
        return None
    
    # Generate CSV filename
    scraped_date = roster[0]['scraped_date']
    csv_filename = output_path / f"{team_code}_depth_chart_{scraped_date}.csv"
    
    # Define CSV columns - organizational depth chart with draft info and enrichment
    fieldnames = [
        'player_name',
        'player_id',
        'position',
        'roster_status',
        'dead_cap',
        'jersey_number',
        'age',
        'birth_date',
        'birth_country',
        'height_inches',
        'weight_pounds',
        'shoots_catches',
        'drafted_by',
        'draft_year',
        'draft_round',
        'draft_overall',
        'must_sign_date',
        'headshot'
    ]
    
    # Write to CSV
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for player in roster:
            # Export complete organizational depth chart data with enrichment
            row = {
                'player_name': player.get('player_name'),
                'player_id': player.get('player_id', ''),
                'position': player.get('position'),
                'roster_status': player.get('roster_status'),
                'dead_cap': 'Yes' if player.get('dead_cap') else '',
                'jersey_number': player.get('jersey_number'),
                'age': player.get('age'),
                'birth_date': player.get('birth_date', ''),
                'birth_country': player.get('birth_country', ''),
                'height_inches': player.get('height_inches', ''),
                'weight_pounds': player.get('weight_pounds', ''),
                'shoots_catches': player.get('shoots_catches', ''),
                'drafted_by': player.get('drafted_by', ''),
                'draft_year': player.get('draft_year', ''),
                'draft_round': player.get('draft_round', ''),
                'draft_overall': player.get('draft_overall', ''),
                'must_sign_date': player.get('must_sign_date', ''),
                'headshot': player.get('headshot', '')
            }
            writer.writerow(row)
    
    logger.info(f"Exported roster to: {csv_filename}")
    return str(csv_filename)


def scrape_team_depth_chart(team_code: str, export_csv: bool = True) -> dict:
    """
    Scrape and store depth chart for a single team
    
    Args:
        team_code: 3-letter team code (e.g., 'VGK', 'MTL')
    
    Returns:
        Dict with scrape results
    """
    team_code = team_code.upper()
    
    if team_code not in NHL_TEAMS:
        logger.error(f"Unknown team code: {team_code}")
        return {'success': False, 'error': f'Unknown team code: {team_code}'}
    
    if team_code not in CAPWAGES_TEAM_SLUGS:
        logger.error(f"No CapWages slug mapping for team: {team_code}")
        return {'success': False, 'error': f'No CapWages slug for {team_code}'}
    
    team_slug = CAPWAGES_TEAM_SLUGS[team_code]
    team_name = NHL_TEAMS[team_code]['name']
    
    logger.info(f"Starting depth chart scrape for {team_name} ({team_code})")
    logger.info(f"CapWages URL: https://capwages.com/teams/{team_slug}")
    
    try:
        # Scrape the depth chart
        depth_chart_data = scrapers.scrape_capwages_team_depth_chart(team_slug)
        
        if not depth_chart_data.get('team_code'):
            logger.warning(f"Could not determine team code from scraped data, using: {team_code}")
            depth_chart_data['team_code'] = team_code
        
        # Enrich with unified roster data
        logger.info(f"Enriching player data with unified roster...")
        all_players = (
            depth_chart_data.get('signed_roster', []) + 
            depth_chart_data.get('signed_non_roster', []) + 
            depth_chart_data.get('unsigned', [])
        )
        enriched_players = player_enrichment.enrich_depth_chart_players(all_players)
        
        # Re-categorize enriched players back into original categories
        enriched_by_status = {'signed_roster': [], 'signed_non_roster': [], 'unsigned': []}
        for player in enriched_players:
            roster_status = player.get('roster_status', '').lower()
            if roster_status in ['roster', 'signed_roster']:
                enriched_by_status['signed_roster'].append(player)
            elif roster_status in ['non_roster', 'signed_non_roster']:
                enriched_by_status['signed_non_roster'].append(player)
            elif roster_status == 'unsigned':
                enriched_by_status['unsigned'].append(player)
        
        # Update depth chart data with enriched players
        depth_chart_data['signed_roster'] = enriched_by_status['signed_roster']
        depth_chart_data['signed_non_roster'] = enriched_by_status['signed_non_roster']
        depth_chart_data['unsigned'] = enriched_by_status['unsigned']
        
        # Store in database
        scraped_date = datetime.now().date()
        stored_counts = {
            'signed_roster': 0,
            'signed_non_roster': 0,
            'unsigned': 0
        }
        
        with db.get_connection() as conn:
            # Store roster players
            for player in depth_chart_data.get('signed_roster', []):
                player['team_code'] = team_code
                player['scraped_date'] = scraped_date
                player['roster_status'] = 'roster'  # Update to new naming
                result = db.insert_team_roster_player(conn, player)
                if result:
                    stored_counts['signed_roster'] += 1
            
            # Store non-roster players
            for player in depth_chart_data.get('signed_non_roster', []):
                player['team_code'] = team_code
                player['scraped_date'] = scraped_date
                player['roster_status'] = 'non_roster'  # Update to new naming
                result = db.insert_team_roster_player(conn, player)
                if result:
                    stored_counts['signed_non_roster'] += 1
            
            # Store unsigned players (draft picks, rights)
            for player in depth_chart_data.get('unsigned', []):
                player['team_code'] = team_code
                player['scraped_date'] = scraped_date
                # roster_status already set to 'unsigned'
                result = db.insert_team_roster_player(conn, player)
                if result:
                    stored_counts['unsigned'] += 1
        
        total_stored = sum(stored_counts.values())
        
        logger.info(f"Successfully scraped {team_name} ({team_code})")
        logger.info(f"  Roster: {stored_counts['signed_roster']} players")
        logger.info(f"  Non-Roster: {stored_counts['signed_non_roster']} players")
        logger.info(f"  Unsigned: {stored_counts['unsigned']} players")
        logger.info(f"  Total Cap Hit: ${depth_chart_data.get('total_cap_hit', 0):,}")
        logger.info(f"  Total Cap %: {depth_chart_data.get('total_cap_percent', 0):.2f}%")
        
        # Export to CSV
        csv_path = None
        if export_csv:
            csv_path = export_roster_to_csv(team_code)
        
        return {
            'success': True,
            'team_code': team_code,
            'team_name': team_name,
            'scraped_date': scraped_date,
            'counts': stored_counts,
            'total_stored': total_stored,
            'total_cap_hit': depth_chart_data.get('total_cap_hit', 0),
            'total_cap_percent': depth_chart_data.get('total_cap_percent', 0.0),
            'csv_file': csv_path
        }
        
    except Exception as e:
        logger.error(f"Error scraping depth chart for {team_code}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'team_code': team_code,
            'error': str(e)
        }


def export_all_teams_csv() -> dict:
    """
    Export CSV files for all teams that have been scraped
    
    Returns:
        Dict with summary of exports
    """
    logger.info("Exporting CSV files for all scraped teams")
    logger.info("=" * 80)
    
    exported = []
    failed = []
    
    for team_code in sorted(NHL_TEAMS.keys()):
        try:
            csv_path = export_roster_to_csv(team_code)
            if csv_path:
                exported.append({'team_code': team_code, 'csv_file': csv_path})
            else:
                failed.append(team_code)
        except Exception as e:
            logger.error(f"Failed to export {team_code}: {e}")
            failed.append(team_code)
    
    logger.info("=" * 80)
    logger.info(f"CSV Export Complete: {len(exported)} teams exported")
    if failed:
        logger.warning(f"Failed to export: {', '.join(failed)}")
    
    return {
        'exported_count': len(exported),
        'failed_count': len(failed),
        'exported': exported,
        'failed': failed
    }


def scrape_all_teams(export_csv: bool = True) -> dict:
    """
    Scrape depth charts for all 32 NHL teams
    
    Returns:
        Dict with summary of results
    """
    logger.info("Starting depth chart scrape for all 32 NHL teams")
    logger.info("=" * 80)
    
    results = []
    success_count = 0
    fail_count = 0
    total_players = 0
    
    for team_code in sorted(NHL_TEAMS.keys()):
        result = scrape_team_depth_chart(team_code, export_csv=export_csv)
        results.append(result)
        
        if result.get('success'):
            success_count += 1
            total_players += result.get('total_stored', 0)
        else:
            fail_count += 1
        
        logger.info("-" * 80)
    
    logger.info("=" * 80)
    logger.info("SCRAPING COMPLETE")
    logger.info(f"Successfully scraped: {success_count}/32 teams")
    logger.info(f"Failed: {fail_count}/32 teams")
    logger.info(f"Total players stored: {total_players}")
    
    return {
        'success_count': success_count,
        'fail_count': fail_count,
        'total_players': total_players,
        'results': results
    }


def scrape_multiple_teams(team_codes: List[str], export_csv: bool = True) -> dict:
    """
    Scrape depth charts for multiple specified teams
    
    Args:
        team_codes: List of 3-letter team codes
    
    Returns:
        Dict with summary of results
    """
    logger.info(f"Starting depth chart scrape for {len(team_codes)} teams")
    logger.info("=" * 80)
    
    results = []
    success_count = 0
    fail_count = 0
    total_players = 0
    
    for team_code in team_codes:
        result = scrape_team_depth_chart(team_code, export_csv=export_csv)
        results.append(result)
        
        if result.get('success'):
            success_count += 1
            total_players += result.get('total_stored', 0)
        else:
            fail_count += 1
        
        logger.info("-" * 80)
    
    logger.info("=" * 80)
    logger.info("SCRAPING COMPLETE")
    logger.info(f"Successfully scraped: {success_count}/{len(team_codes)} teams")
    logger.info(f"Failed: {fail_count}/{len(team_codes)} teams")
    logger.info(f"Total players stored: {total_players}")
    
    return {
        'success_count': success_count,
        'fail_count': fail_count,
        'total_players': total_players,
        'results': results
    }


def main():
    """Command-line interface for depth chart scraping"""
    parser = argparse.ArgumentParser(
        description='Scrape NHL team depth charts from CapWages'
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--team',
        type=str,
        help='Scrape a single team (e.g., VGK, MTL, TOR)'
    )
    group.add_argument(
        '--teams',
        type=str,
        nargs='+',
        help='Scrape multiple teams (e.g., VGK MTL TOR)'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='Scrape all 32 NHL teams'
    )
    
    parser.add_argument(
        '--export-csv',
        action='store_true',
        default=False,
        help='Export existing roster data to CSV (without scraping)'
    )
    
    parser.add_argument(
        '--no-csv',
        action='store_true',
        default=False,
        help='Skip CSV export after scraping'
    )
    
    args = parser.parse_args()
    
    # Handle export-only mode
    if args.export_csv:
        if args.team:
            csv_path = export_roster_to_csv(args.team)
            if csv_path:
                print(f"\nExported: {csv_path}")
            else:
                print(f"\nNo data found for {args.team}")
                exit(1)
        elif args.teams:
            for team_code in args.teams:
                csv_path = export_roster_to_csv(team_code)
                if csv_path:
                    print(f"Exported: {csv_path}")
        elif args.all:
            result = export_all_teams_csv()
            print(f"\nExported {result['exported_count']} CSV files to data/depth_charts/")
        return
    
    export_csv = not args.no_csv
    
    if args.team:
        result = scrape_team_depth_chart(args.team, export_csv=export_csv)
        if result.get('success'):
            print(f"\nSuccess! Scraped {result['total_stored']} players for {result['team_name']}")
            if result.get('csv_file'):
                print(f"CSV exported: {result['csv_file']}")
        else:
            print(f"\nFailed to scrape {args.team}: {result.get('error')}")
            exit(1)
    
    elif args.teams:
        result = scrape_multiple_teams(args.teams, export_csv=export_csv)
        print(f"\nScraped {result['success_count']}/{len(args.teams)} teams successfully")
        print(f"Total players: {result['total_players']}")
        if export_csv:
            print(f"CSV files saved to: data/depth_charts/")
        if result['fail_count'] > 0:
            exit(1)
    
    elif args.all:
        result = scrape_all_teams(export_csv=export_csv)
        print(f"\nScraped {result['success_count']}/32 teams successfully")
        print(f"Total players: {result['total_players']}")
        if export_csv:
            print(f"CSV files saved to: data/depth_charts/")
        if result['fail_count'] > 0:
            exit(1)


if __name__ == '__main__':
    main()

