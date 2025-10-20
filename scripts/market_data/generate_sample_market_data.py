"""
Generate realistic sample contract and market data for development.

Creates sample data for:
- Player contracts
- Contract performance indices
- Team cap management
- Trade history
- Market comparables
- League market summaries

Uses existing player stats and rosters to generate realistic contract data.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime, timedelta, date
import random
import uuid
from typing import Dict, List, Any
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.market_data.schemas import (
    PLAYER_CONTRACTS_SCHEMA,
    CONTRACT_PERFORMANCE_INDEX_SCHEMA,
    TEAM_CAP_MANAGEMENT_SCHEMA,
    TRADE_HISTORY_SCHEMA,
    MARKET_COMPARABLES_SCHEMA,
    LEAGUE_MARKET_SUMMARY_SCHEMA
)
from scripts.market_data.real_player_names import get_player_name_for_team


class SampleMarketDataGenerator:
    """Generate sample market data for development."""
    
    def __init__(self, output_dir: str = "data/processed/market"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # NHL teams
        self.teams = [
            "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET",
            "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT",
            "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK",
            "WPG", "WSH"
        ]
        
        # Position-based contract ranges (in millions)
        self.contract_ranges = {
            'C': (750000, 12500000),
            'LW': (750000, 11000000),
            'RW': (750000, 11000000),
            'D': (750000, 10500000),
            'G': (750000, 10000000)
        }
        
        # Current season
        self.current_season = "2025-2026"
        self.cap_ceiling = 95500000  # 2025-26 actual NHL salary cap
        
        # Future cap projections (official NHL/NHLPA projections)
        self.future_caps = {
            "2026-2027": 104000000,   # $104M cap ceiling
            "2027-2028": 113500000    # $113.5M cap ceiling
        }
        
    def generate_all(self):
        """Generate all sample market data."""
        print("Generating sample market data...")
        
        # Generate in order (dependencies)
        contracts_df = self.generate_player_contracts()
        performance_df = self.generate_performance_indices(contracts_df)
        cap_df = self.generate_team_cap_management(contracts_df)
        trades_df = self.generate_trade_history()
        comparables_df = self.generate_market_comparables(contracts_df)
        league_summary_df = self.generate_league_market_summary(contracts_df)
        
        # Save all datasets
        self.save_parquet(contracts_df, "players_contracts", PLAYER_CONTRACTS_SCHEMA)
        self.save_parquet(performance_df, "contract_performance_index", CONTRACT_PERFORMANCE_INDEX_SCHEMA)
        self.save_parquet(cap_df, "team_cap_management", TEAM_CAP_MANAGEMENT_SCHEMA)
        self.save_parquet(trades_df, "trade_history", TRADE_HISTORY_SCHEMA)
        self.save_parquet(comparables_df, "market_comparables", MARKET_COMPARABLES_SCHEMA)
        self.save_parquet(league_summary_df, "league_market_summary", LEAGUE_MARKET_SUMMARY_SCHEMA)
        
        print(f"\nSample data generated successfully!")
        print(f"Output directory: {self.output_dir}")
        
    def generate_player_contracts(self) -> pd.DataFrame:
        """Generate sample player contracts."""
        print("Generating player contracts...")
        
        contracts = []
        player_id_base = 8470000
        
        # Generate 20-25 contracts per team
        for team in self.teams:
            num_players = random.randint(20, 25)
            
            for i in range(num_players):
                player_id = player_id_base + len(contracts)
                position = random.choice(['C', 'LW', 'RW', 'D', 'G'])
                
                # Age distribution (realistic NHL roster)
                age = random.choices(
                    range(19, 42),
                    weights=[5, 10, 15, 20, 20, 15, 10, 8, 6, 4, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    k=1
                )[0]
                
                # Cap hit based on position and age
                min_hit, max_hit = self.contract_ranges[position]
                if age < 23:  # ELC or rookie deal
                    cap_hit = random.uniform(750000, 3500000)
                    contract_type = 'ELC'
                elif age < 27:  # RFA years
                    cap_hit = random.uniform(1000000, 8000000)
                    contract_type = random.choice(['RFA', 'Extension'])
                else:  # UFA years
                    cap_hit = random.uniform(min_hit, max_hit)
                    contract_type = 'UFA'
                
                # Contract term
                if contract_type == 'ELC':
                    years_total = 3
                    years_remaining = random.randint(1, 3)
                else:
                    years_total = random.choice([1, 2, 3, 4, 5, 6, 7, 8])
                    years_remaining = random.randint(1, years_total)
                
                # Contract dates
                signing_year = 2025 - (years_total - years_remaining)
                signing_date = date(signing_year, random.randint(6, 8), random.randint(1, 28))
                start_date = date(signing_year, 10, 1)
                end_date = date(signing_year + years_total, 6, 30)
                
                # Clauses (more common for high-paid veterans)
                has_ntc = cap_hit > 5000000 and age > 28 and random.random() > 0.6
                has_nmc = cap_hit > 7000000 and age > 28 and random.random() > 0.7
                
                contracts.append({
                    'nhl_player_id': player_id,
                    'full_name': f"Player {player_id}",
                    'team_abbrev': team,
                    'position': position,
                    'age': age,
                    'cap_hit': round(cap_hit, 2),
                    'cap_hit_percentage': round((cap_hit / self.cap_ceiling) * 100, 2),
                    'contract_years_total': years_total,
                    'years_remaining': years_remaining,
                    'contract_start_date': start_date,
                    'contract_end_date': end_date,
                    'signing_date': signing_date,
                    'contract_type': contract_type,
                    'no_trade_clause': has_ntc,
                    'no_movement_clause': has_nmc,
                    'signing_age': age - (years_total - years_remaining),
                    'signing_team': team,
                    'contract_status': 'active',
                    'retained_percentage': 0.0,
                    'season': self.current_season,
                    'sync_date': date.today(),
                    'data_source': 'sample_generator'
                })
        
        print(f"Generated {len(contracts)} player contracts")
        return pd.DataFrame(contracts)
    
    def generate_performance_indices(self, contracts_df: pd.DataFrame) -> pd.DataFrame:
        """Generate contract performance indices."""
        print("Generating performance indices...")
        
        indices = []
        
        for _, contract in contracts_df.iterrows():
            # Calculate performance index (0-200 scale, 100 = average)
            # Create more variance for interesting data
            base_performance = random.gauss(100, 40)  # Increased variance from 30 to 40
            performance_index = max(20, min(200, base_performance))
            
            # Contract efficiency (performance / cap hit normalized)
            cap_normalized = contract['cap_hit'] / 3000000  # Normalize around $3M
            contract_efficiency = performance_index / max(cap_normalized, 0.5)
            
            # Add randomness to create more overperforming/underperforming contracts
            contract_efficiency = contract_efficiency * random.uniform(0.7, 1.4)
            
            # Market value estimate
            market_value = (performance_index / 100) * contract['cap_hit'] * random.uniform(0.7, 1.5)
            
            # Surplus value
            surplus_value = market_value - contract['cap_hit']
            
            # Performance percentile
            performance_percentile = min(100, max(0, (performance_index / 200) * 100))
            
            # Contract percentile (based on efficiency)
            contract_percentile = min(100, max(0, (contract_efficiency / 200) * 100))
            
            # Status classification (adjusted thresholds for more variety)
            if contract_efficiency >= 115:
                status = 'overperforming'
            elif contract_efficiency >= 85:
                status = 'fair'
            else:
                status = 'underperforming'
            
            indices.append({
                'nhl_player_id': contract['nhl_player_id'],
                'season': self.current_season,
                'performance_index': round(performance_index, 2),
                'contract_efficiency': round(contract_efficiency, 2),
                'market_value': round(market_value, 2),
                'surplus_value': round(surplus_value, 2),
                'performance_percentile': round(performance_percentile, 2),
                'contract_percentile': round(contract_percentile, 2),
                'status': status,
                'last_calculated': datetime.now()
            })
        
        print(f"Generated {len(indices)} performance indices")
        return pd.DataFrame(indices)
    
    def generate_team_cap_management(self, contracts_df: pd.DataFrame) -> pd.DataFrame:
        """Generate team cap management data."""
        print("Generating team cap management...")
        
        cap_data = []
        
        for team in self.teams:
            team_contracts = contracts_df[contracts_df['team_abbrev'] == team]
            
            cap_hit_total = team_contracts['cap_hit'].sum()
            cap_space = self.cap_ceiling - cap_hit_total
            
            # LTIR pool (some teams have it)
            ltir_pool = random.choice([0, 0, 0, random.uniform(1000000, 5000000)])
            
            # Deadline cap space (accrued)
            deadline_cap_space = cap_space * 1.5  # Simplified accrual
            
            # Contracts expiring
            contracts_expiring = len(team_contracts[team_contracts['years_remaining'] == 1])
            
            # Next season projections using official NHL/NHLPA figures
            projected_2026_27 = self.future_caps.get("2026-2027", 104000000)
            committed_next = team_contracts[team_contracts['years_remaining'] > 1]['cap_hit'].sum()
            
            cap_data.append({
                'team_abbrev': team,
                'season': self.current_season,
                'cap_ceiling': self.cap_ceiling,
                'cap_hit_total': round(cap_hit_total, 2),
                'cap_space': round(cap_space, 2),
                'ltir_pool': round(ltir_pool, 2),
                'deadline_cap_space': round(deadline_cap_space, 2),
                'active_roster_count': len(team_contracts),
                'contracts_expiring': contracts_expiring,
                'projected_next_season_cap': projected_2026_27,  # Use real NHL projection
                'committed_next_season': round(committed_next, 2),
                'sync_date': date.today()
            })
        
        print(f"Generated cap data for {len(cap_data)} teams")
        return pd.DataFrame(cap_data)
    
    def generate_trade_history(self) -> pd.DataFrame:
        """Generate sample trade history."""
        print("Generating trade history...")
        
        trades = []
        
        # Generate 10-15 recent trades
        num_trades = random.randint(10, 15)
        
        for i in range(num_trades):
            trade_date = date.today() - timedelta(days=random.randint(1, 90))
            
            # Pick 2-3 teams
            num_teams = random.choice([2, 2, 2, 3])
            teams_involved = random.sample(self.teams, num_teams)
            
            # Players moved (1-3 players)
            num_players = random.randint(1, 3)
            players_moved = []
            for p in range(num_players):
                from_team = random.choice(teams_involved)
                to_team = random.choice([t for t in teams_involved if t != from_team])
                players_moved.append({
                    'player_id': 8470000 + random.randint(0, 10000),
                    'player_name': f"Traded Player {i}-{p}",
                    'from_team': from_team,
                    'to_team': to_team
                })
            
            # Draft picks (maybe)
            draft_picks = []
            if random.random() > 0.5:
                num_picks = random.randint(1, 2)
                for _ in range(num_picks):
                    from_team = random.choice(teams_involved)
                    to_team = random.choice([t for t in teams_involved if t != from_team])
                    draft_picks.append({
                        'year': random.choice([2025, 2026, 2027]),
                        'round': random.choice([1, 2, 3, 4]),
                        'from_team': from_team,
                        'to_team': to_team,
                        'conditions': None
                    })
            
            # Cap implications
            cap_implications = {
                'team_impacts': [
                    {'team': team, 'cap_change': random.uniform(-5000000, 5000000)}
                    for team in teams_involved
                ]
            }
            
            trade_type = random.choice([
                'player_for_player',
                'player_for_picks',
                'three_way',
                'cap_dump'
            ])
            
            trades.append({
                'trade_id': str(uuid.uuid4()),
                'trade_date': trade_date,
                'season': self.current_season,
                'teams_involved': teams_involved,
                'players_moved': players_moved,
                'draft_picks_moved': draft_picks if draft_picks else None,
                'cap_implications': cap_implications,
                'trade_type': trade_type,
                'trade_deadline': trade_date.month == 3 and trade_date.day <= 7,
                'retained_salary_details': None,
                'data_source': 'sample_generator'
            })
        
        print(f"Generated {len(trades)} trades")
        return pd.DataFrame(trades)
    
    def generate_market_comparables(self, contracts_df: pd.DataFrame) -> pd.DataFrame:
        """Generate market comparables."""
        print("Generating market comparables...")
        
        comparables = []
        
        # Generate comparables for a subset of players
        sample_players = contracts_df.sample(min(100, len(contracts_df)))
        
        for _, player in sample_players.iterrows():
            # Find similar players (same position, similar age/production)
            similar_players = contracts_df[
                (contracts_df['position'] == player['position']) &
                (contracts_df['nhl_player_id'] != player['nhl_player_id']) &
                (abs(contracts_df['age'] - player['age']) <= 3) &
                (abs(contracts_df['cap_hit'] - player['cap_hit']) <= 2000000)
            ].head(10)
            
            comparable_list = []
            for _, comp in similar_players.iterrows():
                similarity_score = random.uniform(70, 95)
                comparable_list.append({
                    'player_id': comp['nhl_player_id'],
                    'player_name': comp['full_name'],
                    'team': comp['team_abbrev'],
                    'cap_hit': comp['cap_hit'],
                    'age_at_signing': comp['signing_age'],
                    'contract_years': comp['contract_years_total'],
                    'production_last_season': random.uniform(20, 90),
                    'similarity_score': round(similarity_score, 2)
                })
            
            # Market tier
            if player['cap_hit'] > 9000000:
                market_tier = 'elite'
            elif player['cap_hit'] > 6000000:
                market_tier = 'top_line' if player['position'] in ['C', 'LW', 'RW'] else 'top_pair'
            elif player['cap_hit'] > 3000000:
                market_tier = 'middle_six' if player['position'] in ['C', 'LW', 'RW'] else 'middle_pair'
            else:
                market_tier = 'bottom_six' if player['position'] in ['C', 'LW', 'RW'] else 'bottom_pair'
            
            comparables.append({
                'comparable_id': str(uuid.uuid4()),
                'player_id': player['nhl_player_id'],
                'player_name': player['full_name'],
                'position': player['position'],
                'comparable_players': comparable_list,
                'market_tier': market_tier,
                'season': self.current_season,
                'calculation_date': date.today()
            })
        
        print(f"Generated comparables for {len(comparables)} players")
        return pd.DataFrame(comparables)
    
    def generate_league_market_summary(self, contracts_df: pd.DataFrame) -> pd.DataFrame:
        """Generate league market summary."""
        print("Generating league market summary...")
        
        summaries = []
        
        positions = ['C', 'LW', 'RW', 'D', 'G']
        
        for position in positions:
            position_contracts = contracts_df[contracts_df['position'] == position]
            
            avg_cap = position_contracts['cap_hit'].mean()
            median_cap = position_contracts['cap_hit'].median()
            min_cap = position_contracts['cap_hit'].min()
            max_cap = position_contracts['cap_hit'].max()
            total_contracts = len(position_contracts)
            
            # Tier breakdown
            elite_contracts = position_contracts[position_contracts['cap_hit'] > 9000000]
            top_contracts = position_contracts[
                (position_contracts['cap_hit'] > 6000000) &
                (position_contracts['cap_hit'] <= 9000000)
            ]
            middle_contracts = position_contracts[
                (position_contracts['cap_hit'] > 3000000) &
                (position_contracts['cap_hit'] <= 6000000)
            ]
            bottom_contracts = position_contracts[position_contracts['cap_hit'] <= 3000000]
            
            tier_breakdown = {
                'elite_count': len(elite_contracts),
                'elite_avg': elite_contracts['cap_hit'].mean() if len(elite_contracts) > 0 else 0,
                'top_line_count': len(top_contracts),
                'top_line_avg': top_contracts['cap_hit'].mean() if len(top_contracts) > 0 else 0,
                'middle_count': len(middle_contracts),
                'middle_avg': middle_contracts['cap_hit'].mean() if len(middle_contracts) > 0 else 0,
                'bottom_count': len(bottom_contracts),
                'bottom_avg': bottom_contracts['cap_hit'].mean() if len(bottom_contracts) > 0 else 0
            }
            
            summaries.append({
                'position': position,
                'season': self.current_season,
                'avg_cap_hit': round(avg_cap, 2),
                'median_cap_hit': round(median_cap, 2),
                'min_cap_hit': round(min_cap, 2),
                'max_cap_hit': round(max_cap, 2),
                'total_contracts': total_contracts,
                'tier_breakdown': tier_breakdown,
                'last_updated': datetime.now()
            })
        
        print(f"Generated league summaries for {len(summaries)} positions")
        return pd.DataFrame(summaries)
    
    def save_parquet(self, df: pd.DataFrame, filename: str, schema: pa.Schema):
        """Save DataFrame as Parquet with proper schema."""
        output_path = self.output_dir / f"{filename}_{self.current_season.replace('-', '_')}.parquet"
        
        # Convert DataFrame to PyArrow Table with schema
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
        
        # Write Parquet file with compression
        pq.write_table(
            table,
            output_path,
            compression='ZSTD',
            compression_level=3
        )
        
        print(f"Saved: {output_path}")


def main():
    """Generate sample market data."""
    generator = SampleMarketDataGenerator()
    generator.generate_all()
    
    print("\nSample market data generation complete!")
    print("\nNext steps:")
    print("1. Review generated Parquet files in data/processed/market/")
    print("2. Upload to GCS using setup_bigquery.py")
    print("3. Run BigQuery DDL to create tables")
    print("4. Test API endpoints")


if __name__ == "__main__":
    main()

