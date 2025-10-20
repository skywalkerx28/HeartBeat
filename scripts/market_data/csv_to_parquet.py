"""
Convert CSV contract data to Parquet format.

Usage: 
    python scripts/market_data/csv_to_parquet.py your_contracts.csv
    python scripts/market_data/csv_to_parquet.py mtl_contracts.csv --type contracts
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.market_data.schemas import (
    PLAYER_CONTRACTS_SCHEMA,
    CONTRACT_PERFORMANCE_INDEX_SCHEMA,
    TEAM_CAP_MANAGEMENT_SCHEMA
)


def convert_contracts_csv(csv_file: str, output_dir: str = "data/processed/market", skiprows: int = 0):
    """Convert player contracts CSV to Parquet."""
    
    print(f"Converting contracts from: {csv_file}")
    
    # Load CSV (skip header rows if needed)
    if skiprows > 0:
        df = pd.read_csv(csv_file, skiprows=skiprows)
        print(f"Skipped {skiprows} header rows")
    else:
        df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} contracts")
    
    # Clean data: Replace text in numeric fields with NaN
    # Some rows may have "roster", "minors", etc. in wrong columns
    numeric_cols = ['years_remaining', 'contract_years_total', 'age', 'signing_age']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Type conversions (fill NaN with 0 for integer fields)
    df['nhl_player_id'] = df['nhl_player_id'].astype('int64')
    df['age'] = df['age'].fillna(0).astype('int32')
    df['cap_hit'] = df['cap_hit'].astype('float64')
    if 'retained_percentage' in df.columns:
        df['retained_percentage'] = df['retained_percentage'].fillna(0.0).astype('float64')
    else:
        df['retained_percentage'] = 0.0
    
    # Handle years (fill NaN with 0 for unsigned prospects)
    if 'contract_years_total' in df.columns:
        df['contract_years_total'] = df['contract_years_total'].fillna(0).astype('int32')
    else:
        df['contract_years_total'] = df['years_remaining'] + 1  # Estimate
    
    if 'years_remaining' in df.columns:
        df['years_remaining'] = df['years_remaining'].fillna(0).astype('int32')
    else:
        df['years_remaining'] = df['contract_years_total']  # Assume all remaining
    
    if 'signing_age' in df.columns:
        df['signing_age'] = df['signing_age'].fillna(0).astype('int32')
    else:
        df['signing_age'] = (df['age'] - (df['contract_years_total'] - df['years_remaining'])).fillna(0).astype('int32')
    
    # Date conversions (flexible parsing for different formats)
    if 'contract_start_date' in df.columns:
        df['contract_start_date'] = pd.to_datetime(df['contract_start_date'], errors='coerce')
    else:
        df['contract_start_date'] = pd.to_datetime('2024-10-01')
    
    if 'contract_end_date' in df.columns:
        df['contract_end_date'] = pd.to_datetime(df['contract_end_date'], errors='coerce')
    else:
        df['contract_end_date'] = df['contract_start_date'] + pd.DateOffset(years=df['contract_years_total'].astype(int))
    
    if 'signing_date' in df.columns:
        df['signing_date'] = pd.to_datetime(df['signing_date'], errors='coerce')  # Handles various formats
    else:
        df['signing_date'] = df['contract_start_date'] - pd.DateOffset(years=1)
    
    if 'sync_date' in df.columns:
        df['sync_date'] = pd.to_datetime(df['sync_date'], errors='coerce')
    else:
        df['sync_date'] = pd.Timestamp.now()
    
    if 'must_sign_by' in df.columns:
        df['must_sign_by'] = pd.to_datetime(df['must_sign_by'], errors='coerce')
    
    # Draft and UFA fields (nullable integers - fill with 0)
    for int_col in ['draft_year', 'draft_round', 'draft_overall', 'ufa_year']:
        if int_col in df.columns:
            df[int_col] = df[int_col].fillna(0).astype('int32')
    
    # Boolean conversions
    for bool_col in ['no_trade_clause', 'no_movement_clause', 'arbitration_eligible']:
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].map({
                'true': True, 'false': False, 'True': True, 'False': False,
                'TRUE': True, 'FALSE': False,
                True: True, False: False, 1: True, 0: False
            }).fillna(False)
        else:
            df[bool_col] = False
    
    # String defaults
    if 'contract_type' not in df.columns:
        df['contract_type'] = 'UFA'
    if 'signing_team' not in df.columns:
        df['signing_team'] = df['team_abbrev']
    if 'contract_status' not in df.columns:
        df['contract_status'] = 'active'
    if 'season' not in df.columns:
        df['season'] = '2025-2026'
    if 'data_source' not in df.columns:
        df['data_source'] = 'manual'
    
    # Calculate cap_hit_percentage
    df['cap_hit_percentage'] = (df['cap_hit'] / 95500000) * 100
    
    # Ensure all required columns exist
    required_columns = [col for col in PLAYER_CONTRACTS_SCHEMA.names]
    missing = set(required_columns) - set(df.columns)
    
    if missing:
        print(f"❌ Missing required columns: {missing}")
        return False
    
    # Select only schema columns in correct order
    df = df[required_columns]
    
    # Convert to Parquet
    output_path = Path(output_dir) / 'players_contracts_2025_2026.parquet'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df, schema=PLAYER_CONTRACTS_SCHEMA, preserve_index=False)
    
    pq.write_table(
        table,
        str(output_path),
        compression='ZSTD',
        compression_level=3
    )
    
    file_size = output_path.stat().st_size / 1024
    print(f"\n✅ SUCCESS!")
    print(f"   Saved: {output_path}")
    print(f"   Contracts: {len(df)}")
    print(f"   Size: {file_size:.1f} KB")
    
    # Show team breakdown
    print("\n📊 Team Distribution:")
    team_counts = df['team_abbrev'].value_counts()
    for team, count in team_counts.items():
        total_cap = df[df['team_abbrev'] == team]['cap_hit'].sum() / 1000000
        print(f"   {team}: {count} contracts, ${total_cap:.1f}M total cap")
    
    return True


def convert_performance_csv(csv_file: str, output_dir: str = "data/processed/market"):
    """Convert performance index CSV to Parquet."""
    
    print(f"Converting performance index from: {csv_file}")
    
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} performance records")
    
    # Type conversions
    df['nhl_player_id'] = df['nhl_player_id'].astype('int64')
    df['performance_index'] = df['performance_index'].astype('float64')
    df['contract_efficiency'] = df['contract_efficiency'].astype('float64')
    df['market_value'] = df['market_value'].astype('float64')
    df['surplus_value'] = df['surplus_value'].astype('float64')
    df['performance_percentile'] = df['performance_percentile'].astype('float64')
    df['contract_percentile'] = df['contract_percentile'].astype('float64')
    
    # Date conversion
    df['last_calculated'] = pd.to_datetime(df['last_calculated'])
    
    # Defaults
    if 'season' not in df.columns:
        df['season'] = '2025-2026'
    
    # Convert to Parquet
    output_path = Path(output_dir) / 'contract_performance_index_2025_2026.parquet'
    
    table = pa.Table.from_pandas(df, schema=CONTRACT_PERFORMANCE_INDEX_SCHEMA, preserve_index=False)
    
    pq.write_table(
        table,
        str(output_path),
        compression='ZSTD',
        compression_level=3
    )
    
    print(f"\n✅ Saved: {output_path}")
    
    # Show status breakdown
    print("\n📊 Status Distribution:")
    status_counts = df['status'].value_counts()
    for status, count in status_counts.items():
        print(f"   {status}: {count}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Convert CSV to Parquet for market analytics')
    parser.add_argument('csv_file', help='Input CSV file')
    parser.add_argument('--type', default='contracts', choices=['contracts', 'performance', 'cap'],
                       help='Type of data (contracts, performance, cap)')
    parser.add_argument('--output', default='data/processed/market',
                       help='Output directory')
    parser.add_argument('--skiprows', type=int, default=0,
                       help='Number of rows to skip at top of CSV (for header rows)')
    
    args = parser.parse_args()
    
    if not Path(args.csv_file).exists():
        print(f"File not found: {args.csv_file}")
        sys.exit(1)
    
    if args.type == 'contracts':
        success = convert_contracts_csv(args.csv_file, args.output, skiprows=args.skiprows)
    elif args.type == 'performance':
        success = convert_performance_csv(args.csv_file, args.output)
    else:
        print(f"Type '{args.type}' not yet implemented")
        success = False
    
    if success:
        print("\nConversion complete!")
        print("\nNext steps:")
        print("1. Verify Parquet file with: python3 -c \"import pandas as pd; print(pd.read_parquet('data/processed/market/players_contracts_2025_2026.parquet').head())\"")
        print("2. Restart backend to load new data")
        print("3. Test API: curl http://localhost:8000/api/v1/market/contracts/team/MTL")
        print("4. Test STANLEY: 'Show me MTL contracts'")
    else:
        print("\nConversion failed - check errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()

