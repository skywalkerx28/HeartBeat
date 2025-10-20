"""
Parquet schema definitions for NHL market analytics data.

This module defines the schema for contract, cap, trade, and market comparable data
stored in Parquet format for both local processing and GCS/BigQuery integration.
"""

import pyarrow as pa
from typing import Dict

# Player Contracts Schema
PLAYER_CONTRACTS_SCHEMA = pa.schema([
    ('nhl_player_id', pa.int64()),
    ('full_name', pa.string()),
    ('team_abbrev', pa.string()),
    ('position', pa.string()),
    ('age', pa.int32()),
    ('cap_hit', pa.float64()),
    ('cap_hit_percentage', pa.float64()),
    ('contract_years_total', pa.int32()),
    ('years_remaining', pa.int32()),
    ('contract_start_date', pa.date32()),
    ('contract_end_date', pa.date32()),
    ('signing_date', pa.date32()),
    ('contract_type', pa.string()),  # 'ELC', 'RFA', 'UFA', 'Extension'
    ('no_trade_clause', pa.bool_()),
    ('no_movement_clause', pa.bool_()),
    ('signing_age', pa.int32()),
    ('signing_team', pa.string()),
    ('contract_status', pa.string()),  # 'active', 'unsigned', 'buyout', 'ltir', 'retained'
    ('roster_status', pa.string()),  # 'roster', 'non_roster', 'reserve_list', 'minors'
    ('retained_percentage', pa.float64()),
    ('season', pa.string()),
    ('sync_date', pa.date32()),
    ('data_source', pa.string()),  # 'puckpedia', 'capwages', 'nhlpa', 'manual'
    # Salary breakdown
    ('base_salary', pa.float64()),
    ('signing_bonus', pa.float64()),
    ('performance_bonus', pa.float64()),
    ('clause_details', pa.string()),  # Full text description of NTC/NMC details
    ('arbitration_eligible', pa.bool_()),
    ('ufa_year', pa.int32()),  # Year becomes unrestricted FA (nullable)
    # Draft information (for prospects and tracking)
    ('draft_year', pa.int32()),  # Year drafted (nullable)
    ('draft_round', pa.int32()),  # Round drafted (nullable)
    ('draft_overall', pa.int32()),  # Overall pick number (nullable)
    ('must_sign_by', pa.date32()),  # Deadline to sign unsigned prospects (nullable)
    # Year-by-year salary breakdown (for cap planning)
    ('base_2025_26', pa.float64()),
    ('sb_2025_26', pa.float64()),  # Signing bonus
    ('pb_potential_2025_26', pa.float64()),  # Performance bonus potential
    ('cap_hit_2025_26', pa.float64()),
    ('base_2026_27', pa.float64()),
    ('sb_2026_27', pa.float64()),
    ('pb_potential_2026_27', pa.float64()),
    ('cap_hit_2026_27', pa.float64()),
    ('base_2027_28', pa.float64()),
    ('sb_2027_28', pa.float64()),
    ('pb_potential_2027_28', pa.float64()),
    ('cap_hit_2027_28', pa.float64()),
    ('base_2028_29', pa.float64()),
    ('sb_2028_29', pa.float64()),
    ('pb_potential_2028_29', pa.float64()),
    ('cap_hit_2028_29', pa.float64()),
    ('base_2029_30', pa.float64()),
    ('sb_2029_30', pa.float64()),
    ('pb_potential_2029_30', pa.float64()),
    ('cap_hit_2029_30', pa.float64()),
    ('base_2030_31', pa.float64()),
    ('sb_2030_31', pa.float64()),
    ('pb_potential_2030_31', pa.float64()),
    ('cap_hit_2030_31', pa.float64()),
])

# Contract Performance Index Schema
CONTRACT_PERFORMANCE_INDEX_SCHEMA = pa.schema([
    ('nhl_player_id', pa.int64()),
    ('season', pa.string()),
    ('performance_index', pa.float64()),  # Composite score: points/60, xG/60, defensive metrics
    ('contract_efficiency', pa.float64()),  # Performance value / cap hit ratio
    ('market_value', pa.float64()),  # Estimated fair market value
    ('surplus_value', pa.float64()),  # Market value - cap hit
    ('performance_percentile', pa.float64()),  # vs league peers at position
    ('contract_percentile', pa.float64()),  # Contract AAV vs position
    ('status', pa.string()),  # 'overperforming', 'fair', 'underperforming'
    ('last_calculated', pa.timestamp('us')),
])

# Team Cap Management Schema
TEAM_CAP_MANAGEMENT_SCHEMA = pa.schema([
    ('team_abbrev', pa.string()),
    ('season', pa.string()),
    ('cap_ceiling', pa.float64()),
    ('cap_hit_total', pa.float64()),
    ('cap_space', pa.float64()),
    ('ltir_pool', pa.float64()),
    ('deadline_cap_space', pa.float64()),  # Accrued space at trade deadline
    ('active_roster_count', pa.int32()),
    ('contracts_expiring', pa.int32()),
    ('projected_next_season_cap', pa.float64()),
    ('committed_next_season', pa.float64()),
    ('sync_date', pa.date32()),
])

# Trade History Schema
TRADE_HISTORY_SCHEMA = pa.schema([
    ('trade_id', pa.string()),
    ('trade_date', pa.date32()),
    ('season', pa.string()),
    ('teams_involved', pa.list_(pa.string())),
    ('players_moved', pa.list_(pa.struct([
        ('player_id', pa.int64()),
        ('player_name', pa.string()),
        ('from_team', pa.string()),
        ('to_team', pa.string()),
    ]))),
    ('draft_picks_moved', pa.list_(pa.struct([
        ('year', pa.int32()),
        ('round', pa.int32()),
        ('from_team', pa.string()),
        ('to_team', pa.string()),
        ('conditions', pa.string()),
    ]))),
    ('cap_implications', pa.struct([
        ('team_impacts', pa.list_(pa.struct([
            ('team', pa.string()),
            ('cap_change', pa.float64()),
        ]))),
    ])),
    ('trade_type', pa.string()),  # 'player_for_player', 'player_for_picks', 'three_way', 'cap_dump'
    ('trade_deadline', pa.bool_()),
    ('retained_salary_details', pa.struct([
        ('player_id', pa.int64()),
        ('retaining_team', pa.string()),
        ('percentage', pa.float64()),
        ('years_remaining', pa.int32()),
    ])),
    ('data_source', pa.string()),
])

# Market Comparables Schema
MARKET_COMPARABLES_SCHEMA = pa.schema([
    ('comparable_id', pa.string()),
    ('player_id', pa.int64()),
    ('player_name', pa.string()),
    ('position', pa.string()),
    ('comparable_players', pa.list_(pa.struct([
        ('player_id', pa.int64()),
        ('player_name', pa.string()),
        ('team', pa.string()),
        ('cap_hit', pa.float64()),
        ('age_at_signing', pa.int32()),
        ('contract_years', pa.int32()),
        ('production_last_season', pa.float64()),
        ('similarity_score', pa.float64()),
    ]))),
    ('market_tier', pa.string()),  # 'elite', 'top_line', 'middle_six', 'bottom_six', 'top_pair', etc.
    ('season', pa.string()),
    ('calculation_date', pa.date32()),
])

# League Market Summary Schema
LEAGUE_MARKET_SUMMARY_SCHEMA = pa.schema([
    ('position', pa.string()),
    ('season', pa.string()),
    ('avg_cap_hit', pa.float64()),
    ('median_cap_hit', pa.float64()),
    ('min_cap_hit', pa.float64()),
    ('max_cap_hit', pa.float64()),
    ('total_contracts', pa.int32()),
    ('tier_breakdown', pa.struct([
        ('elite_count', pa.int32()),
        ('elite_avg', pa.float64()),
        ('top_line_count', pa.int32()),
        ('top_line_avg', pa.float64()),
        ('middle_count', pa.int32()),
        ('middle_avg', pa.float64()),
        ('bottom_count', pa.int32()),
        ('bottom_avg', pa.float64()),
    ])),
    ('last_updated', pa.timestamp('us')),
])

# Schema registry for easy access
SCHEMA_REGISTRY: Dict[str, pa.Schema] = {
    'player_contracts': PLAYER_CONTRACTS_SCHEMA,
    'contract_performance_index': CONTRACT_PERFORMANCE_INDEX_SCHEMA,
    'team_cap_management': TEAM_CAP_MANAGEMENT_SCHEMA,
    'trade_history': TRADE_HISTORY_SCHEMA,
    'market_comparables': MARKET_COMPARABLES_SCHEMA,
    'league_market_summary': LEAGUE_MARKET_SUMMARY_SCHEMA,
}


def get_schema(schema_name: str) -> pa.Schema:
    """Get a schema by name from the registry."""
    if schema_name not in SCHEMA_REGISTRY:
        raise ValueError(f"Schema '{schema_name}' not found. Available: {list(SCHEMA_REGISTRY.keys())}")
    return SCHEMA_REGISTRY[schema_name]


def validate_dataframe_schema(df, schema_name: str) -> bool:
    """Validate that a DataFrame matches the expected schema."""
    expected_schema = get_schema(schema_name)
    # Convert DataFrame to Arrow table for schema comparison
    import pyarrow as pa
    table = pa.Table.from_pandas(df)
    
    # Compare field names
    expected_fields = {field.name for field in expected_schema}
    actual_fields = {field.name for field in table.schema}
    
    if expected_fields != actual_fields:
        missing = expected_fields - actual_fields
        extra = actual_fields - expected_fields
        if missing:
            print(f"Missing fields: {missing}")
        if extra:
            print(f"Extra fields: {extra}")
        return False
    
    return True

