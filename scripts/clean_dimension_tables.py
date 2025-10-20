#!/usr/bin/env python3
"""
Clean Dimension Tables

Removes floaty suffixes (.0) from player IDs in dimension tables
for consistency with production chunks.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def clean_players_dimension():
    """Clean player IDs in the players dimension table"""
    print("Cleaning players dimension...")

    base_path = Path("/Users/xavier.bouchard/Desktop/HeartBeat")
    players_file = base_path / "data" / "processed" / "dim" / "players.parquet"

    if not players_file.exists():
        print(f"Players dimension file not found: {players_file}")
        return

    # Read the players dimension
    df_players = pd.read_parquet(players_file)
    print(f"Loaded {len(df_players)} players")

    # Check current format
    sample_ids = df_players['player_id'].head(5).tolist()
    print(f"Sample player IDs before cleaning: {sample_ids}")

    # Clean player_id column
    df_players['player_id'] = df_players['player_id'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Also clean nhl_id if it exists
    if 'nhl_id' in df_players.columns:
        df_players['nhl_id'] = df_players['nhl_id'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Update version timestamp
    df_players['version'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Show sample after cleaning
    sample_ids_cleaned = df_players['player_id'].head(5).tolist()
    print(f"Sample player IDs after cleaning: {sample_ids_cleaned}")

    # Save back to parquet
    df_players.to_parquet(players_file, index=False)
    print(f"Saved cleaned players dimension to {players_file}")

def verify_teams_dimension():
    """Verify teams dimension doesn't need cleaning"""
    print("Checking teams dimension...")

    base_path = Path("/Users/xavier.bouchard/Desktop/HeartBeat")
    teams_file = base_path / "data" / "processed" / "dim" / "teams.parquet"

    if not teams_file.exists():
        print(f"Teams dimension file not found: {teams_file}")
        return

    df_teams = pd.read_parquet(teams_file)
    print(f"Loaded {len(df_teams)} teams")

    # Check for any .0 suffixes
    has_floaty_ids = df_teams['team_id'].astype(str).str.contains(r'\.0$').any()
    if has_floaty_ids:
        print("Warning: Teams dimension has floaty IDs that need cleaning")
    else:
        print("Teams dimension is clean (no floaty IDs)")

def main():
    """Main execution"""
    print("=== DIMENSION TABLE CLEANUP ===")

    clean_players_dimension()
    print()
    verify_teams_dimension()

    print("\n=== CLEANUP COMPLETE ===")
    print("Dimension tables are now consistent with production chunks!")

if __name__ == "__main__":
    main()
