#!/usr/bin/env python3
"""
Matchup Reports Concatenation Script

This script concatenates all Montreal vs opponent matchup report CSV files
into a single unified dataset for comparative analysis.

Features:
- Extracts opponent team names from filenames
- Adds opponent_team column for easy filtering
- Handles identical column formatting across all files
- Provides progress updates during concatenation
- Outputs to processed data directory
"""

import pandas as pd
import os
import glob
from pathlib import Path
import time

def concatenate_matchup_reports():
    """
    Concatenate all matchup report CSV files into a single dataset.

    Returns:
        pd.DataFrame: Concatenated matchup reports data
    """

    # Define paths
    matchup_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/matchup_reports/2024-2025")
    output_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/processed")
    output_file = output_dir / "unified_matchup_reports_2024_2025.csv"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all CSV files
    csv_files = list(matchup_dir.glob("*.csv"))
    csv_files.sort()  # Sort for consistent processing order

    print(f"Found {len(csv_files)} matchup report CSV files to concatenate")

    if len(csv_files) == 0:
        print("No CSV files found in the matchup_reports directory!")
        return None

    # Initialize list to store DataFrames
    dfs = []
    total_rows = 0

    # Process each CSV file
    for i, csv_file in enumerate(csv_files, 1):
        try:
            print(f"Processing file {i}/{len(csv_files)}: {csv_file.name}")

            # Read CSV file
            df = pd.read_csv(csv_file)

            # Extract opponent team name from filename
            # Format: Season-Report-Montreal-vs-{Opponent}.csv
            filename_parts = csv_file.stem.split('-vs-')
            if len(filename_parts) == 2:
                opponent_team = filename_parts[1]  # Get opponent team name
            else:
                opponent_team = "Unknown"

            # Add opponent team column
            df['opponent_team'] = opponent_team

            # Add source file for tracking
            df['source_file'] = csv_file.name

            dfs.append(df)
            total_rows += len(df)

            print(f"  - Added matchup vs {opponent_team} ({len(df)} rows)")

        except Exception as e:
            print(f"Error processing {csv_file.name}: {str(e)}")
            continue

    # Concatenate all DataFrames
    print(f"\nConcatenating {len(dfs)} matchup reports...")
    start_time = time.time()

    unified_df = pd.concat(dfs, ignore_index=True)

    concat_time = time.time() - start_time
    print(f"Concatenation completed in {concat_time:.2f} seconds")
    # Save to CSV
    print(f"Saving unified dataset to: {output_file}")
    unified_df.to_csv(output_file, index=False)

    # Print summary
    print("\n=== MATCHUP REPORTS CONCATENATION SUMMARY ===")
    print(f"Total files processed: {len(dfs)}")
    print(f"Total rows: {len(unified_df):,}")
    print(f"Total columns: {len(unified_df.columns)}")
    print(f"Output file: {output_file}")
    print(f"File size: {output_file.stat().st_size / (1024*1024):.2f} MB")

    # Display unique opponents
    unique_opponents = unified_df['opponent_team'].unique()
    print(f"\nUnique opponents identified: {len(unique_opponents)}")
    print("Opponent teams:")
    for opponent in sorted(unique_opponents):
        print(f"  - {opponent}")

    return unified_df

def validate_matchup_data(df):
    """
    Validate the concatenated matchup dataset.

    Args:
        df (pd.DataFrame): The concatenated DataFrame to validate
    """

    print("\n=== VALIDATION RESULTS ===")

    # Check for missing values
    missing_data = df.isnull().sum()
    missing_cols = missing_data[missing_data > 0]

    if len(missing_cols) > 0:
        print("Columns with missing values:")
        for col, count in missing_cols.items():
            pct = (count / len(df)) * 100
            print(".1f")
    else:
        print("✓ No missing values found")

    # Check unique opponents
    unique_games = df['opponent_team'].nunique()
    print(f"✓ Unique opponents identified: {unique_games}")

    # Check data types
    print("\nColumn data types:")
    for col, dtype in df.dtypes.items():
        print(f"  - {col}: {dtype}")

    # Check for duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        print(f"⚠ Warning: {duplicates} duplicate rows found")
    else:
        print("✓ No duplicate rows found")

def get_team_performance_summary(df):
    """
    Generate a summary of Montreal's performance against each opponent.

    Args:
        df (pd.DataFrame): The concatenated matchup DataFrame
    """

    print("\n=== MONTREAL PERFORMANCE SUMMARY ===")

    # Get key performance metrics
    performance_cols = [
        'ES Expected Goals For',
        'ES Goals Scored',
        'PP Expected Goals For',
        'PP Goals Scored',
        'Goalie ES Save%'
    ]

    available_cols = [col for col in performance_cols if col in df.columns]

    if available_cols:
        print("Average performance metrics across all matchups:")
        for col in available_cols:
            avg_value = df[col].mean()
            print(".3f")

    # Show top performing matchups
    if 'ES Goals Scored' in df.columns:
        print("\nTop matchups by ES Goals Scored:")
        top_games = df.nlargest(5, 'ES Goals Scored')[['opponent_team', 'ES Goals Scored', 'ES Expected Goals For']]
        for _, row in top_games.iterrows():
            print(f"  - vs {row['opponent_team']}: {row['ES Goals Scored']} goals ({row['ES Expected Goals For']:.2f} xG)")

if __name__ == "__main__":
    print("Starting Matchup Reports Concatenation...")
    print("=" * 50)

    # Concatenate the data
    unified_data = concatenate_matchup_reports()

    if unified_data is not None:
        # Validate the result
        validate_matchup_data(unified_data)

        # Generate performance summary
        get_team_performance_summary(unified_data)

        print("\n" + "=" * 50)
        print("✅ Matchup reports concatenation completed successfully!")
    else:
        print("❌ Concatenation failed!")
