"""
HeartBeat Engine - Daily Active NHL Roster Sync
Montreal Canadiens Advanced Analytics Assistant

Automated script to fetch active 23-man rosters for all NHL teams and update
contract status (NHL vs MINOR) for accurate daily cap space calculations.

Features:
- Fetches current 23-man rosters from NHL API for all 32 teams
- Cross-references with league-wide contracts parquet file
- Updates roster_status field: "NHL" for active roster, "MINOR" for non-roster
- Maintains historical snapshots for trend analysis
- Tracks roster changes over time
- Enables dynamic daily cap space calculations
"""

import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import logging
import sys
from typing import Dict, Any, List, Set, Optional
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from orchestrator.tools.nhl_roster_client import NHLRosterClient
from orchestrator.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / 'roster_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# All 32 NHL teams (2024-25 season with Utah relocation)
NHL_TEAMS = [
    "ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL",
    "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD",
    "NSH", "NYI", "NYR", "OTT", "PHI", "PIT", "SEA", "SJS",
    "STL", "TBL", "TOR", "UTA", "VAN", "VGK", "WPG", "WSH"
]


class DailyActiveRosterSync:
    """Daily NHL Active Roster Synchronization System"""
    
    def __init__(self, data_directory: Path, season: str = "2025-2026"):
        """
        Initialize active roster sync.
        
        Args:
            data_directory: Root directory for processed data
            season: NHL season (e.g., "2025-2026")
        """
        self.data_root = data_directory
        self.market_dir = self.data_root / "market"
        self.historical_dir = self.market_dir / "historical"
        self.historical_dir.mkdir(parents=True, exist_ok=True)
        
        self.season = season
        self.contracts_file = self.market_dir / f"nhl_contracts_league_wide_{season.replace('-', '_')}.parquet"
        
        self.client = NHLRosterClient(cache_ttl_seconds=60)
        
        logger.info(f"Daily active roster sync initialized for {season}")
        logger.info(f"Contracts file: {self.contracts_file}")
    
    async def sync_active_rosters(self) -> Dict[str, Any]:
        """
        Fetch active 23-man rosters for all NHL teams and update contract statuses.
        
        Returns:
            Sync status with detailed results
        """
        start_time = datetime.now()
        logger.info(f"Starting daily active roster sync at {start_time.isoformat()}")
        
        # Step 1: Fetch all active rosters from NHL API
        logger.info("Fetching active rosters for all 32 NHL teams...")
        rosters = await self.client.get_all_rosters(
            teams=NHL_TEAMS,
            season="current",  # Use "current" to get today's active roster
            scope="active",
            max_concurrency=8
        )
        
        # Step 2: Build set of all active NHL player IDs
        active_nhl_players: Set[int] = set()
        roster_by_team: Dict[str, List[Dict[str, Any]]] = {}
        
        success_count = 0
        error_count = 0
        
        for team, roster_data in rosters.items():
            if "error" in roster_data:
                logger.error(f"Failed to fetch roster for {team}: {roster_data['error']}")
                error_count += 1
                continue
            
            players = roster_data.get("players", [])
            roster_by_team[team] = players
            
            # Extract player IDs
            for player in players:
                player_id = player.get("nhl_player_id")
                if player_id:
                    active_nhl_players.add(int(player_id))
            
            success_count += 1
            logger.info(f"Fetched {len(players)} active players for {team}")
        
        logger.info(f"Total active NHL players across all teams: {len(active_nhl_players)}")
        
        # Step 3: Load existing contracts file
        if not self.contracts_file.exists():
            logger.error(f"Contracts file not found: {self.contracts_file}")
            return {
                "status": "error",
                "message": f"Contracts file not found: {self.contracts_file}"
            }
        
        logger.info(f"Loading contracts from {self.contracts_file}")
        contracts_df = pd.read_parquet(self.contracts_file)
        original_count = len(contracts_df)
        logger.info(f"Loaded {original_count} contract records")
        
        # Step 4: Update roster_status based on active roster
        logger.info("Updating roster_status field...")
        
        # Add new tracking columns if they don't exist
        if 'last_status_change' not in contracts_df.columns:
            contracts_df['last_status_change'] = None
        if 'days_on_nhl_roster' not in contracts_df.columns:
            contracts_df['days_on_nhl_roster'] = 0
        if 'roster_sync_date' not in contracts_df.columns:
            contracts_df['roster_sync_date'] = None
        
        # Track status changes
        status_changes = []
        nhl_count = 0
        minor_count = 0
        ir_preserved_count = 0
        
        for idx, row in contracts_df.iterrows():
            player_id = row.get('nhl_player_id')
            old_status = row.get('roster_status', '')
            
            # Skip unsigned players
            if old_status == 'Unsigned' or old_status == 'unsigned':
                continue
            
            # Preserve special contract statuses - do not update if player has special status
            # IR = Injured Reserve, LTIR = Long-Term IR, soir = Signed On IR, Loan = On loan to another league
            special_statuses = ['IR', 'LTIR', 'ir', 'ltir', 'soir', 'Loan', 'loan']
            if old_status in special_statuses:
                logger.debug(f"Preserving {old_status} status for {row.get('full_name', 'Unknown')} ({row.get('team_abbrev', 'UNK')})")
                contracts_df.at[idx, 'roster_sync_date'] = datetime.now().isoformat()
                ir_preserved_count += 1
                continue
            
            # Determine new status
            if pd.notna(player_id) and int(float(player_id)) in active_nhl_players:
                new_status = 'NHL'
                nhl_count += 1
            else:
                # Not on any active roster
                new_status = 'MINOR'
                minor_count += 1
            
            # Update status
            contracts_df.at[idx, 'roster_status'] = new_status
            contracts_df.at[idx, 'roster_sync_date'] = datetime.now().isoformat()
            
            # Track status change
            if old_status != new_status and pd.notna(old_status) and old_status not in ['', 'Unsigned', 'unsigned']:
                contracts_df.at[idx, 'last_status_change'] = datetime.now().isoformat()
                status_changes.append({
                    'player_id': player_id,
                    'player_name': row.get('full_name', 'Unknown'),
                    'team': row.get('team_abbrev', 'Unknown'),
                    'old_status': old_status,
                    'new_status': new_status
                })
                logger.info(f"Status change: {row.get('full_name', 'Unknown')} ({row.get('team_abbrev', 'UNK')}): {old_status} -> {new_status}")
            
            # Update days on NHL roster counter
            if new_status == 'NHL':
                current_days = row.get('days_on_nhl_roster', 0)
                contracts_df.at[idx, 'days_on_nhl_roster'] = current_days + 1
            else:
                contracts_df.at[idx, 'days_on_nhl_roster'] = 0
        
        logger.info(f"Updated roster status: {nhl_count} NHL, {minor_count} MINOR, {ir_preserved_count} Special Status (preserved)")
        logger.info(f"Status changes detected: {len(status_changes)}")
        
        # Step 5: Save historical snapshot
        today = datetime.now().strftime("%Y_%m_%d")
        snapshot_file = self.historical_dir / f"nhl_contracts_league_wide_{today}.parquet"
        
        contracts_df.to_parquet(
            snapshot_file,
            engine='pyarrow',
            compression='zstd',
            index=False
        )
        logger.info(f"Saved historical snapshot: {snapshot_file}")
        
        # Step 6: Update canonical contracts file
        contracts_df.to_parquet(
            self.contracts_file,
            engine='pyarrow',
            compression='zstd',
            index=False
        )
        logger.info(f"Updated contracts file: {self.contracts_file}")
        
        # Step 7: Generate roster summary by team
        team_summaries = {}
        for team in NHL_TEAMS:
            team_contracts = contracts_df[contracts_df['team_abbrev'] == team]
            nhl_roster = team_contracts[team_contracts['roster_status'] == 'NHL']
            
            # Calculate cap hit for active roster
            active_cap_hit = nhl_roster['cap_hit_2025_26'].fillna(0).sum()
            
            team_summaries[team] = {
                'team_abbrev': team,
                'active_roster_count': len(nhl_roster),
                'active_cap_hit': float(active_cap_hit),
                'players_nhl': nhl_roster['full_name'].tolist(),
                'players_minor': team_contracts[team_contracts['roster_status'] == 'MINOR']['full_name'].tolist()
            }
        
        # Step 8: Cleanup old snapshots (keep last 60 days)
        self._cleanup_old_snapshots(days_to_keep=60)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = {
            'status': 'success' if error_count == 0 else 'partial_success',
            'teams_synced': success_count,
            'teams_failed': error_count,
            'total_active_nhl_players': len(active_nhl_players),
            'total_contracts': original_count,
            'nhl_status_count': nhl_count,
            'minor_status_count': minor_count,
            'special_status_preserved_count': ir_preserved_count,
            'status_changes': len(status_changes),
            'status_changes_details': status_changes,
            'team_summaries': team_summaries,
            'elapsed_seconds': elapsed,
            'timestamp': datetime.now().isoformat(),
            'snapshot_file': str(snapshot_file),
            'contracts_file': str(self.contracts_file)
        }
        
        logger.info(f"Daily active roster sync complete: {result['status']}")
        logger.info(f"Synced {success_count}/{len(NHL_TEAMS)} teams in {elapsed:.2f}s")
        
        return result
    
    def _cleanup_old_snapshots(self, days_to_keep: int = 60):
        """Remove historical snapshot files older than specified days."""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        
        removed_count = 0
        for file in self.historical_dir.glob("nhl_contracts_league_wide_*.parquet"):
            if file.stat().st_mtime < cutoff_date:
                logger.info(f"Removing old snapshot: {file.name}")
                file.unlink()
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old snapshot files")
    
    def get_roster_summary(self, team: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current roster summary for a team or all teams.
        
        Args:
            team: Team abbreviation (e.g., "MTL") or None for all teams
            
        Returns:
            Roster summary with cap space calculations
        """
        if not self.contracts_file.exists():
            raise FileNotFoundError(f"Contracts file not found: {self.contracts_file}")
        
        contracts_df = pd.read_parquet(self.contracts_file)
        
        if team:
            team = team.upper()
            team_contracts = contracts_df[contracts_df['team_abbrev'] == team]
            nhl_roster = team_contracts[team_contracts['roster_status'] == 'NHL']
            
            active_cap_hit = nhl_roster['cap_hit_2025_26'].fillna(0).sum()
            
            return {
                'team_abbrev': team,
                'active_roster_count': len(nhl_roster),
                'active_cap_hit': float(active_cap_hit),
                'players_nhl': nhl_roster[['full_name', 'position', 'cap_hit_2025_26']].to_dict('records'),
                'players_minor': team_contracts[team_contracts['roster_status'] == 'MINOR'][['full_name', 'position', 'cap_hit_2025_26']].to_dict('records'),
                'last_sync': contracts_df['roster_sync_date'].dropna().max() if not contracts_df['roster_sync_date'].dropna().empty else None
            }
        else:
            # All teams summary
            summaries = {}
            for team_abbrev in NHL_TEAMS:
                team_contracts = contracts_df[contracts_df['team_abbrev'] == team_abbrev]
                nhl_roster = team_contracts[team_contracts['roster_status'] == 'NHL']
                
                active_cap_hit = nhl_roster['cap_hit_2025_26'].fillna(0).sum()
                
                summaries[team_abbrev] = {
                    'team_abbrev': team_abbrev,
                    'active_roster_count': len(nhl_roster),
                    'active_cap_hit': float(active_cap_hit)
                }
            
            return {
                'teams': summaries,
                'last_sync': contracts_df['roster_sync_date'].dropna().max() if not contracts_df['roster_sync_date'].dropna().empty else None
            }


async def main():
    """Main entry point for daily active roster sync"""
    parser = argparse.ArgumentParser(description='Daily NHL Active Roster Sync')
    parser.add_argument('--season', type=str, default='2025-2026', help='NHL season (e.g., 2025-2026)')
    parser.add_argument('--summary', type=str, help='Get roster summary for team (e.g., MTL)')
    args = parser.parse_args()
    
    # Use settings from config
    data_root = Path(settings.parquet.data_directory)
    
    sync = DailyActiveRosterSync(data_root, season=args.season)
    
    # If summary requested, print and exit
    if args.summary:
        summary = sync.get_roster_summary(args.summary)
        print(f"\nRoster Summary for {args.summary}:")
        print(f"Active Roster: {summary['active_roster_count']} players")
        print(f"Active Cap Hit: ${summary['active_cap_hit']:,.0f}")
        print(f"Last Sync: {summary['last_sync']}")
        print(f"\nNHL Players ({len(summary['players_nhl'])}):")
        for player in summary['players_nhl']:
            print(f"  - {player['full_name']} ({player['position']}) - ${player['cap_hit_2025_26']:,.0f}")
        print(f"\nMinor/AHL Players ({len(summary['players_minor'])}):")
        for player in summary['players_minor']:
            print(f"  - {player['full_name']} ({player['position']}) - ${player['cap_hit_2025_26']:,.0f}")
        return 0
    
    # Run sync
    result = await sync.sync_active_rosters()
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"DAILY ACTIVE ROSTER SYNC COMPLETE")
    print(f"{'='*70}")
    print(f"Status: {result['status']}")
    print(f"Teams Synced: {result['teams_synced']}/{len(NHL_TEAMS)}")
    print(f"Active NHL Players: {result['total_active_nhl_players']}")
    print(f"NHL Roster Status: {result['nhl_status_count']}")
    print(f"Minor Roster Status: {result['minor_status_count']}")
    print(f"Special Status (Preserved): {result['special_status_preserved_count']}")
    print(f"Status Changes: {result['status_changes']}")
    print(f"Elapsed Time: {result['elapsed_seconds']:.2f}s")
    print(f"Snapshot: {result['snapshot_file']}")
    print(f"{'='*70}\n")
    
    if result['status_changes'] > 0:
        print("Status Changes Detected:")
        for change in result['status_changes_details']:
            print(f"  - {change['player_name']} ({change['team']}): {change['old_status']} -> {change['new_status']}")
        print()
    
    if result['status'] == 'success':
        logger.info("Daily active roster sync completed successfully")
        
        # Rebuild unified roster index for search functionality
        logger.info("Rebuilding unified roster index...")
        try:
            import subprocess
            rebuild_result = subprocess.run(
                ['python3', 'scripts/transform/build_unified_roster.py'],
                cwd=str(Path(__file__).parent.parent),
                capture_output=True,
                text=True,
                timeout=30
            )
            if rebuild_result.returncode == 0:
                logger.info("Unified roster index rebuilt successfully")
            else:
                logger.warning(f"Unified roster rebuild failed: {rebuild_result.stderr}")
        except Exception as e:
            logger.warning(f"Could not rebuild unified roster: {e}")
        
        return 0
    else:
        logger.warning(f"Roster sync completed with {result['teams_failed']} failures")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

