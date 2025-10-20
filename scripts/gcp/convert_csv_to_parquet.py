"""
HeartBeat Engine - Convert CSV to Parquet for GCS Upload
Convert raw CSV data to optimized Parquet format with ZSTD compression
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_ROOT = Path(__file__).parent.parent / "data"
PROCESSED_ROOT = DATA_ROOT / "processed"

# Enforced schema for PBP conversion to ensure consistent Parquet types across seasons/teams
PBP_ENFORCED_TYPES = {
    # Identifiers and refs
    'gameReferenceId': 'string',
    'id': 'string',
    'playerReferenceId': 'string',
    'teamGoalieOnIceRef': 'string',
    'opposingTeamGoalieOnIceRef': 'string',
    'teamForwardsOnIceRefs': 'string',
    'teamDefencemenOnIceRefs': 'string',
    'opposingTeamForwardsOnIceRefs': 'string',
    'opposingTeamDefencemenOnIceRefs': 'string',
    # Strings
    'timecode': 'string',
    'shorthand': 'string',
    'name': 'string',
    'previousName': 'string',
    'type': 'string',
    'previousType': 'string',
    'outcome': 'string',
    'previousOutcome': 'string',
    'zone': 'string',
    'playZone': 'string',
    'playSection': 'string',
    'manpowerSituation': 'string',
    'team': 'string',
    'team_abbrev': 'string',
    'source_file': 'string',
    'playerFirstName': 'string',
    'playerLastName': 'string',
    'playerPosition': 'string',
    'playerJersey': 'string',
    # Integers
    'period': 'Int64',
    'frame': 'Int64',
    'teamSkatersOnIce': 'Int64',
    # Floats
    'periodTime': 'float64',
    'gameTime': 'float64',
    'xCoord': 'float64',
    'yCoord': 'float64',
    'xAdjCoord': 'float64',
    'yAdjCoord': 'float64',
    'expectedGoalsOnNet': 'float64',
    'expectedGoalsAllShots': 'float64',
}


class CSVToParquetConverter:
    """Convert CSV files to optimized Parquet format."""
    
    def __init__(self, compression: str = "ZSTD", compression_level: int = 3):
        self.compression = compression
        self.compression_level = compression_level
        
    def convert_depth_charts(self) -> int:
        """
        Convert depth chart CSVs to Parquet.
        
        Source: data/depth_charts/*.csv
        Target: data/processed/dim/depth_charts/{team}_depth_chart_{date}.parquet
        """
        logger.info("Converting depth chart CSVs to Parquet...")
        
        depth_charts_dir = DATA_ROOT / "depth_charts"
        output_dir = PROCESSED_ROOT / "dim" / "depth_charts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        converted = 0
        csv_files = list(depth_charts_dir.glob("*.csv"))
        
        for csv_file in csv_files:
            try:
                # Read CSV
                df = pd.read_csv(csv_file)
                
                # Extract team and date from filename (e.g., MTL_depth_chart_2025-10-18.csv)
                parts = csv_file.stem.split('_')
                team = parts[0]
                date = parts[-1]  # 2025-10-18
                
                # Add metadata columns
                df['team_abbrev'] = team
                df['snapshot_date'] = date
                df['loaded_at'] = datetime.now().isoformat()
                
                # Output filename
                output_file = output_dir / f"{team}_depth_chart_{date.replace('-', '_')}.parquet"
                
                # Write Parquet with ZSTD compression
                df.to_parquet(
                    output_file,
                    engine='pyarrow',
                    compression=self.compression,
                    compression_level=self.compression_level,
                    index=False
                )
                
                logger.info(f"  ✓ {csv_file.name} -> {output_file.name}")
                converted += 1
                
            except Exception as e:
                logger.error(f"  Failed to convert {csv_file.name}: {e}")
        
        logger.info(f"✓ Converted {converted} depth chart files")
        return converted
    
    def convert_contracts(self, limit: Optional[int] = None) -> int:
        """
        Convert contract CSVs to consolidated Parquet.
        
        Source: data/contracts/*.csv
        Target: data/processed/market/contracts/contracts_{date}.parquet
        """
        logger.info("Converting contract CSVs to Parquet...")
        
        contracts_dir = DATA_ROOT / "contracts"
        output_dir = PROCESSED_ROOT / "market" / "contracts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        csv_files = list(contracts_dir.glob("*.csv"))
        if limit:
            csv_files = csv_files[:limit]
        
        logger.info(f"Processing {len(csv_files)} contract files...")
        
        # Collect all contract data
        all_contracts = []
        
        for idx, csv_file in enumerate(csv_files):
            try:
                df = pd.read_csv(csv_file)
                
                # Extract player name from filename (e.g., nick_suzuki_summary_20251018_164418.csv)
                # Add source filename for tracking
                df['source_file'] = csv_file.name
                df['loaded_at'] = datetime.now().isoformat()
                
                all_contracts.append(df)
                
                if (idx + 1) % 100 == 0:
                    logger.info(f"  Processed {idx + 1}/{len(csv_files)} files...")
                    
            except Exception as e:
                logger.error(f"  Failed to read {csv_file.name}: {e}")
        
        if not all_contracts:
            logger.warning("No contract data to convert")
            return 0
        
        # Concatenate all contracts
        combined_df = pd.concat(all_contracts, ignore_index=True)
        logger.info(f"Combined {len(combined_df)} contract records")
        
        # Write consolidated Parquet
        output_file = output_dir / f"contracts_{datetime.now().strftime('%Y_%m_%d')}.parquet"
        combined_df.to_parquet(
            output_file,
            engine='pyarrow',
            compression=self.compression,
            compression_level=self.compression_level,
            index=False
        )
        
        logger.info(f"✓ Converted {len(csv_files)} contract files to {output_file.name}")
        logger.info(f"  Total records: {len(combined_df)}")
        logger.info(f"  File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
        
        return len(csv_files)
    
    def convert_play_by_play(self, team: str = "mtl") -> int:
        """
        Legacy helper: convert a single team's PBP from data/{team}_play_by_play.
        Prefer convert_pbp_from_analytics_source() for full-league ingestion.
        """
        source_dir = DATA_ROOT / f"{team.lower()}_play_by_play"
        return self._convert_pbp_from_dir(source_dir, team.upper())

    def convert_pbp_from_analytics_source(self) -> int:
        """
        Convert league-wide play-by-play CSVs to Parquet.
        
        Source: data/processed/analytics/nhl_play_by_play/{TEAM}/{SEASON}/*.csv
        Target: data/processed/fact/pbp/season={SEASON}/team={TEAM}/*.parquet
        """
        base_dir = PROCESSED_ROOT / "analytics" / "nhl_play_by_play"
        if not base_dir.exists():
            logger.warning(f"Analytics PBP source not found: {base_dir}")
            return 0
        converted = 0
        for team_dir in sorted(base_dir.iterdir()):
            if not team_dir.is_dir():
                continue
            team = team_dir.name.upper()
            for season_dir in sorted(team_dir.iterdir()):
                if not season_dir.is_dir():
                    continue
                converted += self._convert_pbp_from_dir(season_dir, team, explicit_season=season_dir.name)
        logger.info(f"✓ Converted {converted} play-by-play files (league-wide)")
        return converted

    def _convert_pbp_from_dir(self, source_dir: Path, team: str, explicit_season: Optional[str] = None) -> int:
        """Internal: convert all CSVs in a season directory to partitioned Parquet."""
        if not source_dir.exists():
            return 0
        output_base_dir = PROCESSED_ROOT / "fact" / "pbp"
        count = 0
        # If called with path .../{SEASON}, capture it; else keep None
        season = explicit_season
        # If season unknown and direct structure is season folders, derive later from filename
        csv_files = list(source_dir.glob("*.csv"))
        if not csv_files:
            return 0
        if season is None:
            # Try to infer from first filename (e.g., playsequence-20251016-...-20252026-20062.csv → 2025-2026)
            season = _infer_season_from_filename(csv_files[0].name)
        # Prepare partition dir
        out_dir = output_base_dir / f"season={season}" / f"team={team}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                # Metadata
                df['season'] = season
                df['team_abbrev'] = team
                df['source_file'] = csv_file.name
                # Best-effort parse date and game code
                game_date = _infer_game_date_from_filename(csv_file.name)
                if game_date:
                    df['game_date'] = game_date
                game_code = _infer_game_code_from_filename(csv_file.name)
                if game_code:
                    df['game_code'] = game_code
                # Enforce stable schema for problematic and commonly varying columns
                for col, dtype in PBP_ENFORCED_TYPES.items():
                    if col not in df.columns:
                        df[col] = pd.NA
                    try:
                        if dtype == 'string':
                            df[col] = df[col].astype('string')
                        elif dtype == 'Int64':
                            # pandas nullable integer dtype
                            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                        elif dtype == 'float64':
                            df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
                    except Exception as e:
                        logger.warning(
                            f"  Could not cast column {col} to {dtype} in {csv_file.name}: {e}"
                        )
                # Write
                out_file = out_dir / f"{csv_file.stem}.parquet"
                df.to_parquet(out_file, engine='pyarrow', compression=self.compression,
                              compression_level=self.compression_level, index=False)
                count += 1
            except Exception as e:
                logger.error(f"  Failed to convert {csv_file.name}: {e}")
        logger.info(f"  ✓ {team} {season}: {count} games converted from {source_dir}")
        return count
    
    def create_unified_roster_snapshot(self) -> str:
        """
        Create unified roster snapshot Parquet from all team depth charts.
        
        Source: data/depth_charts/*.csv
        Target: data/processed/dim/rosters/nhl_rosters_latest.parquet
        """
        logger.info("Creating unified roster snapshot...")
        
        depth_charts_dir = DATA_ROOT / "depth_charts"
        output_dir = PROCESSED_ROOT / "dim" / "rosters"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_rosters = []
        snapshot_date = None
        
        for csv_file in sorted(depth_charts_dir.glob("*.csv")):
            try:
                df = pd.read_csv(csv_file)
                
                # Extract team and date
                parts = csv_file.stem.split('_')
                team = parts[0]
                date = parts[-1]  # 2025-10-18
                
                if snapshot_date is None:
                    snapshot_date = date
                
                # Add team abbreviation
                df['team_abbrev'] = team
                
                all_rosters.append(df)
                
            except Exception as e:
                logger.error(f"  Failed to read {csv_file.name}: {e}")
        
        if not all_rosters:
            logger.error("No roster data found")
            return ""
        
        # Concatenate all rosters
        combined_df = pd.concat(all_rosters, ignore_index=True)
        
        # Add snapshot metadata
        combined_df['snapshot_date'] = snapshot_date
        combined_df['loaded_at'] = datetime.now().isoformat()
        
        # Write as latest snapshot
        latest_file = output_dir / "nhl_rosters_latest.parquet"
        combined_df.to_parquet(
            latest_file,
            engine='pyarrow',
            compression=self.compression,
            compression_level=self.compression_level,
            index=False
        )
        
        # Also write with date stamp
        dated_file = output_dir / f"nhl_rosters_{snapshot_date.replace('-', '_')}.parquet"
        combined_df.to_parquet(
            dated_file,
            engine='pyarrow',
            compression=self.compression,
            compression_level=self.compression_level,
            index=False
        )
        
        logger.info(f"✓ Created unified roster snapshot")
        logger.info(f"  Total players: {len(combined_df)}")
        logger.info(f"  Teams: {combined_df['team_abbrev'].nunique()}")
        logger.info(f"  Snapshot date: {snapshot_date}")
        logger.info(f"  Output: {latest_file.name}")
        
        return str(latest_file)
    
    def convert_league_player_stats(self) -> int:
        """
        Convert league player stats CSVs to Parquet by season.
        
        Source: data/processed/league_player_stats/{season}/unified_player_stats_{season}.csv
        Target: data/processed/league_player_stats/parquet/season={season}/*.parquet
        """
        logger.info("Converting league player stats CSVs to Parquet...")
        
        league_stats_dir = PROCESSED_ROOT / "league_player_stats"
        if not league_stats_dir.exists():
            logger.warning(f"League stats directory not found: {league_stats_dir}")
            return 0
        
        output_base_dir = league_stats_dir / "parquet"
        converted = 0
        
        # Process each season directory
        for season_dir in sorted(league_stats_dir.iterdir()):
            if not season_dir.is_dir() or season_dir.name == "parquet":
                continue
            
            season = season_dir.name  # e.g., "2024-2025"
            csv_files = list(season_dir.glob("*.csv"))
            
            if not csv_files:
                continue
            
            logger.info(f"  Processing {season}...")
            
            # Create output directory with Hive partitioning
            output_dir = output_base_dir / f"season={season}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process CSV file
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    
                    # Add season metadata
                    df['season'] = season
                    df['loaded_at'] = datetime.now().isoformat()
                    
                    # Output filename
                    output_file = output_dir / f"unified_player_stats_{season.replace('-', '')}.parquet"
                    
                    # Write Parquet with ZSTD compression
                    df.to_parquet(
                        output_file,
                        engine='pyarrow',
                        compression=self.compression,
                        compression_level=self.compression_level,
                        index=False
                    )
                    
                    logger.info(f"    ✓ {season}: {len(df)} player records")
                    converted += 1
                    
                except Exception as e:
                    logger.error(f"  Failed to convert {csv_file.name}: {e}")
        
        logger.info(f"✓ Converted {converted} league player stat files")
        return converted
    
    def run_full_conversion(self) -> dict:
        """Run complete CSV to Parquet conversion."""
        
        logger.info("=" * 60)
        logger.info("HEARTBEAT CSV TO PARQUET CONVERSION")
        logger.info("=" * 60)
        logger.info("")
        
        results = {}
        
        # Convert depth charts (individual files)
        results['depth_charts'] = self.convert_depth_charts()
        
        # Create unified roster snapshot
        roster_file = self.create_unified_roster_snapshot()
        results['unified_roster'] = roster_file
        
        # Convert play-by-play (league-wide from analytics source)
        results['play_by_play'] = self.convert_pbp_from_analytics_source()
        
        # Convert league player stats (10 seasons)
        results['league_player_stats'] = self.convert_league_player_stats()
        
        # Convert contracts (limit to avoid processing 2000+ files)
        # Note: Contract processing can be run separately if needed
        logger.info("\nNote: Skipping full contract conversion (2287 files)")
        logger.info("      Run with convert_contracts(limit=None) if needed")
        results['contracts'] = 0
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("CONVERSION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Depth charts:        {results['depth_charts']} files")
        logger.info(f"  Unified roster:      {results['unified_roster']}")
        logger.info(f"  Play-by-play:        {results['play_by_play']} files")
        logger.info(f"  League player stats: {results['league_player_stats']} seasons")
        logger.info("")
        
        return results


"""Filename parsing helpers for play-by-play CSVs"""
def _infer_season_from_filename(name: str) -> Optional[str]:
    # Example: playsequence-20251016-NHL-NSHvsMTL-20252026-20062.csv → 2025-2026
    import re
    m = re.search(r"-(20\d{2})(?:\s*|)(?:\-|)(\d{2})\b", name)
    # Above not reliable; fallback to 8-digit date + trailing season code 20252026
    m2 = re.search(r"-(20\d{2})(\d{2})(\d{2}).*-(20\d{2})(\d{2})\b", name)
    if m2:
        y1 = m2.group(4); y2 = m2.group(5)
        return f"{y1}-{y2}"
    m3 = re.search(r"-(20\d{2})(\d{2})(\d{2}).*-([12]\d{3})([12]\d)\b", name)
    if m3:
        y1 = m3.group(4); y2 = m3.group(5)
        return f"{y1}-{y2}"
    # Last resort: None
    return None

def _infer_game_date_from_filename(name: str) -> Optional[str]:
    # playsequence-YYYYMMDD-... → YYYY-MM-DD
    import re
    m = re.search(r"playsequence-(\d{4})(\d{2})(\d{2})", name)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

def _infer_game_code_from_filename(name: str) -> Optional[str]:
    # trailing -<digits>.csv
    import re
    m = re.search(r"-(\d+)\.csv$", name)
    return m.group(1) if m else None


def main():
    """Run CSV to Parquet conversion."""
    
    converter = CSVToParquetConverter(compression="ZSTD", compression_level=3)
    results = converter.run_full_conversion()
    
    return 0


if __name__ == "__main__":
    exit(main())
