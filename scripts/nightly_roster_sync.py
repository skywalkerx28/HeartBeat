"""
HeartBeat Engine - Daily NHL Roster Sync
Montreal Canadiens Advanced Analytics Assistant

Automated script to fetch and store NHL rosters for all 32 teams.
Runs daily to maintain up-to-date roster data.

Features:
- Fetches rosters for all 32 NHL teams
- Optimized for daily updates (searches last 14 days for games)
- Saves to Parquet with efficient compression
- Maintains historical snapshots
- Handles API failures gracefully
- Logs sync status and errors
"""

import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import sys
from typing import Dict, Any, List

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

# All 32 NHL teams (updated for 2024-25 season with Utah relocation)
NHL_TEAMS = [
    "ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL",
    "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD",
    "NSH", "NYI", "NYR", "OTT", "PHI", "PIT", "SEA", "SJS",
    "STL", "TBL", "TOR", "UTA", "VAN", "VGK", "WPG", "WSH"
]


class DailyRosterSync:
    """Automated NHL roster synchronization system"""
    
    def __init__(self, data_directory: Path):
        """
        Initialize roster sync.
        
        Args:
            data_directory: Root directory for processed data
        """
        self.data_root = data_directory
        self.roster_dir = self.data_root / "rosters"
        self.roster_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = NHLRosterClient(cache_ttl_seconds=60)
        
        logger.info(f"Daily roster sync initialized: {self.roster_dir}")
    
    async def sync_all_rosters(self, season: str = "current") -> Dict[str, Any]:
        """
        Fetch rosters for all 32 NHL teams and save to Parquet.
        
        Args:
            season: NHL season (e.g., "2025-2026" or "current")
            
        Returns:
            Sync status with success/failure counts
        """
        start_time = datetime.now()
        logger.info(f"Starting daily roster sync for season: {season}")
        
        # Fetch all rosters concurrently
        rosters = await self.client.get_all_rosters(
            teams=NHL_TEAMS,
            season=season,
            scope="active",
            max_concurrency=8
        )
        
        # Process results
        success_count = 0
        error_count = 0
        all_players: List[Dict[str, Any]] = []
        
        for team, roster_data in rosters.items():
            if "error" in roster_data:
                logger.error(f"Failed to fetch roster for {team}: {roster_data['error']}")
                error_count += 1
                continue
            
            players = roster_data.get("players", [])
            
            # Add team and sync metadata to each player
            for player in players:
                player["team_abbrev"] = team
                player["sync_date"] = datetime.now().isoformat()
                player["season"] = roster_data.get("season", season)
                all_players.append(player)
            
            success_count += 1
            logger.info(f"Synced {len(players)} players for {team}")
        
        # Convert to DataFrame
        if all_players:
            df = pd.DataFrame(all_players)

            # Deduplicate players by team + player ID to handle relocations
            original_count = len(df)
            df = df.drop_duplicates(subset=['team_abbrev', 'nhl_player_id'], keep='last')
            if len(df) < original_count:
                logger.info(f"Removed {original_count - len(df)} duplicate players during deduplication")
            
            # Save to Parquet with today's date
            today = datetime.now().strftime("%Y_%m_%d")
            output_file = self.roster_dir / f"nhl_rosters_{today}.parquet"
            
            df.to_parquet(
                output_file,
                engine='pyarrow',
                compression='zstd',
                index=False
            )
            
            logger.info(f"Saved {len(all_players)} players to {output_file}")
            
            # Also save as "latest" for easy access
            latest_file = self.roster_dir / "nhl_rosters_latest.parquet"
            df.to_parquet(
                latest_file,
                engine='pyarrow',
                compression='zstd',
                index=False
            )
            
            logger.info(f"Updated latest roster file: {latest_file}")
        else:
            logger.error("No roster data retrieved")
        
        # Cleanup old roster files (keep last 30 days)
        self._cleanup_old_rosters(days_to_keep=30)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success" if error_count == 0 else "partial_success",
            "teams_synced": success_count,
            "teams_failed": error_count,
            "total_players": len(all_players),
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Daily roster sync complete: {result}")
        return result
    
    def _cleanup_old_rosters(self, days_to_keep: int = 30):
        """Remove roster files older than specified days."""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        
        for file in self.roster_dir.glob("nhl_rosters_*.parquet"):
            # Skip the "latest" file
            if "latest" in file.name:
                continue
            
            if file.stat().st_mtime < cutoff_date:
                logger.info(f"Removing old roster file: {file.name}")
                file.unlink()
    
    def get_latest_roster(self) -> pd.DataFrame:
        """Load the most recent roster snapshot."""
        latest_file = self.roster_dir / "nhl_rosters_latest.parquet"
        
        if latest_file.exists():
            return pd.read_parquet(latest_file)
        
        # Fallback: find most recent dated file
        roster_files = sorted(self.roster_dir.glob("nhl_rosters_*.parquet"), reverse=True)
        if roster_files:
            return pd.read_parquet(roster_files[0])
        
        raise FileNotFoundError("No roster data found")
    
    def get_team_roster(self, team: str) -> pd.DataFrame:
        """
        Get roster for specific team from latest snapshot.
        
        Args:
            team: Team abbreviation (e.g., "MTL", "TOR")
            
        Returns:
            DataFrame of team's roster
        """
        df = self.get_latest_roster()
        return df[df['team_abbrev'] == team.upper()].copy()
    
    def search_player(self, player_name: str) -> pd.DataFrame:
        """
        Search for player across all teams.
        
        Args:
            player_name: Full or partial player name
            
        Returns:
            DataFrame of matching players
        """
        df = self.get_latest_roster()
        
        # Case-insensitive search in full_name
        mask = df['full_name'].str.contains(player_name, case=False, na=False)
        
        return df[mask].copy()


async def main():
    """Main entry point for daily roster sync"""
    # Use settings from config
    data_root = Path(settings.parquet.data_directory)

    sync = DailyRosterSync(data_root)
    
    # Sync current season
    result = await sync.sync_all_rosters(season="current")
    
    if result["status"] == "success":
        logger.info("Daily roster sync completed successfully")
        return 0
    else:
        logger.warning(f"Roster sync completed with {result['teams_failed']} failures")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

