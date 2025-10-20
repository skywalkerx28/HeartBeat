"""
Merge League Player Stats

This script merges advanced and general stats for both forwards and defensemen
into a single unified file per season.

INPUT:
- data/processed/league_player_stats/{season}/forwards/advanced/
- data/processed/league_player_stats/{season}/forwards/general/
- data/processed/league_player_stats/{season}/defensemen/advanced/
- data/processed/league_player_stats/{season}/defensemen/general/

OUTPUT:
- data/processed/league_player_stats/{season}/unified_player_stats_{season}.csv

Author: HeartBeat Engine
Date: October 2025
"""

import pandas as pd
import os
from pathlib import Path

def standardize_team_names(df: pd.DataFrame, team_col: str = 'Team') -> pd.DataFrame:
    """
    Standardize team abbreviations to 3-letter codes.
    
    Args:
        df: DataFrame with team column
        team_col: Name of the team column
        
    Returns:
        DataFrame with standardized team names
    """
    team_mapping = {
        'Anaheim': 'ANA', 'Arizona': 'ARI', 'Boston': 'BOS', 'Buffalo': 'BUF',
        'Calgary': 'CGY', 'Carolina': 'CAR', 'Chicago': 'CHI', 'Colorado': 'COL',
        'Columbus': 'CBJ', 'Dallas': 'DAL', 'Detroit': 'DET', 'Edmonton': 'EDM',
        'Florida': 'FLA', 'Los Angeles': 'LAK', 'Minnesota': 'MIN', 'Montreal': 'MTL',
        'Nashville': 'NSH', 'New Jersey': 'NJD', 'NY Islanders': 'NYI', 'NY Rangers': 'NYR',
        'Ottawa': 'OTT', 'Philadelphia': 'PHI', 'Pittsburgh': 'PIT', 'San Jose': 'SJS',
        'St. Louis': 'STL', 'Tampa Bay': 'TBL', 'Toronto': 'TOR', 'Vancouver': 'VAN',
        'Washington': 'WSH', 'Winnipeg': 'WPG', 'Vegas': 'VGK', 'Seattle': 'SEA'
    }
    
    df = df.copy()
    df[team_col] = df[team_col].replace(team_mapping)
    return df


def merge_season_stats(season: str, base_path: str) -> pd.DataFrame:
    """
    Merge all player stats (forwards + defensemen, advanced + general) for a given season.
    
    Args:
        season: Season string like '2015-2016'
        base_path: Base directory path
        
    Returns:
        DataFrame with all merged player stats
    """
    
    season_path = Path(base_path) / season
    
    # File paths
    fwd_adv_path = season_path / "forwards/advanced" / f"advanced_forwards_stats_{season.replace('-', '')}.csv"
    fwd_gen_path = season_path / "forwards/general" / f"general_forwards_stats_{season.replace('-', '')}.csv"
    def_adv_path = season_path / "defensemen/advanced" / f"advanced_defensemen_stats_{season.replace('-', '')}.csv"
    def_gen_path = season_path / "defensemen/general" / f"general_defensemen_stats_{season.replace('-', '')}.csv"
    
    print(f"\n{'='*60}")
    print(f"Processing Season: {season}")
    print(f"{'='*60}")
    
    # Load forwards data
    print(f"Loading: {fwd_adv_path.name}")
    fwd_advanced = pd.read_csv(fwd_adv_path)
    print(f"  Rows: {len(fwd_advanced)}, Columns: {len(fwd_advanced.columns)}")
    
    print(f"Loading: {fwd_gen_path.name}")
    fwd_general = pd.read_csv(fwd_gen_path)
    print(f"  Rows: {len(fwd_general)}, Columns: {len(fwd_general.columns)}")
    
    # Load defensemen data
    print(f"Loading: {def_adv_path.name}")
    def_advanced = pd.read_csv(def_adv_path)
    print(f"  Rows: {len(def_advanced)}, Columns: {len(def_advanced.columns)}")
    
    print(f"Loading: {def_gen_path.name}")
    def_general = pd.read_csv(def_gen_path)
    print(f"  Rows: {len(def_general)}, Columns: {len(def_general.columns)}")
    
    # Standardize team names to 3-letter codes
    print("\nStandardizing team names...")
    fwd_advanced = standardize_team_names(fwd_advanced)
    fwd_general = standardize_team_names(fwd_general)
    def_advanced = standardize_team_names(def_advanced)
    def_general = standardize_team_names(def_general)
    
    # Rename overlapping columns in general files before merging
    # Keep the advanced column names as primary
    gen_rename_map = {
        'Total TOI(sec)': 'TOI (sec)',
        'Total TOI(min)': 'TOI (min)',
        'GP': 'Total Games played',
        'TOI/GP(sec)': 'Total TOI/GP (sec)',
        'TOI/GP(min)': 'Total TOI/GP (min)'
    }
    
    fwd_general = fwd_general.rename(columns=gen_rename_map)
    def_general = def_general.rename(columns=gen_rename_map)
    
    # Now merge on Player and Team
    fwd_merged = pd.merge(
        fwd_advanced,
        fwd_general[['Player', 'Team', 'G', 'A', 'PTS', '+/-', 'S', 'Sh%']],
        on=['Player', 'Team'],
        how='left'
    )
    print(f"\nForwards merged: {len(fwd_merged)} players")
    
    def_merged = pd.merge(
        def_advanced,
        def_general[['Player', 'Team', 'G', 'A', 'PTS', '+/-', 'S', 'Sh%']],
        on=['Player', 'Team'],
        how='left'
    )
    print(f"Defensemen merged: {len(def_merged)} players")
    
    # Combine forwards and defensemen
    all_players = pd.concat([fwd_merged, def_merged], ignore_index=True)
    print(f"\nTotal players combined: {len(all_players)}")
    
    # Organize columns in a logical order (flexible based on what exists)
    priority_columns = [
        'Player', 'Position', 'Team',
        'TOI (sec)', 'TOI (min)', 'Total Games played',
        'Total TOI/GP (sec)', 'Total TOI/GP (min)',
        'G', 'A', 'PTS', '+/-', 'S', 'Sh%'
    ]
    
    # Add priority columns that exist
    column_order = [col for col in priority_columns if col in all_players.columns]
    
    # Add all remaining columns (advanced stats) in alphabetical order
    remaining_cols = sorted([col for col in all_players.columns if col not in column_order])
    column_order.extend(remaining_cols)
    
    # Reorder columns
    all_players = all_players[column_order]
    
    # Sort by Position (F first, then D), then by Player name
    all_players['Position'] = all_players['Position'].fillna('D')
    all_players = all_players.sort_values(['Position', 'Player'], ascending=[True, True])
    all_players = all_players.reset_index(drop=True)
    
    return all_players


def main():
    """Main execution function."""
    
    base_path = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/league_player_stats")
    
    # Process all seasons
    seasons = [
        "2015-2016",
        "2016-2017",
        "2017-2018",
        "2018-2019",
        "2019-2020",
        "2020-2021",
        "2021-2022",
        "2022-2023",
        "2023-2024",
        "2024-2025"
    ]
    
    total_success = 0
    total_failed = 0
    
    for season in seasons:
        try:
            # Check if season directory exists
            season_path = base_path / season
            if not season_path.exists():
                print(f"\n[SKIP] Season {season} directory not found")
                continue
            
            # Merge stats
            merged_df = merge_season_stats(season, base_path)
            
            # Save unified file
            output_path = base_path / season / f"unified_player_stats_{season.replace('-', '')}.csv"
            merged_df.to_csv(output_path, index=False)
            
            print(f"\n{'='*60}")
            print(f"SUCCESS: Unified stats saved to:")
            print(f"  {output_path.name}")
            print(f"  Total players: {len(merged_df)}")
            print(f"  Total columns: {len(merged_df.columns)}")
            print(f"{'='*60}")
            
            total_success += 1
            
        except Exception as e:
            print(f"\n[ERROR] Failed to process season {season}: {str(e)}")
            total_failed += 1
            continue
    
    # Final summary
    print(f"\n\n{'#'*60}")
    print(f"MERGE COMPLETE")
    print(f"{'#'*60}")
    print(f"Total seasons processed successfully: {total_success}")
    print(f"Total seasons failed: {total_failed}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()

