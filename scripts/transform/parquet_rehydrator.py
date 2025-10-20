#!/usr/bin/env python3
"""
Parquet Rehydrator

Query-time helper that accepts row_selector metadata and returns 
exact rows from parquet files for deterministic metric computation.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import json
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

class ParquetRehydrator:
    """Rehydrates data from parquet files using structured selectors"""
    
    def __init__(self, base_path: str = "/Users/xavier.bouchard/Desktop/HeartBeat"):
        self.base_path = Path(base_path)
        self.processed_path = self.base_path / "data" / "processed"
        
        # Initialize DuckDB connection for advanced querying (optional)
        if DUCKDB_AVAILABLE:
            self.conn = duckdb.connect()
        else:
            self.conn = None

    def rehydrate_from_selector(self, row_selector: Dict[str, Any]) -> pd.DataFrame:
        """
        Rehydrate rows from parquet using row_selector specification
        
        Args:
            row_selector: Dict containing table, partitions, where, columns, etc.
            
        Returns:
            DataFrame with selected rows and columns
        """
        table = row_selector.get('table', 'pbp')
        partitions = row_selector.get('partitions', {})
        where_clause = row_selector.get('where', {})
        columns = row_selector.get('columns', [])
        row_ids = row_selector.get('row_ids', [])
        
        # Determine file path
        file_path = self._resolve_file_path(table, partitions)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")
        
        # Load data
        print(f"Loading data from: {file_path}")
        df = pd.read_parquet(file_path)
        
        # Apply row_ids filter first (most efficient)
        if row_ids:
            df = df[df['row_id'].isin(row_ids)]
        
        # Apply where clause filters
        if where_clause:
            df = self._apply_where_filters(df, where_clause)
        
        # Apply partition filters
        if partitions:
            df = self._apply_partition_filters(df, partitions)
        
        # Select specific columns
        if columns:
            available_columns = [col for col in columns if col in df.columns]
            if available_columns != columns:
                missing = set(columns) - set(available_columns)
                print(f"Warning: Missing columns {missing}")
            df = df[available_columns]
        
        print(f"Rehydrated {len(df)} rows with {len(df.columns)} columns")
        return df

    def _resolve_file_path(self, table: str, partitions: Dict[str, Any]) -> Path:
        """Resolve the actual parquet file path from table and partitions"""
        
        if table == 'pbp':
            # Handle PBP table
            season = partitions.get('season', '2024-25')
            game_id = partitions.get('game_id')
            
            if game_id:
                # Partitioned approach (future)
                return self.processed_path / "fact" / "pbp" / f"season={season}" / f"game_id={game_id}.parquet"
            else:
                # Single file approach (current)
                return self.processed_path / "fact" / "pbp" / f"unified_pbp_{season}.parquet"
        
        elif table == 'season_results':
            season = partitions.get('season', '2024-2025')
            return self.processed_path / "analytics" / "mtl_season_results" / season / f"mtl_season_game_results_{season}.parquet"
        
        elif table == 'matchup_reports':
            return self.processed_path / "analytics" / "mtl_matchup_reports" / "unified_matchup_reports_2024_2025.parquet"
        
        elif table == 'line_combinations':
            combo_type = partitions.get('type', 'forwards')
            return self.processed_path / "analytics" / f"mtl_line_combinations_2024-2025" / f"Line_Combinations_Metrics_for_{combo_type.title()}.parquet"
        
        else:
            raise ValueError(f"Unknown table: {table}")

    def _apply_partition_filters(self, df: pd.DataFrame, partitions: Dict[str, Any]) -> pd.DataFrame:
        """Apply partition-level filters"""
        for key, value in partitions.items():
            if key in df.columns:
                df = df[df[key] == value]
        return df

    def _apply_where_filters(self, df: pd.DataFrame, where_clause: Dict[str, Any]) -> pd.DataFrame:
        """Apply where clause filters using MongoDB-style operators"""
        
        for field, condition in where_clause.items():
            if field not in df.columns:
                continue
                
            if isinstance(condition, dict):
                for operator, value in condition.items():
                    if operator == '$eq':
                        df = df[df[field] == value]
                    elif operator == '$ne':
                        df = df[df[field] != value]
                    elif operator == '$in':
                        df = df[df[field].isin(value)]
                    elif operator == '$nin':
                        df = df[~df[field].isin(value)]
                    elif operator == '$gt':
                        df = df[df[field] > value]
                    elif operator == '$gte':
                        df = df[df[field] >= value]
                    elif operator == '$lt':
                        df = df[df[field] < value]
                    elif operator == '$lte':
                        df = df[df[field] <= value]
                    elif operator == '$between':
                        if len(value) == 2:
                            df = df[(df[field] >= value[0]) & (df[field] <= value[1])]
                    elif operator == '$contains_all':
                        # For array fields
                        if hasattr(df[field].iloc[0], '__iter__'):
                            mask = df[field].apply(lambda x: all(item in x for item in value))
                            df = df[mask]
                    elif operator == '$contains_any':
                        # For array fields
                        if hasattr(df[field].iloc[0], '__iter__'):
                            mask = df[field].apply(lambda x: any(item in x for item in value))
                            df = df[mask]
            else:
                # Direct equality
                df = df[df[field] == condition]
                
        return df

    def compute_metrics_from_selector(self, row_selector: Dict[str, Any], metrics: List[str]) -> Dict[str, Any]:
        """Compute specific metrics from rehydrated data"""
        
        # Rehydrate data
        df = self.rehydrate_from_selector(row_selector)
        
        if df.empty:
            return {metric: None for metric in metrics}
        
        results = {}
        
        for metric in metrics:
            if metric == 'total_events':
                results[metric] = len(df)
            elif metric == 'shots':
                results[metric] = len(df[df['event_type'] == 'SHOT'])
            elif metric == 'goals':
                results[metric] = len(df[df['event_type'] == 'GOAL'])
            elif metric == 'xg_total':
                results[metric] = df['xg'].sum() if 'xg' in df.columns else 0
            elif metric == 'xg_avg':
                results[metric] = df['xg'].mean() if 'xg' in df.columns else 0
            elif metric == 'possession_time':
                if 'period_seconds' in df.columns:
                    possession_events = df[df['is_possession_event'] == True]
                    if len(possession_events) > 1:
                        results[metric] = possession_events['period_seconds'].max() - possession_events['period_seconds'].min()
                    else:
                        results[metric] = 0
                else:
                    results[metric] = 0
            elif metric == 'zone_time':
                zone_counts = df['zone'].value_counts().to_dict() if 'zone' in df.columns else {}
                results[metric] = zone_counts
            elif metric == 'unique_players':
                if 'player_id' in df.columns:
                    results[metric] = df['player_id'].nunique()
                else:
                    results[metric] = 0
            else:
                results[metric] = None
        
        return results

    def create_heatmap_data(self, row_selector: Dict[str, Any]) -> Dict[str, Any]:
        """Create heatmap data from coordinate information"""
        
        df = self.rehydrate_from_selector(row_selector)
        
        if df.empty or 'x_coord' not in df.columns or 'y_coord' not in df.columns:
            return {'error': 'No coordinate data available'}
        
        # Filter out null coordinates
        coord_df = df.dropna(subset=['x_coord', 'y_coord'])
        
        if coord_df.empty:
            return {'error': 'No valid coordinates found'}
        
        heatmap_data = {
            'coordinates': coord_df[['x_coord', 'y_coord']].values.tolist(),
            'events': coord_df['event_type'].tolist() if 'event_type' in coord_df.columns else [],
            'xg_values': coord_df['xg'].tolist() if 'xg' in coord_df.columns else [],
            'count': len(coord_df),
            'bounds': {
                'x_min': float(coord_df['x_coord'].min()),
                'x_max': float(coord_df['x_coord'].max()),
                'y_min': float(coord_df['y_coord'].min()),
                'y_max': float(coord_df['y_coord'].max())
            }
        }
        
        return heatmap_data

    def validate_selector(self, row_selector: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that a row_selector is properly formatted and executable"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Required fields
        if 'table' not in row_selector:
            validation_result['errors'].append("Missing required field: table")
            validation_result['valid'] = False
        
        # Check table validity
        table = row_selector.get('table')
        valid_tables = ['pbp', 'season_results', 'matchup_reports', 'line_combinations']
        if table not in valid_tables:
            validation_result['errors'].append(f"Invalid table: {table}. Valid options: {valid_tables}")
            validation_result['valid'] = False
        
        # Check file existence
        try:
            partitions = row_selector.get('partitions', {})
            file_path = self._resolve_file_path(table, partitions)
            if not file_path.exists():
                validation_result['errors'].append(f"File not found: {file_path}")
                validation_result['valid'] = False
        except Exception as e:
            validation_result['errors'].append(f"Error resolving file path: {str(e)}")
            validation_result['valid'] = False
        
        # Check where clause format
        where_clause = row_selector.get('where', {})
        if where_clause and not isinstance(where_clause, dict):
            validation_result['errors'].append("Where clause must be a dictionary")
            validation_result['valid'] = False
        
        # Validate operators in where clause
        valid_operators = ['$eq', '$ne', '$in', '$nin', '$gt', '$gte', '$lt', '$lte', '$between', '$contains_all', '$contains_any']
        for field, condition in where_clause.items():
            if isinstance(condition, dict):
                for operator in condition.keys():
                    if operator not in valid_operators:
                        validation_result['warnings'].append(f"Unknown operator: {operator}")
        
        return validation_result

def main():
    """Example usage and testing"""
    rehydrator = ParquetRehydrator()
    
    # Example row_selector
    test_selector = {
        "table": "pbp",
        "partitions": {"season": "2024-25", "game_id": 20006},
        "where": {
            "period": {"$in": [1, 2, 3]},
            "event_type": {"$in": ["SHOT", "GOAL"]}
        },
        "columns": ["row_id", "period", "period_seconds", "event_type", "team_abbr", "x_coord", "y_coord", "player_id", "xg"]
    }
    
    # Validate selector
    validation = rehydrator.validate_selector(test_selector)
    print("Validation result:", validation)
    
    if validation['valid']:
        try:
            # Test rehydration
            df = rehydrator.rehydrate_from_selector(test_selector)
            print(f"Rehydrated {len(df)} rows")
            print(f"Columns: {list(df.columns)}")
            
            # Test metrics computation
            metrics = rehydrator.compute_metrics_from_selector(
                test_selector, 
                ['total_events', 'shots', 'goals', 'xg_total']
            )
            print("Computed metrics:", metrics)
            
        except Exception as e:
            print(f"Error during rehydration: {e}")

if __name__ == "__main__":
    main()
