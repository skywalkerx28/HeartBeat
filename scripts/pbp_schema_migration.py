#!/usr/bin/env python3
"""
Play-by-Play Schema Migration Script

Upgrades unified PBP parquet to production-ready format with:
- Proper schema normalization
- Canonical player IDs
- Time standardization
- Event type categorization
- Coordinate system normalization
- Row-level selectors for rehydration
"""

import pandas as pd
import numpy as np
from pathlib import Path
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

class PBPSchemaMigrator:
    """Migrates PBP data to production schema with proper normalization"""
    
    def __init__(self, base_path: str = "/Users/xavier.bouchard/Desktop/HeartBeat"):
        self.base_path = Path(base_path)
        self.data_path = self.base_path / "data"
        self.processed_path = self.data_path / "processed"
        
        # Schema configuration
        self.season = "2024-25"
        self.ingest_timestamp = int(time.time())
        self.version = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Event type mappings
        self.event_type_mapping = {
            'shot': 'SHOT',
            'goal': 'GOAL', 
            'pass': 'PASS',
            'reception': 'RECEPTION',
            'carry': 'CARRY',
            'faceoff': 'FACEOFF',
            'lpr': 'LPR',
            'dumpin': 'DUMPIN',
            'dumpinagainst': 'DUMPIN_AGAINST',
            'entry': 'ENTRY',
            'exit': 'EXIT',
            'hit': 'HIT',
            'penalty': 'PENALTY',
            'block': 'BLOCK',
            'giveaway': 'GIVEAWAY',
            'takeaway': 'TAKEAWAY'
        }
        
        # Strength categorization
        self.strength_mapping = {
            'evenStrength': 'EV',
            'shortHanded': 'PK', 
            'powerPlay': 'PP',
            'emptyNet': 'EN',
            '3v3': '3v3',
            'shootout': 'SO',
            '4v4': '4v4',
            '5v3': '5v3',
            '3v5': '3v5'
        }

    def parse_period_time(self, period_time: str) -> Optional[int]:
        """Convert period time MM:SS to seconds"""
        if pd.isna(period_time) or period_time == '':
            return None
            
        try:
            if isinstance(period_time, (int, float)):
                # Already in seconds
                return int(period_time * 60) if period_time < 100 else int(period_time)
                
            time_str = str(period_time)
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    minutes, seconds = parts
                    return int(minutes) * 60 + int(float(seconds))
            else:
                # Decimal minutes
                return int(float(time_str) * 60)
        except (ValueError, TypeError):
            return None

    def normalize_event_type(self, event_type: str) -> str:
        """Normalize event types to standard enum"""
        if pd.isna(event_type):
            return 'UNKNOWN'
            
        event_lower = str(event_type).lower().strip()
        return self.event_type_mapping.get(event_lower, event_type.upper())

    def normalize_strength(self, strength: str) -> str:
        """Normalize strength situations"""
        if pd.isna(strength):
            return 'EV'
            
        return self.strength_mapping.get(str(strength), 'EV')

    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize full team names to abbreviations"""
        if pd.isna(team_name):
            return 'UNK'
            
        team_mapping = {
            'Montreal Canadiens': 'MTL',
            'Toronto Maple Leafs': 'TOR',
            'Boston Bruins': 'BOS',
            'Tampa Bay Lightning': 'TBL',
            'Florida Panthers': 'FLA',
            'Ottawa Senators': 'OTT',
            'Buffalo Sabres': 'BUF',
            'Detroit Red Wings': 'DET',
            'New York Rangers': 'NYR',
            'New York Islanders': 'NYI',
            'New Jersey Devils': 'NJD',
            'Philadelphia Flyers': 'PHI',
            'Pittsburgh Penguins': 'PIT',
            'Washington Capitals': 'WSH',
            'Carolina Hurricanes': 'CAR',
            'Columbus Blue Jackets': 'CBJ',
            'Chicago Blackhawks': 'CHI',
            'Colorado Avalanche': 'COL',
            'Dallas Stars': 'DAL',
            'Minnesota Wild': 'MIN',
            'Nashville Predators': 'NSH',
            'St. Louis Blues': 'STL',
            'Winnipeg Jets': 'WPG',
            'Calgary Flames': 'CGY',
            'Edmonton Oilers': 'EDM',
            'Vancouver Canucks': 'VAN',
            'Seattle Kraken': 'SEA',
            'Los Angeles Kings': 'LAK',
            'San Jose Sharks': 'SJS',
            'Anaheim Ducks': 'ANA',
            'Vegas Golden Knights': 'VGK',
            'Utah Mammoth': 'UTA'
        }
        
        team_str = str(team_name)
        return team_mapping.get(team_str, team_str[:3].upper())

    def create_canonical_player_id(self, player_ref_id: str, first_name: str, last_name: str) -> str:
        """Create canonical player ID format"""
        if pd.notna(player_ref_id) and str(player_ref_id).strip():
            return f"nhl_{player_ref_id}"
        elif pd.notna(first_name) and pd.notna(last_name):
            # Fallback to name-based ID
            name_id = f"{first_name}_{last_name}".lower().replace(' ', '_')
            return f"name_{name_id}"
        else:
            return "unknown"

    def normalize_coordinates(self, x_coord: float, y_coord: float) -> tuple:
        """Normalize coordinates to standard NHL system"""
        if pd.isna(x_coord) or pd.isna(y_coord):
            return None, None
            
        # Assuming current coords are in feet, convert to standard NHL coords
        # NHL standard: center ice (0,0), range roughly [-100,100] x [-42.5,42.5]
        try:
            # Simple conversion - adjust based on your coordinate system
            norm_x = float(x_coord)
            norm_y = float(y_coord)
            
            # Clamp to reasonable bounds
            norm_x = max(-110, min(110, norm_x))
            norm_y = max(-50, min(50, norm_y))
            
            return norm_x, norm_y
        except (ValueError, TypeError):
            return None, None

    def extract_on_ice_players(self, forwards_refs: str, defensemen_refs: str, goalie_ref: str) -> List[str]:
        """Extract canonical on-ice player IDs"""
        players = []
        
        for refs in [forwards_refs, defensemen_refs]:
            if pd.notna(refs) and str(refs).strip():
                # Parse comma-separated player reference IDs
                ref_ids = str(refs).replace('\t', '').split(',')
                for ref_id in ref_ids:
                    ref_id = ref_id.strip()
                    if ref_id:
                        players.append(f"nhl_{ref_id}")
        
        if pd.notna(goalie_ref) and str(goalie_ref).strip():
            players.append(f"nhl_{str(goalie_ref).strip()}")
            
        return players

    def migrate_schema(self, input_file: str, output_file: str) -> pd.DataFrame:
        """Main migration function"""
        print(f"Starting PBP schema migration...")
        print(f"Input: {input_file}")
        print(f"Output: {output_file}")
        
        # Load current parquet
        print("Loading current parquet file...")
        df = pd.read_parquet(input_file)
        print(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
        
        # Create new schema
        print("Applying schema transformations...")
        
        # 1. Keys & identity
        df_new = pd.DataFrame()
        df_new['season'] = pd.Series([self.season] * len(df), dtype='string')
        df_new['game_id'] = df['gameReferenceId'].astype('int32')
        df_new['row_id'] = np.arange(len(df), dtype='int64')
        
        # 2. Time normalization
        df_new['period'] = df['period'].astype('int8')
        df_new['periodTime'] = df['periodTime'].apply(
            lambda x: f"{int(x//60):02d}:{int(x%60):02d}" if pd.notna(x) and x >= 0 else "00:00"
        )
        df_new['period_seconds'] = df['periodTime'].apply(self.parse_period_time)
        df_new['gameTime'] = df['gameTime'].fillna(0).astype('int32')
        
        # 3. Event & team
        df_new['event_type'] = df['name'].apply(self.normalize_event_type)
        df_new['team_abbr'] = df['team'].apply(self._normalize_team_name).fillna('UNK').astype('string')
        df_new['strength'] = df['manpowerSituation'].apply(self.normalize_strength)
        
        # 4. Players
        # Create primary player ID
        df_new['player_id'] = df.apply(
            lambda row: self.create_canonical_player_id(
                row.get('playerReferenceId'), 
                row.get('playerFirstName'), 
                row.get('playerLastName')
            ), axis=1
        ).astype('string')
        
        # Extract on-ice players
        df_new['on_ice_ids'] = df.apply(
            lambda row: self.extract_on_ice_players(
                row.get('teamForwardsOnIceRefs', ''),
                row.get('teamDefencemenOnIceRefs', ''),
                row.get('teamGoalieOnIceRef', '')
            ), axis=1
        )
        
        # 5. Location (unified units)
        coords = df[['xCoord', 'yCoord']].apply(
            lambda row: self.normalize_coordinates(row['xCoord'], row['yCoord']), axis=1
        )
        df_new['x_coord'] = coords.apply(lambda x: x[0] if x[0] is not None else np.nan).astype('float32')
        df_new['y_coord'] = coords.apply(lambda x: x[1] if x[1] is not None else np.nan).astype('float32')
        
        # 6. Quality features
        if 'expectedGoalsOnNet' in df.columns:
            df_new['xg'] = pd.to_numeric(df['expectedGoalsOnNet'], errors='coerce').astype('float32')
        else:
            df_new['xg'] = np.nan
            
        df_new['shot_result'] = df['outcome'].fillna('UNKNOWN').astype('string')
        df_new['zone'] = df['zone'].fillna('nz').astype('string')
        
        # 7. Additional context
        df_new['possession_team'] = df['teamInPossession'].fillna('').astype('string')
        df_new['is_possession_event'] = df['isPossessionEvent'].map({'true': True, 'false': False}).fillna(False)
        df_new['score_differential'] = df['scoreDifferential'].fillna(0).astype('int8')
        
        # 8. Provenance
        df_new['ingest_ts'] = self.ingest_timestamp
        df_new['source_file'] = df.get('source_file', 'unified_pbp_2024_2025.csv').astype('string')
        df_new['version'] = self.version
        
        # Data quality checks
        print("Performing data quality checks...")
        self._validate_migrated_data(df_new)
        
        # Sort for optimal querying
        print("Sorting data for optimal querying...")
        df_new = df_new.sort_values(['game_id', 'period', 'period_seconds', 'row_id']).reset_index(drop=True)
        
        # Update row_id to reflect new ordering
        df_new['row_id'] = np.arange(len(df_new), dtype='int64')
        
        # Save migrated data
        print(f"Saving migrated parquet to: {output_file}")
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df_new.to_parquet(
            output_file, 
            engine='pyarrow',
            compression='zstd',
            index=False
        )
        
        # Print summary
        print("\n=== MIGRATION SUMMARY ===")
        print(f"Original rows: {len(df):,}")
        print(f"Migrated rows: {len(df_new):,}")
        print(f"Original columns: {len(df.columns)}")
        print(f"Migrated columns: {len(df_new.columns)}")
        print(f"Unique games: {df_new['game_id'].nunique()}")
        print(f"Date range: {df_new['season'].iloc[0]}")
        print(f"File size: {Path(output_file).stat().st_size / (1024*1024):.2f} MB")
        
        return df_new

    def _validate_migrated_data(self, df: pd.DataFrame):
        """Validate migrated data quality"""
        issues = []
        
        # Required fields
        required_fields = ['season', 'game_id', 'row_id', 'period']
        for field in required_fields:
            null_count = df[field].isnull().sum()
            if null_count > 0:
                issues.append(f"{field}: {null_count} null values")
        
        # Row IDs should be unique and sequential
        if not df['row_id'].is_unique:
            issues.append("row_id: Not unique")
            
        # Period seconds parsing
        parsed_seconds = df['period_seconds'].notna().sum()
        total_rows = len(df)
        parse_rate = parsed_seconds / total_rows * 100
        if parse_rate < 95:
            issues.append(f"period_seconds: Only {parse_rate:.1f}% parsed successfully")
        
        # Coordinate bounds
        x_out_of_bounds = ((df['x_coord'] < -120) | (df['x_coord'] > 120)).sum()
        y_out_of_bounds = ((df['y_coord'] < -60) | (df['y_coord'] > 60)).sum()
        if x_out_of_bounds > 0:
            issues.append(f"x_coord: {x_out_of_bounds} values out of bounds")
        if y_out_of_bounds > 0:
            issues.append(f"y_coord: {y_out_of_bounds} values out of bounds")
            
        # XG bounds
        if 'xg' in df.columns:
            xg_out_of_bounds = ((df['xg'] < 0) | (df['xg'] > 1)).sum()
            if xg_out_of_bounds > 0:
                issues.append(f"xg: {xg_out_of_bounds} values out of [0,1] bounds")
        
        if issues:
            print("Data quality issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("All data quality checks passed!")

def main():
    """Main execution function"""
    migrator = PBPSchemaMigrator()
    
    # Define file paths
    input_file = migrator.processed_path / "analytics" / "mtl_play_by_play" / "unified_play_by_play_2024_2025.parquet"
    output_file = migrator.processed_path / "fact" / "pbp" / f"unified_pbp_{migrator.season}.parquet"
    
    # Create backup of original
    backup_file = input_file.with_suffix('.parquet.backup')
    if not backup_file.exists():
        print(f"Creating backup: {backup_file}")
        import shutil
        shutil.copy2(input_file, backup_file)
    
    # Perform migration
    df_migrated = migrator.migrate_schema(str(input_file), str(output_file))
    
    print("\nMigration completed successfully!")
    print(f"New schema available at: {output_file}")
    
    return df_migrated

if __name__ == "__main__":
    main()
