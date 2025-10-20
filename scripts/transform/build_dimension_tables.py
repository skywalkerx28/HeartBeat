#!/usr/bin/env python3
"""
Dimension Tables Builder

Creates clean, normalized dimension tables for players and teams
to support stable joins and Pinecone filtering.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import time
from datetime import datetime
from typing import Dict, List, Set, Any
import requests

class DimensionTableBuilder:
    """Builds normalized dimension tables for hockey data"""
    
    def __init__(self, base_path: str = "/Users/xavier.bouchard/Desktop/HeartBeat"):
        self.base_path = Path(base_path)
        self.data_path = self.base_path / "data"
        self.processed_path = self.data_path / "processed"
        self.dim_path = self.processed_path / "dim"
        
        # Ensure dim directory exists
        self.dim_path.mkdir(parents=True, exist_ok=True)
        
        self.season = "2024-25"
        self.version = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # NHL team mappings
        self.nhl_teams = {
            'ANA': {'name': 'Anaheim Ducks', 'conference': 'Western', 'division': 'Pacific'},
            'BOS': {'name': 'Boston Bruins', 'conference': 'Eastern', 'division': 'Atlantic'},
            'BUF': {'name': 'Buffalo Sabres', 'conference': 'Eastern', 'division': 'Atlantic'},
            'CAR': {'name': 'Carolina Hurricanes', 'conference': 'Eastern', 'division': 'Metropolitan'},
            'CBJ': {'name': 'Columbus Blue Jackets', 'conference': 'Eastern', 'division': 'Metropolitan'},
            'CGY': {'name': 'Calgary Flames', 'conference': 'Western', 'division': 'Pacific'},
            'CHI': {'name': 'Chicago Blackhawks', 'conference': 'Western', 'division': 'Central'},
            'COL': {'name': 'Colorado Avalanche', 'conference': 'Western', 'division': 'Central'},
            'DAL': {'name': 'Dallas Stars', 'conference': 'Western', 'division': 'Central'},
            'DET': {'name': 'Detroit Red Wings', 'conference': 'Eastern', 'division': 'Atlantic'},
            'EDM': {'name': 'Edmonton Oilers', 'conference': 'Western', 'division': 'Pacific'},
            'FLA': {'name': 'Florida Panthers', 'conference': 'Eastern', 'division': 'Atlantic'},
            'LAK': {'name': 'Los Angeles Kings', 'conference': 'Western', 'division': 'Pacific'},
            'MIN': {'name': 'Minnesota Wild', 'conference': 'Western', 'division': 'Central'},
            'MTL': {'name': 'Montreal Canadiens', 'conference': 'Eastern', 'division': 'Atlantic'},
            'NJD': {'name': 'New Jersey Devils', 'conference': 'Eastern', 'division': 'Metropolitan'},
            'NSH': {'name': 'Nashville Predators', 'conference': 'Western', 'division': 'Central'},
            'NYI': {'name': 'New York Islanders', 'conference': 'Eastern', 'division': 'Metropolitan'},
            'NYR': {'name': 'New York Rangers', 'conference': 'Eastern', 'division': 'Metropolitan'},
            'OTT': {'name': 'Ottawa Senators', 'conference': 'Eastern', 'division': 'Atlantic'},
            'PHI': {'name': 'Philadelphia Flyers', 'conference': 'Eastern', 'division': 'Metropolitan'},
            'PIT': {'name': 'Pittsburgh Penguins', 'conference': 'Eastern', 'division': 'Metropolitan'},
            'SEA': {'name': 'Seattle Kraken', 'conference': 'Western', 'division': 'Pacific'},
            'SJS': {'name': 'San Jose Sharks', 'conference': 'Western', 'division': 'Pacific'},
            'STL': {'name': 'St. Louis Blues', 'conference': 'Western', 'division': 'Central'},
            'TBL': {'name': 'Tampa Bay Lightning', 'conference': 'Eastern', 'division': 'Atlantic'},
            'TOR': {'name': 'Toronto Maple Leafs', 'conference': 'Eastern', 'division': 'Atlantic'},
            'UTA': {'name': 'Utah Hockey Club', 'conference': 'Western', 'division': 'Central'},
            'VAN': {'name': 'Vancouver Canucks', 'conference': 'Western', 'division': 'Pacific'},
            'VGK': {'name': 'Vegas Golden Knights', 'conference': 'Western', 'division': 'Pacific'},
            'WPG': {'name': 'Winnipeg Jets', 'conference': 'Western', 'division': 'Central'},
            'WSH': {'name': 'Washington Capitals', 'conference': 'Eastern', 'division': 'Metropolitan'}
        }

    def build_teams_dimension(self) -> pd.DataFrame:
        """Build teams dimension table"""
        print("Building teams dimension table...")
        
        teams_data = []
        for abbr, info in self.nhl_teams.items():
            teams_data.append({
                'team_id': f"nhl_{abbr.lower()}",
                'team_abbr': abbr,
                'team_name': info['name'],
                'conference': info['conference'],
                'division': info['division'],
                'season': self.season,
                'is_active': True,
                'created_ts': int(time.time()),
                'version': self.version
            })
        
        df_teams = pd.DataFrame(teams_data)
        
        # Save to parquet
        output_file = self.dim_path / "teams.parquet"
        df_teams.to_parquet(output_file, index=False, compression='zstd')
        
        print(f"Teams dimension saved: {output_file}")
        print(f"Teams count: {len(df_teams)}")
        
        return df_teams

    def extract_players_from_pbp(self, pbp_file: str) -> pd.DataFrame:
        """Extract unique players from PBP data"""
        print(f"Extracting players from PBP: {pbp_file}")
        
        # Load PBP data
        df_pbp = pd.read_parquet(pbp_file)
        
        # Extract unique player combinations
        players_data = []
        seen_players = set()
        
        for _, row in df_pbp.iterrows():
            # Extract primary player info
            player_ref_id = row.get('playerReferenceId')
            first_name = row.get('playerFirstName')
            last_name = row.get('playerLastName')
            position = row.get('playerPosition')
            team = row.get('team')
            jersey = row.get('playerJersey')
            
            if pd.notna(player_ref_id):
                player_key = str(player_ref_id)
                if player_key not in seen_players:
                    seen_players.add(player_key)
                    
                    # Create canonical player ID
                    player_id = f"nhl_{player_ref_id}"
                    
                    # Map team name to abbreviation
                    team_abbr = self._map_team_to_abbr(str(team) if pd.notna(team) else '')
                    
                    players_data.append({
                        'player_id': player_id,
                        'nhl_id': int(player_ref_id) if str(player_ref_id).isdigit() else None,
                        'first_name': str(first_name) if pd.notna(first_name) else '',
                        'last_name': str(last_name) if pd.notna(last_name) else '',
                        'full_name': f"{first_name} {last_name}".strip() if pd.notna(first_name) and pd.notna(last_name) else '',
                        'position': str(position) if pd.notna(position) else 'UNK',
                        'team_abbr': team_abbr,
                        'jersey_number': int(jersey) if pd.notna(jersey) and str(jersey).isdigit() else None,
                        'shoots': None,  # Not available in current data
                        'first_seen_ts': int(time.time()),
                        'last_seen_ts': int(time.time()),
                        'games_played': 1,  # Will be updated in aggregation
                        'is_active': True,
                        'season': self.season,
                        'version': self.version
                    })
        
        df_players = pd.DataFrame(players_data)
        
        print(f"Extracted {len(df_players)} unique players")
        return df_players

    def _map_team_to_abbr(self, team_name: str) -> str:
        """Map full team name to abbreviation"""
        if not team_name:
            return 'UNK'
            
        # Direct mapping for common team names
        team_mappings = {
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
            'Utah Hockey Club': 'UTA'
        }
        
        return team_mappings.get(team_name, 'UNK')

    def enhance_players_with_stats(self, df_players: pd.DataFrame) -> pd.DataFrame:
        """Enhance players dimension with stats from NHL player files"""
        print("Enhancing players with additional stats...")
        
        # Try to load MTL player stats for additional info
        mtl_stats_path = self.data_path / "nhl_player_stats" / "MTL"
        
        if mtl_stats_path.exists():
            # Load skater stats
            for stats_file in mtl_stats_path.glob("*.csv"):
                try:
                    df_stats = pd.read_csv(stats_file)
                    print(f"Loaded stats from: {stats_file.name}")
                    
                    # Try to merge additional info
                    if 'Player' in df_stats.columns and 'Pos' in df_stats.columns:
                        for _, stat_row in df_stats.iterrows():
                            player_name = stat_row['Player']
                            position = stat_row['Pos']
                            
                            # Find matching player in dimension
                            matches = df_players[df_players['full_name'].str.contains(player_name, na=False)]
                            if len(matches) > 0:
                                df_players.loc[matches.index, 'position'] = position
                                
                except Exception as e:
                    print(f"Error processing {stats_file}: {e}")
        
        return df_players

    def build_players_dimension(self, pbp_file: str) -> pd.DataFrame:
        """Build players dimension table from PBP data"""
        print("Building players dimension table...")
        
        # Extract players from PBP
        df_players = self.extract_players_from_pbp(pbp_file)
        
        # Enhance with additional stats if available
        df_players = self.enhance_players_with_stats(df_players)
        
        # Aggregate player statistics
        df_players = self._aggregate_player_stats(df_players, pbp_file)
        
        # Save to parquet
        output_file = self.dim_path / "players.parquet"
        df_players.to_parquet(output_file, index=False, compression='zstd')
        
        print(f"Players dimension saved: {output_file}")
        print(f"Players count: {len(df_players)}")
        
        return df_players

    def _aggregate_player_stats(self, df_players: pd.DataFrame, pbp_file: str) -> pd.DataFrame:
        """Add aggregated stats from PBP data"""
        print("Aggregating player statistics...")
        
        try:
            df_pbp = pd.read_parquet(pbp_file)
            
            # Create player stats aggregations
            player_stats = {}
            
            for _, row in df_pbp.iterrows():
                player_ref = row.get('playerReferenceId')
                if pd.notna(player_ref):
                    player_id = f"nhl_{player_ref}"
                    game_id = row.get('gameReferenceId')
                    
                    if player_id not in player_stats:
                        player_stats[player_id] = {
                            'games': set(),
                            'events': 0,
                            'shots': 0,
                            'goals': 0,
                            'assists': 0
                        }
                    
                    if pd.notna(game_id):
                        player_stats[player_id]['games'].add(game_id)
                    
                    player_stats[player_id]['events'] += 1
                    
                    # Count specific event types
                    event_type = str(row.get('name', '')).lower()
                    if 'shot' in event_type:
                        player_stats[player_id]['shots'] += 1
                    if 'goal' in event_type:
                        player_stats[player_id]['goals'] += 1
            
            # Update player dimension with stats
            for _, player_row in df_players.iterrows():
                player_id = player_row['player_id']
                if player_id in player_stats:
                    stats = player_stats[player_id]
                    df_players.loc[df_players['player_id'] == player_id, 'games_played'] = len(stats['games'])
                    
        except Exception as e:
            print(f"Error aggregating player stats: {e}")
        
        return df_players

    def build_all_dimensions(self) -> Dict[str, pd.DataFrame]:
        """Build all dimension tables"""
        print("Building all dimension tables...")
        
        # Build teams dimension
        df_teams = self.build_teams_dimension()
        
        # Build players dimension
        pbp_file = self.processed_path / "analytics" / "mtl_play_by_play" / "unified_play_by_play_2024_2025.parquet"
        df_players = self.build_players_dimension(str(pbp_file))
        
        # Validation
        self._validate_dimensions(df_teams, df_players)
        
        print("\n=== DIMENSION TABLES SUMMARY ===")
        print(f"Teams: {len(df_teams)} records")
        print(f"Players: {len(df_players)} records")
        print(f"Output directory: {self.dim_path}")
        
        return {
            'teams': df_teams,
            'players': df_players
        }

    def _validate_dimensions(self, df_teams: pd.DataFrame, df_players: pd.DataFrame):
        """Validate dimension table quality"""
        print("Validating dimension tables...")
        
        issues = []
        
        # Teams validation
        if not df_teams['team_id'].is_unique:
            issues.append("Teams: team_id not unique")
        if not df_teams['team_abbr'].is_unique:
            issues.append("Teams: team_abbr not unique")
        
        # Players validation
        if not df_players['player_id'].is_unique:
            issues.append("Players: player_id not unique")
        
        null_names = df_players['full_name'].isnull().sum()
        if null_names > 0:
            issues.append(f"Players: {null_names} null full_name values")
        
        if issues:
            print("Dimension validation issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("All dimension validation checks passed!")

def main():
    """Main execution function"""
    builder = DimensionTableBuilder()
    dimensions = builder.build_all_dimensions()
    
    print("\nDimension tables built successfully!")
    return dimensions

if __name__ == "__main__":
    main()
