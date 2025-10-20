#!/usr/bin/env python3
"""
CSV to Parquet Converter
========================

Simple utility to convert CSV files to Parquet format for efficient storage
and analysis of hockey data.
"""

import pandas as pd
from pathlib import Path
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_csv_to_parquet(csv_path: str, output_dir: str = None) -> str:
    """
    Convert a CSV file to Parquet format.

    Args:
        csv_path: Path to the input CSV file
        output_dir: Directory to save the Parquet file (optional)

    Returns:
        Path to the created Parquet file
    """
    try:
        csv_file = Path(csv_path)

        # Verify input file exists
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Read CSV file
        logger.info(f"Reading CSV file: {csv_path}")
        df = pd.read_csv(csv_file)

        # Generate output path
        if output_dir:
            output_directory = Path(output_dir)
        else:
            # Default to same directory as CSV file
            output_directory = csv_file.parent

        # Create output filename with .parquet extension
        output_filename = csv_file.stem + ".parquet"
        output_path = output_directory / output_filename

        # Convert to Parquet
        logger.info(f"Converting to Parquet format: {output_path}")
        df.to_parquet(output_path, index=False)

        logger.info(f"Successfully converted {len(df)} rows and {len(df.columns)} columns")
        logger.info(f"Output file: {output_path}")

        return str(output_path)

    except Exception as e:
        logger.error(f"Error converting CSV to Parquet: {e}")
        raise

def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python csv_to_parquet_converter.py <csv_file_path> [output_directory]")
        print("Example: python csv_to_parquet_converter.py data/mtl_season_results/2024-2025/mtl_season_game_results_2024-2025.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result_path = convert_csv_to_parquet(csv_path, output_dir)
        print(f"Conversion completed successfully: {result_path}")
    except Exception as e:
        print(f"Conversion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
