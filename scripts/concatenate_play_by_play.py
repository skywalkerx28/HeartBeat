#!/usr/bin/env python3
"""
Play-by-Play Data Concatenation Script

This script concatenates all 82 NHL play-by-play CSV files from the 2024-2025 season
into a single unified dataset for analysis and processing.

Features:
- Handles identical column formatting across all files
- Adds game metadata for tracking
- Provides progress updates during concatenation
- Outputs to processed data directory
"""

import pandas as pd
import os
import glob
from pathlib import Path
import time

def concatenate_play_by_play_data():
    """
    Concatenate all play-by-play CSV files into a single dataset.

    Returns:
        pd.DataFrame: Concatenated play-by-play data
    """

    # Define paths
    play_by_play_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/play_by_play")
    output_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/processed")
    output_file = output_dir / "unified_play_by_play_2024_2025.csv"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all CSV files
    csv_files = list(play_by_play_dir.glob("*.csv"))
    csv_files.sort()  # Sort for consistent processing order

    print(f"Found {len(csv_files)} CSV files to concatenate")

    if len(csv_files) == 0:
        print("No CSV files found in the play_by_play directory!")
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

            # Add game identifier column from filename
            game_id = csv_file.stem.split('-')[5]  # Extract game ID from filename
            df['game_id'] = game_id

            # Add source file for tracking
            df['source_file'] = csv_file.name

            dfs.append(df)
            total_rows += len(df)

            print(f"  - Added {len(df)} rows from {csv_file.name}")

        except Exception as e:
            print(f"Error processing {csv_file.name}: {str(e)}")
            continue

    # Concatenate all DataFrames
    print(f"\nConcatenating {len(dfs)} DataFrames...")
    start_time = time.time()

    unified_df = pd.concat(dfs, ignore_index=True)

    concat_time = time.time() - start_time
    print(f"Concatenation completed in {concat_time:.2f} seconds")
    # Save to CSV
    print(f"Saving unified dataset to: {output_file}")
    unified_df.to_csv(output_file, index=False)

    # Print summary
    print("\n=== CONCATENATION SUMMARY ===")
    print(f"Total files processed: {len(dfs)}")
    print(f"Total rows: {len(unified_df):,}")
    print(f"Total columns: {len(unified_df.columns)}")
    print(f"Output file: {output_file}")
    print(f"File size: {output_file.stat().st_size / (1024*1024):.2f} MB")

    # Display column information
    print("\nColumns in unified dataset:")
    for col in unified_df.columns:
        print(f"  - {col}")

    return unified_df

def validate_concatenation(df):
    """
    Validate the concatenated dataset for consistency and completeness.

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

    # Check unique games
    unique_games = df['game_id'].nunique()
    print(f"✓ Unique games identified: {unique_games}")

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

if __name__ == "__main__":
    print("Starting Play-by-Play Data Concatenation...")
    print("=" * 50)

    # Concatenate the data
    unified_data = concatenate_play_by_play_data()

    if unified_data is not None:
        # Validate the result
        validate_concatenation(unified_data)

        print("\n" + "=" * 50)
        print("✅ Concatenation completed successfully!")
    else:
        print("❌ Concatenation failed!")
